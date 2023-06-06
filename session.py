"""
session类型，远程会话的根类
"""

import asyncio, re, logging, functools, importlib
from protocol import MudClientProtocol
from objects import Alias, Trigger, Command, Timer

class Session:
    """会话类，管理与远程服务器的连接和配置."""

    "转义字符串替代"
    _esc_regx = re.compile("\x1b\\[[^mz]+[mz]")
    #_esc_regx = re.compile("\x1b\\[[^m]+[m]")

    def __init__(self, app, name, host, port, terminal, encoding, encoding_errors, clientwidth, clientheight, *args, **kwargs):
        """
        初始化一个会话session，并将会话连接到指定的远程服务器。
        session类运行时，必须有运行的事件循环，因此必须在asyncio的异步环境下运行。
        当没有正在运行的循环时，初始化会抛出异常，由asyncio.get_running_loop函数抛出。
        参数信息：
            app     : 本会话绑定的application， 当前版本下为PyMud类的实例
            name    : 会话名称
            host    : 远程服务器的 名称/IP地址
            port    : 远程服务器的 端口
            terminal: 信息的输出终端
            encoding: 远程服务器编码
            encoding_errors : 对远程服务器数据解码错误时的处理
            clientwidth     : 终端的宽度（每行字符数）
            clientheight    : 终端的高度（行数）
        """
        self.loop   = asyncio.get_running_loop()
        self.log    = logging.getLogger("pymud.session")
        self.app    = app
        self.name   = name
        self.host   = host
        self.port   = port
        self.terminal = terminal
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self.clientwidth = clientwidth
        self.clientheight = clientheight
        self.newline = "\n"
        self.seperator = ";"

        self.active = False
        self.state  = "INIT"
        self._extra = args
        self._kwextra = kwargs

        self.last_command = ""

        self._bglines = []  # 非激活情况下的会话缓冲
        self._tasks = []

        self._uid = 0       # 适用于本会话的全局id标识

        self._timers    = {}
        self._triggers  = {}
        self._aliases   = {}
        self._variables = {}
        self._commands  = {}

        # 任务：创建连接
        self._task_cc = self.loop.create_task(self.open(), name="open_connection")
        self._task_cc.add_done_callback(functools.partial(self._connection_created))

    async def open(self):
        "异步非阻塞方式创建远程连接"
        def _protocol_factory():
            return MudClientProtocol(
                self.loop, 
                self.encoding, 
                self.encoding_errors,
                self.clientwidth,
                self.clientheight
                )

        transport, protocol = await self.loop.create_connection(_protocol_factory, self.host, self.port)
        return transport, protocol

    def _connection_created(self, task):
        "远程连接创建成功时的回调"
        self._task_cc = None    # 取消引用，待自动垃圾回收
        if task.done() and not task.exception():
            transport, protocol = task.result()
            self.transport = transport
            self.protocol  = protocol
            self.reader    = protocol.reader
            self.writer    = protocol.writer

            self._task_rd  = self.loop.create_task(self.readline(), name = "remote_read")            
            self.state     = "RUNNING"
            self.app.activate_session(self)

            # if self.host == "pkuxkx.net":
            #     self.config = pkuxkx(self)
                
        else:
            #self.log.error("创建连接过程中发生错误，错误信息为：{%r}" % task.exception())
            self.app.info("创建连接过程中发生错误，错误信息为 %r " % task.exception())
            self.close()

    def _cleansession(self):
        try:
            self._tasks.clear()
            self._timers.clear()
            self._triggers.clear()
            self._aliases.clear()
            self._variables.clear()
            self._commands.clear()
        except asyncio.CancelledError:
            pass

    def loadconfig(self, module):
        try:
            self.config_name = module

            if hasattr(self, "cfg_module") and self.cfg_module:
                del self.cfg_module
                self._cleansession()

            self.cfg_module = importlib.import_module(module)
            self.config = self.cfg_module.Configuration(self)
            self.app.info(f"配置模块 {module} 加载完成.")
        except Exception as e:
            import traceback
            self.app.error(f"配置模块 {module} 加载失败，异常为 {e}, 类型为 {type(e)}.")
            self.app.error(f"异常追踪为： {traceback.format_exc()}")

        
    def reload(self):
        if hasattr(self, "config_name"):
            try:
                del self.config
                self._cleansession()
                self.cfg_module = importlib.reload(self.cfg_module)
                self.config = self.cfg_module.Configuration(self)
                self.app.info(f"配置模块 {self.cfg_module} 重新加载完成.")
            except:
                self.app.error(f"配置模块 {self.cfg_module} 重新加载失败.")
        else:
            self.app.error(f"原先未加载过配置模块，怎么能重新加载！")

    async def readline(self):
        "远程服务器读取数据并进行处理"
        while not self.reader.at_eof():
            # 输出到终端
            raw_line = await self.reader.readline()
            if self.active:
                self.terminal.write(raw_line)
                await self.terminal.drain()
            else:
                # 未激活时，不输出到终端显示，保存到背景缓冲
                self._bglines.append(raw_line)
                pass
                #self.app.info("session未被激活")

            # 触发器处理
            # 触发器触发时的回调函数都是保存在触发器类型实例本身的，因此当执行trymatch时，会自动调用回调函数
            tri_line = self.getPlainText(raw_line, True)

            if self.app.logdata:
                self.app.rawlogger.info(raw_line)
                self.app.plainlogger.info(tri_line + self.newline)

            all_tris = list(self._triggers.values())
            all_tris.sort(key = lambda tri: tri.priority)
            for tri in all_tris:
                #tri = Trigger()
                if isinstance(tri, Trigger) and tri.enabled:
                    if tri.raw:
                        state = tri.match(raw_line)
                    else:
                        state = tri.match(tri_line)

                    if state.result == Trigger.SUCCESS:
                        if tri.oneShot:                     # 仅执行一次的trigger，匹配成功后，删除该Trigger（从触发器列表中移除）
                            self._triggers.pop(tri.id)

                        if not tri.keepEval:                # 非持续匹配的trigger，匹配成功后停止检测后续Trigger
                            break
                        else:
                            pass
                
        self.close()

    def listgmcp(self):
        "返回当前GMCP列表中的所有内容"
        return self.reader.list_gmcp()

    async def readgmcp(self, key):
        "返回当前GMCP列表中的指定key内容（仅当其更新后）"
        return await self.reader.read_gmcp(key)

    def writeline(self, line: str):
        """
        向服务器写入一行，会自动添加换行符。
        对于使用分隔符隔开的，会分成多行发送。
        此函数除了分割行之外，不会对内容进行解析
        """
        def write_one_line(ln):
            self.writer.write(line.encode(self.encoding, self.encoding_errors))
            self.writer.write(self.newline.encode(self.encoding, self.encoding_errors))

        #asyncio.StreamWriter.write()
        if self.seperator in line:          # 多个命令集合
            lines = line.split(self.seperator)
            for ln in lines:
                write_one_line(ln)
        else:
            write_one_line(line)

    async def exec_command_async(self, line: str, *args, **kwargs):
        """
        异步执行MUD命令，是exec_command的异步实现
        """
        async def exec_one_command_async(cmd):
            "执行分离后的单个MUD Command/Alias"

            # 先判断是否是命令
            isNotCmd = True
            for command in self._commands.values():
                if isinstance(command, Command) and command.enabled:
                    state = command.match(cmd)
                    if state.result == Command.SUCCESS:
                        # 命令的任务名称采用命令id，以便于后续处理
                        cmd_task = asyncio.create_task(command.execute(cmd), name = "task-{0}".format(command.id))
                        self._tasks.append(cmd_task)
                        
                        await cmd_task              # 这一句是单命令执行的异步唯一变化，即如果是Command，则需异步等待Command执行完毕
                        isNotCmd = False
                        break

            # 再判断是否是别名
            if isNotCmd:
                notAlias = True
                for alias in self._aliases.values():
                    if isinstance(alias, Alias) and alias.enabled: 
                        state = alias.match(cmd)
                        if state.result == Alias.SUCCESS:
                            notAlias = False
                            break

                # 都不是则是普通命令，直接发送
                if notAlias:
                    self.writeline(cmd)

        
        ## 以下为函数执行本体
        self.clean_finished_tasks()

        if self.seperator in line:          # 多个命令集合
            cmds = line.split(self.seperator)
            for cmd in cmds:
                await exec_one_command_async(cmd)           # 这一句是异步变化，修改为异步等待Command执行完毕
                await asyncio.sleep(0.1)                    # 异步命令，在多个命令中插入0.1s的等待
        else:
            await exec_one_command_async(line)              # 这一句是异步变化，修改为异步等待Command执行完毕


    def exec_command(self, line: str, *args, **kwargs):
        """
        执行MUD命令。多个命令可以用分隔符隔开。
        此函数中，多个命令是一次性发送到服务器的，并未进行等待确认上一条命令执行完毕
        本函数和writeline的区别在于，本函数会先进行Command和Alias解析，若不是再使用writeline发送
        当line不包含Command和Alias时，等同于writeline
        """
        def exec_one_command(cmd):
            "执行分离后的单个MUD Command/Alias"

            # 先判断是否是命令
            isNotCmd = True
            for command in self._commands.values():
                if isinstance(command, Command) and command.enabled:
                    state = command.match(cmd)
                    if state.result == Command.SUCCESS:
                        # 命令的任务名称采用命令id，以便于后续处理
                        cmd_task = asyncio.create_task(command.execute(cmd), name = "task-{0}".format(command.id))
                        self._tasks.append(cmd_task)
                        isNotCmd = False
                        break

            # 再判断是否是别名
            if isNotCmd:
                notAlias = True
                for alias in self._aliases.values():
                    if isinstance(alias, Alias) and alias.enabled: 
                        state = alias.match(cmd)
                        if state.result == Alias.SUCCESS:
                            notAlias = False
                            break

                # 都不是则是普通命令，直接发送
                if notAlias:
                    self.writeline(cmd)

        
        ## 以下为函数执行本体
        self.clean_finished_tasks()

        if self.seperator in line:          # 多个命令集合
            cmds = line.split(self.seperator)
            for cmd in cmds:
                exec_one_command(cmd)
        else:
            exec_one_command(line)



    def exec_command_after(self, wait: float, line: str):
        "延时一段时间之后，执行命令(exec_command)"
        delay_task = asyncio.create_task(asyncio.sleep(wait))
        delay_task.add_done_callback(functools.partial(self.exec_command, line))
        self._tasks.append(delay_task)

    def clean_finished_tasks(self):
        "清理已完成的任务"
        for task in self._tasks:
            if isinstance(task, asyncio.Task) and task.done():
                self._tasks.remove(task)

    def activate(self):
        "激活本会话，即将本会话设置为当前会话。同时，返回会话本身。"
        self.active = True

        # 将背景数据一次性写入终端，并清空背景数据
        if len(self._bglines) > 0:
            self.terminal.writelines(self._bglines, True)
            self._bglines.clear()

        return self

    def deactivate(self):
        "取消激活本会话，将当前会话设置为后台。同时，返回会话本身。"
        self.active = False
        return self

    def is_active(self):
        "返回本会话是否激活。激活状态与否，仅影响是否向控制台输出信息"
        return self.state

    def close(self):
        "关闭本会话, 并从app的会话清单中移除本会话"
        self.state = "END"
        self.active = False
        #if not self._task_rd.done():
        if hasattr(self,"_task_rd") and self._task_rd:
            self._task_rd.cancel("宿主要求退出，任务中止. ")
            self._task_rd = None

        for task in self._tasks:
            if isinstance(task, asyncio.Task) and (not task.done()):
                task.cancel("session closed.")

        for timer in self._timers.values():
            if isinstance(timer, Timer):
                timer.enabled = False

        self._tasks.clear()
        self._aliases.clear()
        self._triggers.clear()
        self._commands.clear()
        self._timers.clear()

        self.app.info("远程服务器断开，将自动关闭session")
        self.app.remove_session(self)

    def getPlainText(self, rawText: str, trim_newline = False) -> str:
        "将带有VT100或者MXP转义字符的字符串转换为正常字符串（删除所有转义）"
        plainText = self._esc_regx.sub("", rawText)
        if trim_newline:
            plainText = plainText.rstrip("\n").rstrip("\r")

        return plainText
    
    def getUniqueNumber(self):
        "获取本session中的唯一编号"
        self._uid += 1
        return self._uid

    def getUniqueID(self, prefix):
        "根据唯一编号获取本session中的唯一名称, 格式为: prefix_uid"
        return "{0}_{1}".format(prefix, self.getUniqueNumber())

    def enableGroup(self, group: str, enabled = True):
        "使能或禁用Group中所有对象"
        for ali in self._aliases.values():
            if isinstance(ali, Alias) and ali.group == group:
                ali.enabled = enabled

        for tri in self._triggers.values():
            if isinstance(tri, Trigger) and tri.group == group:
                tri.enabled = enabled

        for cmd in self._commands.values():
            if isinstance(cmd, Command) and cmd.group == group:
                cmd.enabled = enabled

        for tmr in self._timers.values():
            if isinstance(cmd, Timer) and tmr.group == group:
                tmr.enabled = enabled

    ## ##################
    ## 别名Alias 处理
    ## ##################
    def addAliases(self, alis: dict):
        """将系列别名添加到session"""
        self._aliases.update(alis)

    def addAlias(self, ali: Alias):
        """将单个别名添加到session。若存在同id的，则会替换"""
        self._aliases[ali.id] = ali

    def delAlias(self, id):
        """删除指定id的alias"""
        if id in self._aliases.keys():
            self._aliases.pop(id)

    ## ##################
    ## 触发器Trigger 处理
    ## ##################
    def addTriggers(self, tris: dict):
        """将系列触发器添加到session"""
        self._triggers.update(tris)

    def addTrigger(self, tri: Trigger):
        """将单个触发器添加到session。若存在同id的，则会替换"""
        self._triggers[tri.id] = tri

    def delTrigger(self, id):
        """删除指定id的trigger"""
        if id in self._triggers.keys():
            self._triggers.pop(id)

    ## ##################
    ## 命令 Command 处理
    ## ##################
    def addCommands(self, cmds: dict):
        """将系列命令添加到session"""
        self._commands.update(cmds)

    def addCommand(self, cmd: Command):
        """将单个命令添加到session。若存在同id的，则会替换"""
        self._commands[cmd.id] = cmd

    def delCommand(self, id):
        """删除指定id的command"""
        if id in self._commands.keys():
            self._commands.pop(id)

    ## ##################
    ## 定时器 Timer 处理
    ## ##################
    def addTimers(self, tms: dict):
        """将系列定时器添加到session"""
        self._timers.update(tms)

    def addTimer(self, timer: Timer):
        """将单个定时器添加到session。若存在同id的，则会替换"""
        self._timers[timer.id] = timer

    def delTimer(self, id):
        """删除指定id的timer"""
        if id in self._timers.keys():
            self._timers.pop(id)

    ## ###################
    ## 变量 Variables 处理
    ## ###################
    def setVariable(self, name, value):
        """设置一个变量的值"""
        assert isinstance(name, str), "name必须是一个字符串"
        self._variables[name] = value

    def getVariable(self, name, default = None):
        """获取一个变量的值. 待决定：当name指定的变量不存在时，是返回default还是抛出异常？当前为返回default"""
        assert isinstance(name, str), "name必须是一个字符串"
        return self._variables.get(name, default)
    
    def setVariables(self, names, values):
        """设置一组变量的值，names为名称元组，values为值元组"""
        assert isinstance(names, tuple) or isinstance(names, list), "names命名应为元组或列表，不接受其他类型"
        assert isinstance(values, tuple) or isinstance(values, list), "values值应为元组或列表，不接受其他类型"
        assert (len(names) > 0) and (len(values) > 0) and (len(names) == len(values)), "names与values应不为空，且长度相等"
        for index in range(0, len(names)):
            name  = names[index]
            value = values[index]
            self.setVariable(name, value)

    def getVariables(self, names):
        """获取一组变量的值，names为获取值的元组，返回values元组"""
        assert isinstance(names, tuple) or isinstance(names, list), "names命名应为元组或列表，不接受其他类型"
        assert len(names) > 0, "names应不为空"
        values = list()
        for name in names:
            value = self.getVariable(name)
            values.append(value)
        
        return tuple(values)
    
    def updateVariables(self, kvdict: dict):
        """使用dict字典更新变量值"""
        self._variables.update(kvdict)