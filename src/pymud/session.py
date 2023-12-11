import asyncio, logging, re, functools, math, importlib, json, os, pickle
from collections.abc import Iterable

from .extras import SessionBuffer, DotDict
from .protocol import MudClientProtocol
from .objects import Trigger, Alias, Command, Timer, SimpleAlias, SimpleTrigger, GMCPTrigger
from .settings import Settings


class Session:
    #_esc_regx = re.compile("\x1b\\[[^mz]+[mz]")
    _esc_regx = re.compile("\x1b\\[[\d;]+[abcdmz]", flags = re.IGNORECASE)

    _commands = (
        "connect",      # 连接到服务器

        "info",         # 输出蓝色info
        "warning",      # 输出黄色warning
        "error",        # 输出红色error
        "clear",        # 清除屏幕

        "test",         # 测试输出信息

        "wait",         # 等待指定毫秒数，与zmud使用相同
        "timer",        # 定时器
        "variable",     # 变量
        "alias",        # 别名
        "trigger",      # 触发器
        "global",       # PyMUD跨session全局变量

        "command",      # 命令
        
        "load",         # 加载脚本文件
        "reload",       # 重新加载脚本文件

        "save",         # 将动态运行信息保存到磁盘

        "gmcp",         # GMCP协议信息
        "num",          # 重复多次指令
        "repeat",       # 重复上一行输入的指令

        "replace",      # 替代显示的行
        "gag",          # 不显示对应行

        "message",      # 用弹出式对话框显示消息
    )

    _commands_alias = {
        "ali" : "alias",
        "cmd" : "command",
        "ti"  : "timer",
        "tri" : "trigger",
        "var" : "variable",
        "rep" : "repeat",
        "con" : "connect",
        "wa"  : "wait",
        "mess": "message",
        "action": "trigger",
        "cls" : "clear",
    }

    def __init__(self, app, name, host, port, encoding = None, after_connect = None, **kwargs):
        self.log = logging.getLogger("pymud.Session")
        self.application = app
        self.name = name
        self._transport = None
        self._protocol  = None
        self.state      = "INITIALIZED"
        self._eof       = False
        self._uid       = 0

        self._auto_script = kwargs.get("script", None)

        self._cmds_handler = dict()                         # 支持的命令的处理函数字典
        for cmd in self._commands:
            handler = getattr(self, f"handle_{cmd}", None)
            self._cmds_handler[cmd] = handler

        self.seperator   = Settings.client["seperator"] or ";"
        self.newline     = Settings.server["newline"] or "\n"
        self.encoding    = Settings.server["default_encoding"]
        self.newline_cli = Settings.client["newline"] or "\n"

        self.last_command = ""
        
        self.buffer     = SessionBuffer()
        self.buffer_pos_end   = 0                           # 标注最后位置光标指针
        self.buffer_pos_view  = 0                           # 标注查看位置光标指针
        self.buffer_pos_view_line = -1
        self.showHistory      = False                       # 是否显示历史

        self._status_maker = None                           # 创建状态窗口的函数（属性）
        self.display_line  = ""

        self.initialize()

        self.host = host
        self.port = port
        self.encoding = encoding or self.encoding
        self.after_connect = after_connect

        if Settings.client["auto_connect"]:
            self.open()

    def initialize(self):
        self._line_buffer = bytearray()
        
        self._triggers = DotDict()
        self._aliases  = DotDict()
        self._commands = DotDict()
        self._timers   = DotDict()
        self._gmcp     = DotDict()

        self._variables = DotDict()

        self._tasks    = []

        self._command_history = []

    def open(self):
        self.clean()
        asyncio.ensure_future(self.connect())

    async def connect(self):
        "异步非阻塞方式创建远程连接"
        def _protocol_factory():
            return MudClientProtocol(self, onDisconnected = self.onDisconnected)
        
        try:
            self.loop = asyncio.get_running_loop()
            transport, protocol = await self.loop.create_connection(_protocol_factory, self.host, self.port)
            
            self._transport = transport
            self._protocol  = protocol
            self._state     = "RUNNING"
            self.initialize()

            self.onConnected()

        except Exception as exc:
            self.error("创建连接过程中发生错误，错误信息为 %r " % exc)
            self._state     = "EXCEPTION"

    def onConnected(self):
        if isinstance(self.after_connect, str):
            self.writeline(self.after_connect)
            if self._auto_script:
                self.handle_load(self._auto_script)
            
            file = f"{self.name}.mud"
            if os.path.exists(file):
                with open(file, "rb") as fp:
                    #vars = json.load(fp)
                    vars = pickle.load(fp)
                    self._variables.update(vars)
                    self.info(f"自动从{file}中加载保存变量成功")

    def disconnect(self):
        if self.connected:
            self.write_eof()

            # 断开时自动保存变量数据
            self.handle_save()

    def onDisconnected(self, protocol):
        # 断开时自动保存变量数据
        self.handle_save()

    @property
    def connected(self):
        "返回服务器端连接状态"
        if self._protocol:
            con = self._protocol.connected
        else:
            con = False

        return con

    @property
    def duration(self):
        "返回服务器端连接的时间，以秒为单位"
        dura = 0
        if self._protocol and self._protocol.connected:
            dura = self._protocol.duration

        return dura

    @property
    def status_maker(self):
        return self._status_maker
    
    @status_maker.setter
    def status_maker(self, value):
        if callable(value):
            self._status_maker = value

    @property
    def vars(self):
        "本会话变量的辅助访问器"
        return self._variables

    @property
    def globals(self):
        "全局变量的辅助访问器"
        return self.application.globals

    @property
    def tris(self):
        "本回话的触发器辅助访问器"
        return self._triggers

    @property
    def alis(self):
        "本回话的别名辅助访问器"
        return self._aliases
    
    @property
    def cmds(self):
        "本回话的命令辅助访问器"
        return self._commands

    @property
    def timers(self):
        "本回话的定时器辅助访问器"
        return self._timers

    @property
    def gmcp(self):
        "本回话的GMCP辅助访问器"
        return self._gmcp

    def get_status(self):
        text = f"这是一个默认的状态窗口信息\n会话: {self.name} 连接状态: {self.connected}"
        if callable(self._status_maker):
            text = self._status_maker()
            
        return text

    def getPlainText(self, rawText: str, trim_newline = False) -> str:
        "将带有VT100或者MXP转义字符的字符串转换为正常字符串（删除所有转义）"
        plainText = self._esc_regx.sub("", rawText)
        if trim_newline:
            plainText = plainText.rstrip("\n").rstrip("\r")

        return plainText

    def writetobuffer(self, data, newline = False):
        "将数据写入到用于本地显示的缓冲中"
        self.buffer.insert_text(data)

        if newline:
            self.buffer.insert_text(self.newline_cli)

    def feed_data(self, data) -> None:
        "永远只会传递1个字节的数据，以bytes形式"
        self._line_buffer.extend(data)

        if (len(data) == 1) and (data[0] == ord("\n")):
            self.go_ahead()

    def feed_eof(self) -> None:
        self._eof = True
        if self.connected:
            self._transport.write_eof()
        self.state = "DISCONNECTED"
        self.log.info(f"服务器断开连接! {self._protocol.__repr__}")
    
    def feed_gmcp(self, name, value) -> None:
        if name in self._gmcp.keys():
            gmcp = self._gmcp[name]
            if isinstance(gmcp, GMCPTrigger):
                gmcp(value)

    def feed_msdp(self, name, value) -> None:
        pass

    def feed_mssp(self, name, value) -> None:
        pass

    def go_ahead(self) -> None:
        "把当前接收缓冲内容放到显示缓冲中"
        raw_line = self._line_buffer.decode(self.encoding, Settings.server["encoding_errors"])
        tri_line = self.getPlainText(raw_line, trim_newline = True)
        self._line_buffer.clear()

        # MXP SUPPORT
        # 目前只有回复功能支持，还没有对内容进行解析，待后续完善
        if Settings.server["MXP"]:
            if raw_line == '\x1b[1z<SUPPORT>\r\n':
                self.write(b"\x1b[1z<SUPPORTS>")
            else:
                #self.write(b"\x1b[0z")
                self.warning("MXP支持尚未开发，请暂时不要打开MXP支持设置")
        
        # 全局变量%line
        self.setVariable("%line", tri_line)
        # 全局变量%raw
        self.setVariable("%raw", raw_line.rstrip("\n").rstrip("\r"))

        # 此处修改，为了处理#replace和#gag命令
        #self.writetobuffer(raw_line)
        #self._line_buffer.clear()
        # 将显示行数据暂存到session的display_line中，可以由trigger改变显示内容
        self.display_line = raw_line

        all_tris = list(self._triggers.values())
        all_tris.sort(key = lambda tri: tri.priority)

        for tri in all_tris:
            if isinstance(tri, Trigger) and tri.enabled:
                if tri.raw:
                    state = tri.match(raw_line, docallback = True)
                else:
                    state = tri.match(tri_line, docallback = True)

                if state.result == Trigger.SUCCESS:
                    if tri.oneShot:                     # 仅执行一次的trigger，匹配成功后，删除该Trigger（从触发器列表中移除）
                        self._triggers.pop(tri.id)

                    if not tri.keepEval:                # 非持续匹配的trigger，匹配成功后停止检测后续Trigger
                        break
                    else:
                        pass

        # 将数据写入缓存添加到此处
        if len(self.display_line) > 0:
            self.writetobuffer(self.display_line)

    def set_exception(self, exc: Exception):
        self.error(f"连接过程中发生异常，异常信息为： {exc}")
        pass

    def create_task(self, coro, *args, name: str = None) -> asyncio.Task:
        task = asyncio.create_task(coro, name = name)
        self._tasks.append(task)
        return task

    def remove_task(self, task: asyncio.Task, msg = None):
        result = task.cancel(msg)
        if task in self._tasks:
            self._tasks.remove(task)
        return result

    def clean_finished_tasks(self):
        "清理已经完成的任务"
        for task in self._tasks:
            if isinstance(task, asyncio.Task) and task.done():
                self._tasks.remove(task)

    def write(self, data) -> None:
        "向服务器写入数据（RAW格式字节数组/字节串）"
        if self._transport and not self._transport.is_closing():
            self._transport.write(data)
    
    def writeline(self, line: str) -> None:
        "向服务器中写入一行。如果使用;分隔（使用Settings.client.seperator指定）的多个命令，将逐行写入"
        if self.seperator in line:
            lines = line.split(self.seperator)
            for ln in lines:
                cmd = ln + self.newline
                self.write(cmd.encode(self.encoding, Settings.server["encoding_errors"]))
                
                if Settings.client["echo_input"]:
                    self.writetobuffer(f"\x1b[32m{cmd}\x1b[0m")

        else:
            cmd = line + self.newline
            self.write(cmd.encode(self.encoding, Settings.server["encoding_errors"]))

            #if Settings.client["echo_input"]:
            if Settings.client["echo_input"] and (len(cmd) > len(self.newline)):        # 修改2023-12-3， 向服务器发送空回车时，不回显
                self.writetobuffer(f"\x1b[32m{cmd}\x1b[0m")
    
    def exec_command(self, line: str, *args, **kwargs) -> None:
        """
        执行MUD命令。多个命令可以用分隔符隔开。
        此函数中，多个命令是一次性发送到服务器的，并未进行等待确认上一条命令执行完毕
        本函数和writeline的区别在于，本函数会先进行Command和Alias解析，若不是再使用writeline发送
        当line不包含Command和Alias时，等同于writeline
        """
        def exec_one_command(cmd):
            "执行分离后的单个MUD Command/Alias"
            # 先判断是否是命令
            self._command_history.append(cmd)
            isNotCmd = True
            for command in self._commands.values():
                if isinstance(command, Command) and command.enabled:
                    state = command.match(cmd)
                    if state.result == Command.SUCCESS:
                        # 命令的任务名称采用命令id，以便于后续查错
                        self.create_task(command.execute(cmd), name = "task-{0}".format(command.id))
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
        delay_task = self.create_task(asyncio.sleep(wait))
        delay_task.add_done_callback(functools.partial(self.exec_command, line))

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
                        # 这一句是单命令执行的异步唯一变化，即如果是Command，则需异步等待Command执行完毕
                        await self.create_task(command.execute(cmd), name = "task-{0}".format(command.id))
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
                if Settings.client["interval"] > 0:
                    await asyncio.sleep(Settings.client["interval"] / 1000.0)
        else:
            await exec_one_command_async(line)              # 这一句是异步变化，修改为异步等待Command执行完毕

    def write_eof(self) -> None:
        self._transport.write_eof()
    
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

        for gmcp in self._gmcp.values():
            if isinstance(gmcp, GMCPTrigger) and gmcp.group == group:
                gmcp.enabled = enabled        

    def _addObjects(self, objs: dict, cls: type):
        if cls == Alias:
            self._aliases.update(objs)
        elif cls == Command:
            self._commands.update(objs)
        elif cls == Trigger:
            self._triggers.update(objs)
        elif cls == Timer:
            self._timers.update(objs)
        elif cls == GMCPTrigger:
            self._gmcp.update(objs)

    def _addObject(self, obj, cls: type):
        if type(obj) == cls:
            if cls == Alias:
                self._aliases[obj.id] = obj
            elif cls == Command:
                self._commands[obj.id] = obj
            elif cls == Trigger:
                self._triggers[obj.id] = obj
            elif cls == Timer:
                self._timers[obj.id] = obj
            elif cls == GMCPTrigger:
                self._gmcp[obj.id] = obj

    def _delObject(self, id, cls: type):
        if cls == Alias:
            self._aliases.pop(id, None)
        elif cls == Command:
            self._commands.pop(id, None)
        elif cls == Trigger:
            self._triggers.pop(id, None)
        elif cls == Timer:
            self._timers.pop(id, None)
        elif cls == GMCPTrigger:
            self._gmcp.pop(id, None)

    def addAliases(self, alis: dict):
        "向会话中增加多个别名"
        self._addObjects(alis, Alias)

    def addCommands(self, cmds: dict):
        "向会话中增加多个命令"
        self._addObjects(cmds, Command)

    def addTriggers(self, tris: dict):
        "向会话中增加多个触发器"
        self._addObjects(tris, Trigger)

    def addGMCPs(self, gmcps: dict):
        "增加多个GMCP处理函数"
        self._addObjects(gmcps, GMCPTrigger)

    def addTimers(self, tis: dict):
        "向会话中增加多个定时器"
        self._addObjects(tis, Timer)

    def addAlias(self, ali: Alias):
        "向会话中增加别名"
        self._addObject(ali, Alias)

    def addCommand(self, cmd: Command):
        "向会话中增加命令"
        self._addObject(cmd, Command)

    def addTrigger(self, tri: Trigger):
        "向会话中增加触发器"
        self._addObject(tri, Trigger)

    def addTimer(self, ti: Timer):
        "向会话中增加定时器"
        self._addObject(ti, Timer)

    def addGMCP(self, gmcp: GMCPTrigger):
        "增加GMCP处理函数"
        self._addObject(gmcp, GMCPTrigger)

    def delAlias(self, ali: Alias):
        "从会话中移除别名"
        self._delObject(ali, Alias)

    def delCommand(self, cmd: Command):
        "从会话中移除命令"
        self._delObject(cmd, Command)

    def delTrigger(self, tri: Trigger):
        "从会话中移除触发器"
        self._delObject(tri, Trigger)

    def delTimer(self, ti: Timer):
        "从会话中移除定时器"
        self._delObject(ti, Timer)

    def delGMCP(self, gmcp: GMCPTrigger):
        "从会话中移除定时器"
        self._delObject(gmcp, GMCPTrigger)

    def replace(self, newstr):
        "替换当前行内容显示为newstr"
        self.handle_replace(newstr)

    ## ###################
    ## 变量 Variables 处理
    ## ###################
    def setVariable(self, name, value):
        """设置一个变量的值"""
        assert isinstance(name, str), "name必须是一个字符串"
        self._variables[name] = value

    def getVariable(self, name, default = None):
        """获取一个变量的值. 当name指定的变量不存在时，返回default"""
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

    ## ###################
    ## 全局变量 Globals 处理
    ## ###################
    def setGlobal(self, name, value):
        """设置一个全局变量的值"""
        assert isinstance(name, str), "name必须是一个字符串"
        self.application.set_globals(name, value)

    def getGlobal(self, name, default = None):
        """获取一个全局变量的值。当name指定的变量不存在时，返回default"""
        assert isinstance(name, str), "name必须是一个字符串"
        return self.application.get_globals(name, default)

    ## ###################
    ## 各类命令处理函数
    ## ###################
    def handle_input(self, *args):
        """处理命令行输入的#开头的命令"""
        asyncio.ensure_future(self.handle_input_async(*args))

    async def handle_input_async(self, code):
        """异步处理命令行输入的#开头的命令"""
        args = code[1:].split()        # 去除#号并分隔
        cmd = args[0]

        if cmd.isnumeric():
            times = 0
            try:
                times = int(cmd)
            except ValueError:
                pass

            if times > 0:
                self.handle_num(times, *args[1:])
            else:
                self.warning("#{num} {cmd}只能支持正整数!")
        
        else:
            cmd = cmd.lower()
            if cmd in self._commands_alias.keys():
                cmd = self._commands_alias[cmd]

            handler = self._cmds_handler.get(cmd, None)
            if handler and callable(handler):
                if cmd == "test":                       # 脚本测试时，要原样发送
                    self.handle_test(code[6:])          # 去除前面的#code 加空格共6个字符

                elif asyncio.iscoroutinefunction(handler):
                    await handler(*args[1:])
                else:
                    handler(*args[1:])
            else:
                self.warning("未识别的命令: %s" % " ".join(args))

    # async def handle_input_async(self, *args):
    #     """异步处理命令行输入的#开头的命令"""
    #     cmd = args[0]

    #     if cmd.isnumeric():
    #         times = 0
    #         try:
    #             times = int(cmd)
    #         except ValueError:
    #             pass

    #         if times > 0:
    #             self.handle_num(times, *args[1:])
    #         else:
    #             self.warning("#{num} {cmd}只能支持正整数!")
    #     else:
    #         cmd = cmd.lower()
    #         if cmd in self._commands_alias.keys():
    #             cmd = self._commands_alias[cmd]

    #         handler = self._cmds_handler.get(cmd, None)
    #         if handler and callable(handler):
    #             if asyncio.iscoroutinefunction(handler):
    #                 await handler(*args[1:])
    #             else:
    #                 handler(*args[1:])
    #         else:
    #             self.warning("未识别的命令: %s" % " ".join(args))

    async def handle_wait(self, msec: str, *args):
        "异步等待，毫秒后结束"
        if msec.isnumeric():
            wait_time = float(msec) / 1000.0
            await asyncio.sleep(wait_time)

    def handle_connect(self, *args):
        "\x1b[1m命令\x1b[0m: #connect|#con\n" \
        "      连接到远程服务器（仅当远程服务器未连接时有效）\n" \
        "\x1b[1m相关\x1b[0m: disconnect"

        if not self.connected:
            self.open()

        else:
            duration = self._protocol.duration
            hour = duration // 3600
            min  = (duration - 3600 * hour) // 60
            sec  = duration % 60
            time_msg = ""
            if hour > 0:
                time_msg += f"{hour} 小时"
            if min > 0:
                time_msg += f"{min} 分"
            time_msg += f"{math.ceil(sec)} 秒"

            self.info("已经与服务器连接了 {}".format(time_msg))

    def handle_variable(self, *args):
        "\x1b[1m命令\x1b[0m: #variable|#var\n" \
        "      不带参数时，列出当前会话中所有的变量清单\n" \
        "      带1个参数时，列出当前会话中名称为该参数的变量值\n" \
        "      带2个参数时，设置名称为该参数的变量值\n" \
        "\x1b[1m相关\x1b[0m: alias, trigger, command"

        if len(args) == 0:
            vars = self._variables
            vars_simple = {}
            vars_complex = {}
            for k, v in vars.items():
                # 不显示line, raw两个系统变量
                if k in ("%line", "%raw"):
                    continue

                if isinstance(v, Iterable) and not isinstance(v, str):
                    vars_complex[k] = v
                else:
                    vars_simple[k] = v

            width = self.application.get_width()
            
            title = f"  VARIABLE LIST IN SESSION {self.name}  "
            left = (width - len(title)) // 2
            right = width - len(title) - left
            self.writetobuffer("="*left + title + "="*right, newline = True)
            
            # print vars in simple, 每个变量占40格，一行可以多个变量
            var_count = len(vars_simple)
            var_per_line = (width - 2) // 40
            lines = math.ceil(var_count / var_per_line)
            left_space = (width - var_per_line * 40) // 2
            if left_space > 4:  left_space = 4
            
            var_keys = sorted(vars_simple.keys())

            for idx in range(0, lines):
                start = idx * var_per_line
                end   = (idx + 1) * var_per_line
                if end > var_count: end = var_count
                self.writetobuffer(" " * left_space)
                line_vars = var_keys[start:end]
                for var in line_vars:
                    self.writetobuffer("{0:>18} = {1:<19}".format(var, vars_simple[var].__repr__()))

                self.writetobuffer("", newline = True)

            # print vars in complex, 每个变量占1行
            for k, v in vars_complex.items():
                self.writetobuffer(" " * left_space)
                self.writetobuffer("{0:>18} = {1}".format(k, v.__repr__()), newline = True)

            self.writetobuffer("="*width, newline = True)

        elif len(args) == 1:
            if args[0] in self._variables.keys():
                obj = self.getVariable(args[0])
                self.info(f"变量{args[0]}值为:{obj}")
            else:
                self.warning(f"当前session中不存在名称为 {args[0]} 的变量")
            
        elif len(args) == 2:
            self.setVariable(args[0], args[1])

    def handle_global(self, *args):
        "\x1b[1m命令\x1b[0m: #global\n" \
        "      不带参数时，列出程序当前所有全局变量清单\n" \
        "      带1个参数时，列出程序当前名称我为该参数的全局变量值\n" \
        "      带2个参数时，设置名称为该全局变量的变量值\n" \
        "\x1b[1m相关\x1b[0m: variable"

        if len(args) == 0:
            vars = self.application.globals
            vars_simple = {}
            vars_complex = {}
            for k, v in vars.items():
                if isinstance(v, Iterable) and not isinstance(v, str):
                    vars_complex[k] = v
                else:
                    vars_simple[k] = v

            width = self.application.get_width()
            
            title = f" GLOBAL VARIABLES LIST "
            left = (width - len(title)) // 2
            right = width - len(title) - left
            self.writetobuffer("="*left + title + "="*right, newline = True)
            
            # print vars in simple, 每个变量占40格，一行可以多个变量
            var_count = len(vars_simple)
            var_per_line = (width - 2) // 40
            lines = math.ceil(var_count / var_per_line)
            left_space = (width - var_per_line * 40) // 2
            if left_space > 4:  left_space = 4
            
            var_keys = sorted(vars_simple.keys())

            for idx in range(0, lines):
                start = idx * var_per_line
                end   = (idx + 1) * var_per_line
                if end > var_count: end = var_count
                self.writetobuffer(" " * left_space)
                line_vars = var_keys[start:end]
                for var in line_vars:
                    self.writetobuffer("{0:>18} = {1:<19}".format(var, vars_simple[var].__repr__()))

                self.writetobuffer("", newline = True)

            # print vars in complex, 每个变量占1行
            for k, v in vars_complex.items():
                self.writetobuffer(" " * left_space)
                self.writetobuffer("{0:>18} = {1}".format(k, v.__repr__()), newline = True)

            self.writetobuffer("="*width, newline = True)

        elif len(args) == 1:
            var = args[0]
            if var in self.application.globals.keys():
                self.info("{0:>18} = {1:<19}".format(var, self.application.get_globals(var).__repr__()), "全局变量")
            else:
                self.info("全局空间不存在名称为 {} 的变量".format(var), "全局变量")
            
        elif len(args) == 2:
            self.application.set_globals(args[0], args[1])

    def _handle_objs(self, name: str, objs: dict, *args):
        if len(args) == 0:
            width = self.application.get_width()
            
            title = f"  {name.upper()} LIST IN SESSION {self.name}  "
            left = (width - len(title)) // 2
            right = width - len(title) - left
            self.writetobuffer("="*left + title + "="*right, newline = True)

            for id in sorted(objs.keys()):
                self.writetobuffer("  %r" % objs[id], newline = True)

            self.writetobuffer("="*width, newline = True)

        elif len(args) == 1:
            if args[0] in objs.keys():
                obj = objs[args[0]]
                self.info(obj.__detailed__())
            else:
                self.warning(f"当前session中不存在key为 {args[0]} 的 {name}, 请确认后重试.")

        elif len(args) == 2:
            # 当第一个参数为对象obj名称时，对对象进行处理
            if args[0] in objs.keys():
                obj = objs[args[0]]
                if args[1] == "on":
                    obj.enabled = True
                    self.info(f"对象 {obj} 的使能状态已打开.")
                elif args[1] == "off":
                    obj.enabled = False
                    self.info(f"对象 {obj} 的使能状态已禁用.")
                else:
                    self.error(f"#{name.lower()}命令的第二个参数仅能接受on或off")
            
            # 当第一个参数为不是对象obj名称时，创建新对象
            else:
                name = name.lower()
                if name == "alias":
                    ali = SimpleAlias(self, args[0], args[1])
                    self.addAlias(ali)
                    self.info("创建Alias {} 成功: {}".format(ali.id, ali.__repr__()))
                elif name == "trigger":
                    tri = SimpleTrigger(self, args[0], args[1])
                    self.addTrigger(tri)
                    self.info("创建Trigger {} 成功: {}".format(tri.id, tri.__repr__()))

    def handle_alias(self, *args):
        "\x1b[1m命令\x1b[0m: #alias|#ali\n" \
        "      不指定参数时, 列出当前会话中所有的别名清单\n" \
        "      为一个参数时, 该参数应为某个Alias的id, 可列出Alias的详细信息\n" \
        "      为一个参数时, 第一个参数应为Alias的id, 第二个应为on/off, 可修改Alias的使能状态\n" \
        "\x1b[1m相关\x1b[0m: variable, trigger, command, timer"

        self._handle_objs("Alias", self._aliases, *args)


    def handle_timer(self, *args):
        "\x1b[1m命令\x1b[0m: #timer|#tmr\n" \
        "      不指定参数时, 列出当前会话中所有的定时器清单\n" \
        "      为一个参数时, 该参数应为某个Timer的id, 可列出Timer的详细信息\n" \
        "      为一个参数时, 第一个参数应为Timer的id, 第二个应为on/off, 可修改Timer的使能状态\n" \
        "\x1b[1m相关\x1b[0m: variable, alias, trigger, command"
   
        self._handle_objs("Timer", self._timers, *args)

    def handle_command(self, *args):
        "\x1b[1m命令\x1b[0m: #command|#cmd\n" \
        "      不指定参数时, 列出当前会话中所有的命令清单\n" \
        "      为一个参数时, 该参数应为某个Command的id, 可列出Command的详细信息\n" \
        "      为一个参数时, 第一个参数应为Command的id, 第二个应为on/off, 可修改Command的使能状态\n" \
        "\x1b[1m相关\x1b[0m: alias, variable, trigger, timer"

        self._handle_objs("Command", self._commands, *args)

    def handle_trigger(self, *args):
        "\x1b[1m命令\x1b[0m: #trigger|#tri\n" \
        "      不指定参数时, 列出当前会话中所有的触发器清单\n" \
        "      为一个参数时, 该参数应为某个Trigger的id, 可列出Trigger的详细信息\n" \
        "      为一个参数时, 第一个参数应为Trigger的id, 第二个应为on/off, 可修改Trigger的使能状态\n" \
        "\x1b[1m相关\x1b[0m: alias, variable, command, timer"
                
        self._handle_objs("Trigger", self._triggers, *args)


    def handle_repeat(self, *args):
        "\x1b[1m命令\x1b[0m: #repeat|#rep\n" \
        "      重复向session输出上一次人工输入的命令 \n" \
        "\x1b[1m相关\x1b[0m: num"

        if self.connected and self.last_command:
            self.exec_command(self.last_command)
        else:
            self.info("当前会话没有连接或没有键入过指令，repeat无效")

    def handle_num(self, times, *args):
        "\x1b[1m命令\x1b[0m: #{num} {cmd}\n" \
        "      向session中输出{num}次{cmd} \n" \
        "      如: #3 drink jiudai, 表示连喝3次酒袋 \n" \
        "\x1b[1m相关\x1b[0m: repeat"
        
        if self.connected:
            if len(args) > 0:
                cmd = " ".join(args)
                for i in range(0, times):
                    self.exec_command(cmd)
        else:
            self.error("当前会话没有连接，指令无效")

    def handle_gmcp(self, *args):
        "\x1b[1m命令\x1b[0m: #gmcp {key}\n" \
        "      指定key时，显示由GMCP收到的key信息\n" \
        "      不指定key时，显示所有GMCP收到的信息\n" \
        "\x1b[1m相关\x1b[0m: 暂无"

        self._handle_objs("GMCPs", self._gmcp, *args)

    def handle_message(self, *args):
        "\x1b[1m命令\x1b[0m: #message|#mess {msg}\n" \
        "      使用弹出窗体显示信息\n" \
        "\x1b[1m相关\x1b[0m: 暂无"

        title = "来自会话 {} 的消息".format(self.name)
        
        new_args = []
        for item in args:
            if item[0] == "%":
                item_val = self.getVariable(item, "")
                new_args.append(item_val)
            # 非系统变量，@开头，在变量明前加@引用
            elif item[0] == "@":
                item_val = self.getVariable(item[1:], "")
                new_args.append(item_val)
            else:
                new_args.append(item)

        msg   = " ".join(new_args)
        self.application.show_message(title, msg, False)

    def clean(self):
        "清除会话有关信息"
        try:
            for task in self._tasks:
                if isinstance(task, asyncio.Task) and not task.done():
                    task.cancel("session exit.")

            self._tasks.clear()
            for tm in self._timers.values():
                tm.enabled = False
            self._timers.clear()
            self._triggers.clear()
            self._aliases.clear()

            # 重新加载脚本时，变量考虑保留
            #self._variables.clear()

            for cmd in self._commands:
                if isinstance(cmd, Command):
                    cmd.reset()
                    del cmd

            self._commands.clear()
            
        except asyncio.CancelledError:
            pass

    def handle_load(self, *args):
        "\x1b[1m命令\x1b[0m: #load {config}\n" \
        "      为当前session加载{config}指定的模块\n" \
        "\x1b[1m相关\x1b[0m: reload"

        if len(args) > 0:
            module = args[0]
            try:
                self.config_name = module

                if hasattr(self, "cfg_module") and self.cfg_module:
                    del self.cfg_module
                    self.clean()

                self.cfg_module = importlib.import_module(module)
                self.config = self.cfg_module.Configuration(self)
                self.info(f"配置模块 {module} 加载完成.")
            except Exception as e:
                import traceback
                self.error(f"配置模块 {module} 加载失败，异常为 {e}, 类型为 {type(e)}.")
                self.error(f"异常追踪为： {traceback.format_exc()}")

    def handle_reload(self, *args):
        "\x1b[1m命令\x1b[0m: #reload\n" \
        "      为当前session重新加载配置模块（解决配置模块文件修改后的重启问题）\n" \
        "\x1b[1m相关\x1b[0m: load"

        if hasattr(self, "config_name"):
            try:
                del self.config
                self.clean()
                self.cfg_module = importlib.reload(self.cfg_module)
                self.config = self.cfg_module.Configuration(self)
                self.info(f"配置模块 {self.cfg_module} 重新加载完成.")
            except:
                self.error(f"配置模块 {self.cfg_module} 重新加载失败.")
        else:
            self.error(f"原先未加载过配置模块，怎么能重新加载！")

    def handle_save(self, *args):
        "\x1b[1m命令\x1b[0m: #save\n" \
        "      将当前会话中的变量保存到文件，系统变量（即%开头的）除外 \n" \
        "      文件保存在当前目录下，文件名为 {会话名}.mud \n" \
        "\x1b[1m相关\x1b[0m: variable"
        file = f"{self.name}.mud"

        with open(file, "wb") as fp:
            saved = dict()
            saved.update(self._variables)
            # keys = list(saved.keys())
            # for key in keys:
            #     if key.startswith("%"):
            #         saved.pop(key)
            saved.pop("%line", None)
            saved.pop("%raw", None)
            saved.pop("%copy", None)
            pickle.dump(saved, fp)
            #json.dump(saved, fp)
            self.info(f"会话变量信息已保存到{file}")

    def handle_clear(self, *args):
        "\x1b[1m命令\x1b[0m: #clear #cls {msg}\n" \
        "      清屏命令，清除当前会话所有缓存显示内容\n" \
        "\x1b[1m相关\x1b[0m: connect, exit"
        self.buffer.text = ""

    def handle_test(self, *args):
        "\x1b[1m命令\x1b[0m: #test {msg}\n" \
        "      用于测试脚本的命令，会将msg发送并显示在session中，同时触发触发器\n" \
        "\x1b[1m相关\x1b[0m: trigger"
        "把当前接收缓冲内容放到显示缓冲中"

        line = "".join(args)
        if "\n" in line:
            lines = line.split("\n")
        else:
            lines = []
            lines.append(line)

        for raw_line in lines:
            #raw_line = "".join(args)
            tri_line = self.getPlainText(raw_line)

            all_tris = list(self._triggers.values())
            all_tris.sort(key = lambda tri: tri.priority)

            for tri in all_tris:
                if isinstance(tri, Trigger) and tri.enabled:
                    if tri.raw:
                        state = tri.match(raw_line, docallback = True)
                    else:
                        state = tri.match(tri_line, docallback = True)

                    if state.result == Trigger.SUCCESS:
                        self.info(f"TRIGGER {tri.id} 被触发", "PYMUD TRIGGER TEST")
                        if tri.oneShot:                     # 仅执行一次的trigger，匹配成功后，删除该Trigger（从触发器列表中移除）
                            self._triggers.pop(tri.id)

                        if not tri.keepEval:                # 非持续匹配的trigger，匹配成功后停止检测后续Trigger
                            break
                        else:
                            pass

            if len(raw_line) > 0:
                self.info(raw_line, "PYMUD TRIGGER TEST")

    def handle_replace(self, *args):
        "\x1b[1m命令\x1b[0m: #replace {msg}\n" \
        "      修改显示内容，将当前行原本显示内容替换为msg显示。不需要增加换行符\n" \
        "      注意：在触发器中使用。多行触发器时，替代只替代最后一行"
        "\x1b[1m相关\x1b[0m: gag"
        
        new_msg = ""
        if len(args) > 0:
            new_msg = args[0]
        
        if len(new_msg) > 0:
            new_msg += Settings.client["newline"]

        self.display_line = new_msg
        
    def handle_gag(self, *args):
        "\x1b[1m命令\x1b[0m: #gag\n" \
        "      在主窗口中不显示当前行\n" \
        "      注意：一旦当前行被gag之后，无论如何都不会再显示此行内容，但对应的触发器不会不生效"
        "\x1b[1m相关\x1b[0m: replace"
        self.display_line = ""

    def handle_info(self, *args):
        "\x1b[1m命令\x1b[0m: #info {msg}\n" \
        "      使用info输出一行, 主要用于测试\n" \
        "\x1b[1m相关\x1b[0m: warning, error"

        if len(args) > 0:
            self.info(" ".join(args))

    def handle_warning(self, *args):
        "\x1b[1m命令\x1b[0m: #warning {msg}\n" \
        "      使用warning输出一行, 主要用于测试\n" \
        "\x1b[1m相关\x1b[0m: info, error"
        
        if len(args) > 0:
            self.warning(" ".join(args))

    def handle_error(self, *args):
        "\x1b[1m命令\x1b[0m: #error {msg}\n" \
        "      使用error输出一行, 主要用于测试\n" \
        "\x1b[1m相关\x1b[0m: info, warning"
        
        if len(args) > 0:
            self.error(" ".join(args))

    def info2(self, msg, title = "PYMUD INFO", style = Settings.INFO_STYLE):
        self.writetobuffer("{}[{}] {}{}".format(style, title, msg, Settings.CLR_STYLE), newline = True)

    def info(self, msg, title = "PYMUD INFO", style = Settings.INFO_STYLE):
        "输出信息（蓝色），自动换行"
        self.info2(msg, title, style)

    def warning(self, msg, title = "PYMUD WARNING", style = Settings.WARN_STYLE):
        "输出警告（黄色），自动换行"
        self.info2(msg, title, style)

    def error(self, msg, title = "PYMUD ERROR", style = Settings.ERR_STYLE):
        "输出错误（红色），自动换行"
        self.info2(msg, title, style)