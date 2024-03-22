import asyncio, logging, re, math, os, pickle, datetime, importlib, importlib.util, sysconfig
from collections.abc import Iterable
from collections import OrderedDict

from .extras import SessionBuffer, DotDict, Plugin
from .protocol import MudClientProtocol
from .objects import Trigger, Alias, Command, Timer, SimpleAlias, SimpleTrigger, SimpleTimer, GMCPTrigger, CodeBlock, CodeLine
from .settings import Settings


class Session:
    """
    会话管理主对象，每一个角色的所有处理实现均在该类中实现。
    """
    #_esc_regx = re.compile("\x1b\\[[^mz]+[mz]")
    _esc_regx = re.compile("\x1b\\[[\d;]+[abcdmz]", flags = re.IGNORECASE)

    _sys_commands = (
        "help",
        "exit",
        "close",
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

        "task",         # 任务
        
        "modules",      # 模块清单
        "load",         # 加载模块
        "reload",       # 重新加载模块
        "unload",       # 卸载模块
        "reset",        # 复位并卸载所有脚本，清除所有内容（含变量?）
        "ignore",       # 忽略所有触发器

        "save",         # 将动态运行信息保存到磁盘

        "gmcp",         # GMCP协议信息
        "num",          # 重复多次指令
        "repeat",       # 重复上一行输入的指令

        "replace",      # 替代显示的行
        "gag",          # 不显示对应行

        "message",      # 用弹出式对话框显示消息

        "plugins",      # 插件
        "py",           # 直接执行python语句

        "all",          # 所有会话执行
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
        "mods": "modules",
        "ig"  : "ignore",
        "t+"  : "ignore",
        "t-"  : "ignore",
    }

    def __init__(self, app, name, host, port, encoding = None, after_connect = None, loop = None, **kwargs):
        self.pyversion = sysconfig.get_python_version()   
        self.loop = loop or asyncio.get_running_loop()    
        self.log = logging.getLogger("pymud.Session")
        self.application = app
        self.name = name
        self._transport = None
        self._protocol  = None
        self.state      = "INITIALIZED"
        self._eof       = False
        self._uid       = 0
        self._ignore    = False
        self._events    = dict()
        self._events["connected"]    = None
        self._events["disconnected"] = None

        self._auto_script = kwargs.get("scripts", None)

        self._cmds_handler = dict()                         # 支持的命令的处理函数字典
        for cmd in self._sys_commands:
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
        self._line_count      = 0                           # 快速访问行数
        self._status_maker = None                           # 创建状态窗口的函数（属性）
        self.display_line  = ""

        self.initialize()

        self.host = host
        self.port = port
        self.encoding = encoding or self.encoding
        self.after_connect = after_connect

        # 插件处置移动到 pymud.py 2024-3-22
        # for plugin in app.plugins.values():
        #     if isinstance(plugin, Plugin):
        #         plugin.onSessionCreate(self)

        self._modules = OrderedDict()

        # 将变量加载和脚本加载调整到会话创建时刻
        if Settings.client["var_autoload"]:
                file = f"{self.name}.mud"
                if os.path.exists(file):
                    with open(file, "rb") as fp:
                        try:
                            vars = pickle.load(fp)
                            self._variables.update(vars)
                            self.info(f"自动从{file}中加载保存变量成功")
                        except Exception as e:
                            self.warning(f"自动从{file}中加载变量失败，错误消息为： {e}")

        

        if self._auto_script:
            self.info(f"即将自动加载以下模块:{self._auto_script}")
            self.load_module(self._auto_script)

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
        asyncio.ensure_future(self.connect(), loop = self.loop)

    async def connect(self):
        "异步非阻塞方式创建远程连接"
        def _protocol_factory():
            return MudClientProtocol(self, onDisconnected = self.onDisconnected)
        
        try:
            #self.loop = asyncio.get_running_loop()
            transport, protocol = await self.loop.create_connection(_protocol_factory, self.host, self.port)
            
            self._transport = transport
            self._protocol  = protocol
            self._state     = "RUNNING"
            #self.initialize()

            self.onConnected()

        except Exception as exc:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.error(f"创建连接过程中发生错误, 错误发生时刻 {now}, 错误信息为 {exc}, ")
            self._state     = "EXCEPTION"

            if Settings.client["auto_reconnect"]:
                wait = Settings.client.get("reconnect_wait", 15)
                asyncio.ensure_future(self.reconnect(wait), loop = self.loop)

    async def reconnect(self, timeout = 15):
        self.info(f"{timeout}秒之后将自动重新连接...")
        await asyncio.sleep(timeout)
        await self.create_task(self.connect())

    def onConnected(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.info(f"{now}: 已成功连接到服务器")
        if isinstance(self.after_connect, str):
            self.writeline(self.after_connect)

        event_connected = self._events["connected"]
        if callable(event_connected):
            event_connected(self)

    def disconnect(self):
        if self.connected:
            self.write_eof()

            # 两次保存，删掉一次
            # # 断开时自动保存变量数据
            # if Settings.client["var_autosave"]:
            #     self.handle_save()

    def onDisconnected(self, protocol):
        # 断开时自动保存变量数据
        if Settings.client["var_autosave"]:
            self.handle_save()
        
        self.clean()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.info(f"{now}: 与服务器连接已断开")

        event_disconnected = self._events["disconnected"]
        if callable(event_disconnected):
            event_disconnected(self)

        if Settings.client["auto_reconnect"]:
            wait = Settings.client.get("reconnect_wait", 15)
            asyncio.ensure_future(self.reconnect(wait), loop = self.loop)

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
    def event_connected(self):
        return self._events["connected"]
    
    @event_connected.setter
    def event_connected(self, event):
        self._events["connected"] = event

    @property
    def event_disconnected(self):
        return self._events["disconnected"]
    
    @event_disconnected.setter
    def event_disconnected(self, event):
        self._events["disconnected"] = event

    @property
    def modules(self):
        "返回本会话加载的所有模块，类型为顺序字典"
        return self._modules

    @property
    def plugins(self):
        "返回PYMUD的插件清单辅助访问器"
        return self.application.plugins

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

        if len(data) > 0 and (data[-1] == "\n"):
            self._line_count += 1

        if newline:
            self.buffer.insert_text(self.newline_cli)
            self._line_count += 1

    def clear_half(self):
        "清除过多缓冲"
        if (self._line_count >= 2 * Settings.client["buffer_lines"]) and self.buffer.document.is_cursor_at_the_end:
            self._line_count = self.buffer.clear_half()

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
        nothandle = True
        if name in self._gmcp.keys():
            gmcp = self._gmcp[name]
            if isinstance(gmcp, GMCPTrigger):
                gmcp(value)
                nothandle = False

        if nothandle:
            self.info(f"{name}: {value}", "GMCP")

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
        # 将显示行数据暂存到session的display_line中，可以由trigger改变显示内容
        self.display_line = raw_line

        if not self._ignore:
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
            self.clear_half()
            self.writetobuffer(self.display_line)

    def set_exception(self, exc: Exception):
        self.error(f"连接过程中发生异常，异常信息为： {exc}")
        pass

    def create_task(self, coro, *args, name: str = None) -> asyncio.Task:
        if self.pyversion in ["3.7", "3.8", "3.9"]:
            task = self.loop.create_task(coro)
            #task = asyncio.create_task(coro)
        else:
            task = self.loop.create_task(coro, name = name)
            #task = asyncio.create_task(coro, name = name)
        self._tasks.append(task)
        return task

    def remove_task(self, task: asyncio.Task, msg = None):
        result = task.cancel()
        if task in self._tasks:
            self._tasks.remove(task)
        return result

    def clean_finished_tasks(self):
        "清理已经完成的任务"
        # for task in self._tasks:
        #     if isinstance(task, asyncio.Task) and task.done():
        #         self._tasks.remove(task)

        self._tasks = list((t for t in self._tasks if isinstance(t, asyncio.Task) and not t.done()))

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
    
    def exec(self, cmd: str, name = None, *args, **kwargs):
        """
        在名称为name的会话中使用exec_command执行MUD命令
        当不指定name时，在当前会话中执行。
        """
        name = name or self.name
        if name in self.application.sessions.keys():
            session = self.application.sessions[name]
            session.exec_command(cmd, *args, **kwargs)
        else:
            self.error(f"不存在名称为{name}的会话")

    def exec_code(self, cl: CodeLine, *args, **kwargs):
        """
        执行解析为CodeLine形式的MUD命令（必定为单个命令）
        这是新修改命令执行后的最核心执行函数，所有真实调用的起源
        """
        if cl.length == 0:
            self.writeline("")

        elif cl.code[0] == "#":
            ## handle # command codes
            cmd = cl.code[1]
            if cmd.isnumeric():
                times = 0
                try:
                    times = int(cmd)
                except ValueError:
                    pass

                if times > 0:
                    self.create_task(self.handle_num(times, code = cl, *args, **kwargs))
                else:
                    self.warning("#{num} {cmd}只能支持正整数!")
            
            elif cmd in self.application.sessions.keys():
                name = cmd
                if cl.length == 2:
                    self.application.activate_session(name)
                elif cl.length > 2:
                    sess_cmd  = " ".join(cl.code[2:])
                    session = self.application.sessions[name]
                    if len(sess_cmd) == 0:
                        session.writeline("")
                    else:
                        try:
                            cb = CodeBlock(sess_cmd)
                            cb.execute(session, *args, **kwargs)
                        except Exception as e:
                            session.exec_command(sess_cmd)
            
            else:
                if cmd in self._commands_alias.keys():
                    cmd = self._commands_alias[cmd]

                handler = self._cmds_handler.get(cmd, None)
                if handler and callable(handler):
                    if asyncio.iscoroutinefunction(handler):
                        self.create_task(handler(code = cl, *args, **kwargs))
                    else:
                        handler(code = cl, *args, **kwargs)
                else:
                    self.warning(f"未识别的命令: {cl.commandText}")

        else:
            cmdtext, code = cl.expand(self, *args, **kwargs)
            self.exec_text(cmdtext)

    async def exec_code_async(self, cl: CodeLine, *args, **kwargs):
        """
        执行解析为CodeLine形式的MUD命令（必定为单个命令）
        这是新修改命令执行后的最核心执行函数，所有真实调用的起源
        """
        if cl.length == 0:
            self.writeline("")

        elif cl.code[0] == "#":
            ## handle # command codes
            cmd = cl.code[1]
            if cmd.isnumeric():
                times = 0
                try:
                    times = int(cmd)
                except ValueError:
                    pass

                if times > 0:
                    await self.handle_num(times, code = cl, *args, **kwargs)
                else:
                    self.warning("#{num} {cmd}只能支持正整数!")
            
            elif cmd in self.application.sessions.keys():
                name = cmd
                sess_cmd  = " ".join(cl.code[2:])
                session = self.application.sessions[name]
                if len(sess_cmd) == 0:
                    session.writeline("")
                else:
                    try:
                        cb = CodeBlock(sess_cmd)
                        await cb.async_execute(session, *args, **kwargs)
                    except Exception as e:
                        await session.exec_command_async(sess_cmd)
            
            else:
                if cmd in self._commands_alias.keys():
                    cmd = self._commands_alias[cmd]

                handler = self._cmds_handler.get(cmd, None)
                if handler and callable(handler):
                    if asyncio.iscoroutinefunction(handler):
                        await handler(code = cl, *args, **kwargs)
                    else:
                        handler(code = cl, *args, **kwargs)
                else:
                    self.warning(f"未识别的命令: {cl.commandText}")

        else:
            cmdtext, code = cl.expand(self, *args, **kwargs)
            self.exec_text(cmdtext)
            
    def exec_text(self, cmdtext: str):
        """
        执行文本形式的MUD命令（必定为单个命令，且确定不是#开头的）
        """
        isNotCmd = True
        for command in self._commands.values():
            if isinstance(command, Command) and command.enabled:
                state = command.match(cmdtext)
                if state.result == Command.SUCCESS:
                    # 命令的任务名称采用命令id，以便于后续查错
                    self.create_task(command.execute(cmdtext), name = "task-{0}".format(command.id))
                    isNotCmd = False
                    break

        # 再判断是否是别名
        if isNotCmd:
            notAlias = True
            for alias in self._aliases.values():
                if isinstance(alias, Alias) and alias.enabled: 
                    state = alias.match(cmdtext)
                    if state.result == Alias.SUCCESS:
                        notAlias = False
                        break

            # 都不是则是普通命令，直接发送
            if notAlias:
                self.writeline(cmdtext)

        self.clean_finished_tasks()

    async def exec_text_async(self, cmdtext: str):
        isNotCmd = True
        for command in self._commands.values():
            if isinstance(command, Command) and command.enabled:
                state = command.match(cmdtext)
                if state.result == Command.SUCCESS:
                    # 命令的任务名称采用命令id，以便于后续查错
                    await self.create_task(command.execute(cmdtext), name = "task-{0}".format(command.id))
                    isNotCmd = False
                    break

        # 再判断是否是别名
        if isNotCmd:
            notAlias = True
            for alias in self._aliases.values():
                if isinstance(alias, Alias) and alias.enabled: 
                    state = alias.match(cmdtext)
                    if state.result == Alias.SUCCESS:
                        notAlias = False
                        break

            # 都不是则是普通命令，直接发送
            if notAlias:
                self.writeline(cmdtext)

    def exec_command(self, line: str, *args, **kwargs) -> None:
        """
        执行MUD命令。多个命令可以用分隔符隔开。
        此函数中，多个命令是一次性发送到服务器的，并未进行等待确认上一条命令执行完毕
        本函数和writeline的区别在于，本函数会先进行Command和Alias解析，若不是再使用writeline发送
        当line不包含Command和Alias时，等同于writeline
        """

        ## 以下为函数执行本体
        if (not "#" in line) and (not "@" in line) and (not "%" in line):
            cmds = line.split(self.seperator)
            for cmd in cmds:
                self.exec_text(cmd)

        else:
            cb = CodeBlock(line)
            cb.execute(self)

    def exec_command_after(self, wait: float, line: str):
        "延时一段时间之后，执行命令(exec_command)"
        async def delay_task():
            await asyncio.sleep(wait)
            self.exec_command(line)
        
        self.create_task(delay_task())

    async def exec_command_async(self, line: str, *args, **kwargs):
        """
        异步执行MUD命令，是exec_command的异步实现
        异步时，多个命令是逐个发送到服务器的，每一命令都等待确认上一条命令执行完毕，且多命令之间会插入interval时间等待
        """

        ## 以下为函数执行本体
        if (not "#" in line) and (not "@" in line) and (not "%" in line):
            cmds = line.split(self.seperator)
            for cmd in cmds:
                await self.exec_text_async(cmd)
                if Settings.client["interval"] > 0:
                    await asyncio.sleep(Settings.client["interval"] / 1000.0)
        else:
            cb = CodeBlock(line)
            await cb.async_execute(self)

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
        "使能或禁用Group中所有对象, 返回组内对象个数。顺序为：别名，触发器，命令，定时器，GMCP"
        counts = [0, 0, 0, 0, 0]
        for ali in self._aliases.values():
            if isinstance(ali, Alias) and (ali.group == group):
                ali.enabled = enabled
                counts[0] += 1

        for tri in self._triggers.values():
            if isinstance(tri, Trigger) and (tri.group == group):
                tri.enabled = enabled
                counts[1] += 1

        for cmd in self._commands.values():
            if isinstance(cmd, Command) and (cmd.group == group):
                cmd.enabled = enabled
                counts[2] += 1

        for tmr in self._timers.values():
            if isinstance(tmr, Timer) and (tmr.group == group):
                tmr.enabled = enabled
                counts[3] += 1

        for gmcp in self._gmcp.values():
            if isinstance(gmcp, GMCPTrigger) and (gmcp.group == group):
                gmcp.enabled = enabled       
                counts[4] += 1 

        return counts

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
        #if type(obj) == cls:
        if isinstance(obj, cls):
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

    def _delObjects(self, ids: Iterable, cls: type):
        "删除多个指定元素"
        for id in ids:
            self._delObject(id, cls)

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

    def delAlias(self, ali):
        "从会话中移除别名，可接受Alias对象或alias的id"
        if isinstance(ali, Alias):
            self._delObject(ali.id, Alias)
        elif isinstance(ali, str) and (ali in self._aliases.keys()):
            self._delObject(ali, Alias)

    def delAliases(self, ali_es: Iterable):
        "删除一组别名"
        for ali in ali_es:
            self.delAlias(ali)

    def delCommand(self, cmd):
        "从会话中移除命令，可接受Command对象或command的id"
        if isinstance(cmd, Command):
            cmd.reset()
            self._delObject(cmd.id, Command)
        elif isinstance(cmd, str) and (cmd in self._commands.keys()):
            self._commands[cmd].reset()
            self._delObject(cmd, Command)

    def delCommands(self, cmd_s: Iterable):
        "删除一组命令"
        for cmd in cmd_s:
            self.delCommand(cmd)

    def delTrigger(self, tri):
        "从会话中移除触发器，可接受Trigger对象或trigger的id"
        if isinstance(tri, Trigger):
            self._delObject(tri.id, Trigger)
        elif isinstance(tri, str) and (tri in self._triggers.keys()):
            self._delObject(tri, Trigger)

    def delTriggers(self, tri_s: Iterable):
        "删除一组触发器"
        for tri in tri_s:
            self.delTrigger(tri)

    def delTimer(self, ti):
        "从会话中移除定时器，可接受Timer对象或者timer的id"
        if isinstance(ti, Timer):
            ti.enabled = False
            self._delObject(ti.id, Timer)
        elif isinstance(ti, str) and (ti in self._timers.keys()):
            self._timers[ti].enabled = False
            self._delObject(ti, Timer)

    def delTimers(self, ti_s: Iterable):
        "删除一组定时器"
        for ti in ti_s:
            self.delTimer(ti)

    def delGMCP(self, gmcp: GMCPTrigger):
        "从会话中移除GMCP触发器，可接受GMCPTrigger对象或其id"
        if isinstance(gmcp, GMCPTrigger):
            self._delObject(gmcp.id, GMCPTrigger)
        elif isinstance(gmcp, str) and (gmcp in self._gmcp.keys()):
            self._delObject(gmcp, GMCPTrigger)

    def delGMCPs(self, gmcp_s: Iterable):
        "删除一组GMCP"
        for gmcp in gmcp_s:
            self.delGMCP(gmcp)

    def replace(self, newstr):
        "替换当前行内容显示为newstr"
        if len(newstr) > 0:
            newstr += Settings.client["newline"]
        self.display_line = newstr


    ## ###################
    ## 变量 Variables 处理
    ## ###################
    def delVariable(self, name):
        """删除一个变量"""
        assert isinstance(name, str), "name必须是一个字符串"
        if name in self._variables.keys():
            self._variables.pop(name)

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
    def delGlobal(self, name):
        "删除一个全局变量"
        assert isinstance(name, str), "name必须是一个字符串"
        self.application.del_globals(name)

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
    def _print_all_help(self):
        """打印所有可用的help主题, 并根据终端尺寸进行排版"""
        width = self.application.get_width()

        #cmds = ["exit", "close", "session", "all", "help"]
        cmds = ["session"]
        cmds.extend(Session._commands_alias.keys())
        cmds.extend(Session._sys_commands)
        cmds = list(set(cmds))
        cmds.sort()

        cmd_count = len(cmds)
        left = (width - 8) // 2
        right = width - 8 - left
        self.writetobuffer("#"*left + "  HELP  " + "#"*right, newline = True)
        cmd_per_line = (width - 2) // 20
        lines = math.ceil(cmd_count / cmd_per_line)
        left_space = (width - cmd_per_line * 20) // 2

        for idx in range(0, lines):
            start = idx * cmd_per_line
            end   = (idx + 1) * cmd_per_line
            if end > cmd_count: end = cmd_count
            line_cmds = cmds[start:end]
            self.writetobuffer(" " * left_space)
            for cmd in line_cmds:
                if cmd in Session._commands_alias.keys():
                    self.writetobuffer(f"\x1b[32m{cmd.upper():<20}\x1b[0m")
                else:
                    self.writetobuffer(f"{cmd.upper():<20}")

            self.writetobuffer("", newline = True)

        self.writetobuffer("#"*width, newline = True)

    def handle_help(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #help 的执行函数，在当前会话中现实帮助信息。
        当不带参数时, #help会列出所有可用的帮助主题。
        带参数显示该系统命令的帮助。参数中不需要#号。
        该函数不应该在代码中直接调用。

        使用:
            - #help {topic}
            - 当不指定 topic: 列出所有可用的帮助主题。
            - 当指定 topic: 列出指定topic的帮助内容。该帮助类容由调用的函数的docstring确定。

        参数:
            :topic: 主题，支持所有的系统命令。在键入主题时，请忽略命令中的#号
    
        示例:
            - ``#help`` 
                在当前会话中显示所有帮助主题。其中，绿色显示的命令为其他命令的别名。
                注意，在没有当前会话时，命令不生效。
            - ``#help help`` 
                显示 #help 有关的帮助（即本帮助）
            - ``#help session`` 
                显示 #session 命令有关的帮助
        '''

        if code.length == 2:
            self._print_all_help()

        elif code.length == 3:
            #topic = args[0]
            topic = code.code[-1].lower()

            if topic in ("session", ):
                command = getattr(self.application, f"handle_{topic}", None)
                docstring = command.__doc__
            elif topic in self._commands_alias.keys():
                command = self._commands_alias[topic]
                docstring = self._cmds_handler[command].__doc__
            elif topic in self._sys_commands:
                docstring = self._cmds_handler[topic].__doc__
            else:
                docstring = f"未找到主题{topic}, 请确认输入是否正确."
            
            self.writetobuffer(docstring, True)

    def handle_exit(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #exit 的执行函数，退出 `PyMudApp` 应用。
        该函数不应该在代码中直接调用。

        *注：当应用中存在还处于连接状态的会话时，#exit退出应用会逐个弹出对话框确认这些会话是否关闭*

        相关命令:
            - #close
            - #session
        '''

        self.application.act_exit()

    def handle_close(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #close 的执行函数，关闭当前会话，并将当前会话从 `PyMudApp` 的会话列表中移除。
        该函数不应该在代码中直接调用。

        *注：当前会话处于连接状态时，#close关闭会话会弹出对话框确认是否关闭*
        
        相关命令:
            - #exit
            - #session
        '''

        self.application.close_session()

    async def handle_wait(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #wait / #wa 的执行函数，异步延时等待指定时间，用于多个命令间的延时等待。
        该函数不应该在代码中直接调用。

        使用:
            - #wa {ms}
        
        参数:
            - ms: 等待时间（毫秒）

        示例:
            - ``eat liang;#wa 300;drink jiudai``
                吃干粮，延时300毫秒后，执行喝酒袋
        
        相关命令:
            - #gag
            - #replace
        '''
        
        wait_time = code.code[2]
        if wait_time.isnumeric():
            msec = float(wait_time) / 1000.0
            await asyncio.sleep(msec)

    def handle_connect(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #connect / #con 的执行函数，连接到远程服务器（仅当远程服务器未连接时有效）。
        该函数不应该在代码中直接调用。
        
        相关命令:
            - #close
            - #exit
        '''

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

    def handle_variable(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #variable / #var 的执行函数，操作会话变量。
        该命令可以不带参数、带一个参数、两个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #var: 列出本会话所有变量
            - #var {name}: 列出本会话中名称为{name}的变量的值
            - #var {name} {value}: 将本会话中名称为{name}的变量设置值为{value}，若不存在则创建

        参数:
            :name: 变量名称
            :value: 变量值。注意: 该值赋值后为str类型!

        相关命令:
            - #global
        '''

        args = code.code[2:]

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

    def handle_global(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #global 的执行函数，操作全局变量（跨会话共享）。
        该命令可以不带参数、带一个参数、两个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #global: 列出所有全局变量
            - #global {name}: 列出中名称为{name}的全局变量的值
            - #global {name} {value}: 将名称为{name}的全局变量设置值为{value}，若不存在则创建

        参数:
            :name: 变量名称
            :value: 变量值。注意: 该值赋值后为str类型! 

        相关命令:
            - #variable
        '''

        args = code.code[2:]

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
                elif args[1] == "del":
                    obj.enabled = False
                    objs.pop(args[0])
                    self.info(f"对象 {obj} 已从会话中删除.")
                else:
                    self.error(f"#{name.lower()}命令的第二个参数仅能接受on/off/del")
            
            # 当第一个参数为不是对象obj名称时，创建新对象 (此处还有BUG，调试中)
            else:
                #self.warning(f"当前session中不存在key为 {args[0]} 的 {name}, 请确认后重试.")
                pattern, code = args[0], args[1]
                if (len(pattern)>=2) and (pattern[0] == '{') and (pattern[-1] == '}'):
                    pattern = pattern[1:-1]

                name = name.lower()
                if name == "alias":
                    ali = SimpleAlias(self, pattern, code)
                    self.addAlias(ali)
                    self.info("创建Alias {} 成功: {}".format(ali.id, ali.__repr__()))
                elif name == "trigger":
                    tri = SimpleTrigger(self, pattern, code)
                    self.addTrigger(tri)
                    self.info("创建Trigger {} 成功: {}".format(tri.id, tri.__repr__()))
                elif name == "timer":
                    if pattern.isnumeric():
                        timeout = float(pattern)
                        if timeout > 0:
                            ti  = SimpleTimer(self, code, timeout = timeout)
                            self.addTimer(ti)
                            self.info("创建Timer {} 成功: {}".format(ti.id, ti.__repr__()))

    def handle_alias(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #alias / #ali 的执行函数，操作别名。该命令可以不带参数、带一个参数或者两个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #ali: 显示本会话所有别名
            - #ali {ali_id}: 显示本会话中id为{ali_id}的别名信息
            - #ali {ali_id} {on/off/del}: 使能/禁用/删除本会话中id为{ali_id}的别名
            - #ali {pattern} {code}: 创建一个新别名，匹配为{pattern}，匹配时执行{code}
            - 别名的code中，可以使用%line代表行，%1~%9代表捕获信息

        参数:
            :ali_id:  别名Alias的id
            :on:      使能
            :off:     禁用
            :del:     删除
            :pattern: 新别名的匹配模式，应为合法的Python 正则表达式
            :code:    别名匹配成功后执行的内容
    
        示例:
            - ``#ali``               : 无参数, 打印列出当前会话中所有的别名清单
            - ``#ali my_ali``        : 一个参数, 列出id为my_ali的Alias对象的详细信息
            - ``#ali my_ali on``     : 两个参数，启用id为my_ali的Alias对象（enabled = True）
            - ``#ali my_ali off``    : 两个参数， 禁用id为my_ali的Alias对象（enabled = False）
            - ``#ali my_ali del``    : 两个参数，删除id为my_ali的Alias对象
            - ``#ali {^gp\s(.+)$} {get %1 from corpse}``   : 两个参数，新增创建一个Alias对象。使用时， ``gp gold = get gold from corpse``

        相关命令:
            - #trigger
            - #timer
            - #command
        '''

        self._handle_objs("Alias", self._aliases, *code.code[2:])

    def handle_timer(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #timer / #ti 的执行函数，操作定时器。该命令可以不带参数、带一个参数或者两个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #ti: 显示本会话所有定时器
            - #ti {ti_id}: 显示本会话中id为{ti_id}的定时器信息
            - #ti {ti_id} {on/off/del}: 使能/禁用/删除本会话中id为{ti_id}的定时器
            - #ti {second} {code}: 创建一个新定时器，定时间隔为{second}秒，定时器到时间执行{code}
            - PyMUD支持同时任意多个定时器。

        参数:
            :ti_id:   定时器Timer的id
            :on:      使能
            :off:     禁用
            :del:     删除
            :second:  新定时器的定时时间，单位为秒
            :code:    定时器到时间后执行的内容
    
        示例:
            - ``#ti``: 无参数, 打印列出当前会话中所有的定时器清单
            - ``#ti my_timer``: 一个参数, 列出id为my_timer的Timer对象的详细信息
            - ``#ti my_timer on``: 两个参数，启用id为my_timer的Timer对象（enabled = True）
            - ``#ti my_timer off``: 两个参数， 禁用id为my_timer的Timer对象（enabled = False）
            - ``#ti my_timer del``: 两个参数，删除id为my_timer的Timer对象
            - ``#ti 100 {drink jiudai;#wa 200;eat liang}``: 两个参数，新增创建一个Timer对象。每隔100s，自动执行一次喝酒袋吃干粮。

        相关命令:
            - #alias
            - #trigger
            - #command
        '''

        self._handle_objs("Timer", self._timers, *code.code[2:])
     
    def handle_command(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #command / #cmd 的执行函数，操作命令。该命令可以不带参数、带一个参数或者两个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #cmd: 显示本会话所有命令（Command及其子类）
            - #cmd {cmd_id}: 显示本会话中id为{cmd_id}的命令信息
            - #cmd {cmd_id} {on/off/del}: 使能/禁用/删除本会话中id为{cmd_id}的命令
            - 由于命令的特殊性，其只能使用脚本代码创建

        参数:
            :cmd_id:  命令Command的id
            :on:      使能
            :off:     禁用
            :del:     删除
    
        示例:
            - ``#cmd`` : 无参数, 打印列出当前会话中所有的命令清单
            - ``#cmd my_cmd`` : 一个参数, 列出id为my_cmd的Command对象的详细信息
            - ``#cmd my_cmd on`` : 两个参数，启用id为my_cmd的Command对象（enabled = True）
            - ``#cmd my_cmd off`` : 两个参数， 禁用id为my_cmd的Command对象（enabled = False）
            - ``#cmd my_cmd del`` : 两个参数，删除id为my_cmd的Command对象
        
        相关命令:
            - #alias
            - #trigger
            - #timer
        '''

        self._handle_objs("Command", self._commands, *code.code[2:])

    def handle_trigger(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #trigger / #tri / #action 的执行函数，操作触发器。该命令可以不带参数、带一个参数或者两个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #tri: 显示本会话所有触发器
            - #tri {tri_id}: 显示本会话中id为{tri_id}的触发器信息
            - #tri {tri_id} {on/off/del}: 使能/禁用/删除本会话中id为{tri_id}的触发器
            - #tri {pattern} {code}: 创建一个新触发器，匹配为{pattern}，匹配时执行{code}
            - 触发器的code中，可以使用%line代表行，%1~%9代表捕获信息

        参数:
            :tri_id:  触发器Trigger的id
            :on:      使能
            :off:     禁用
            :del:     删除
            :pattern: 触发器的匹配模式，应为合法的Python正则表达式
            :code:    触发成功时执行的内容
    
        示例:
            - ``#tri``: 无参数, 打印列出当前会话中所有的触发器清单
            - ``#tri my_tri``: 一个参数, 列出id为my_tri的Trigger对象的详细信息
            - ``#tri my_tri on``: 两个参数，启用id为my_tri的Trigger对象（enabled = True）
            - ``#tri my_tri off``: 两个参数， 禁用id为my_tri的Trigger对象（enabled = False）
            - ``#tri my_tri del``: 两个参数，删除id为my_tri的Trigger对象
            - ``#tri {^[> ]*段誉脚下一个不稳.+} {get duan}``: 两个参数，新增创建一个Trigger对象。当段誉被打倒的时刻把他背起来。

        相关命令:
            - #alias
            - #timer
            - #command
        '''
   
        self._handle_objs("Trigger", self._triggers, *code.code[2:])

    def handle_task(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #task 的执行函数，显示当前管理的所有任务清单（仅用于调试）。
        该函数不应该在代码中直接调用。

        注意：
            当管理任务很多时，该指令会影响系统响应。
        '''

        width = self.application.get_width()
        title = f"  Tasks LIST IN SESSION {self.name}  "
        left = (width - len(title)) // 2
        right = width - len(title) - left
        self.writetobuffer("="*left + title + "="*right, newline = True)

        for task in self._tasks:
            self.writetobuffer("  %r" % task, newline = True)

        self.writetobuffer("="*width, newline = True)


    def handle_ignore(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #ignore / #ig, #t+ / #t- 的执行函数，处理使能/禁用状态。
        该函数不应该在代码中直接调用。

        使用:
            - #ig: 切换触发器全局使能/禁用状态
            - #t+ {group}: 使能{group}组内的所有对象，包括别名、触发器、命令、定时器、GMCPTrigger等
            - #t- {group}: 禁用{group}组内的所有对象，包括别名、触发器、命令、定时器、GMCPTrigger等

        参数:
            :group:  组名
    
        示例:
            - ``#ig``: 切换全局触发器的使能/禁用状态。为禁用时，状态栏右下角会显示“全局已禁用”
            - ``#t+ mygroup``: 使能名称为 mygroup 的组内的所有对象，包括别名、触发器、命令、定时器、GMCPTrigger等
            - ``#t- mygroup``: 禁用名称为 mygroup 的组内的所有对象，包括别名、触发器、命令、定时器、GMCPTrigger等

        相关命令:
            - #trigger
            - #alias
            - #timer
        '''
        
        cmd = code.code[1].lower()
        if cmd in ("ig", "ignore"):
            self._ignore = not self._ignore
            if self._ignore:
                self.info("所有触发器使能已全局禁用。")
            else:
                self.info("不再全局禁用所有触发器使能。")
        elif cmd == "t+":
            if code.length <= 2:
                self.warning("#T+使能组使用不正确，正确使用示例: #t+ mygroup \n请使用#help ignore进行查询。")
                return
            
            groupname = code.code[2]
            cnts = self.enableGroup(groupname)
            self.info(f"组 {groupname} 中的 {cnts[0]} 个别名，{cnts[1]} 个触发器，{cnts[2]} 个命令，{cnts[3]} 个定时器，{cnts[4]} 个GMCP触发器均已使能。")

        elif cmd == "t-":
            if code.length <= 2:
                self.warning("#T-禁用组使用不正确，正确使用示例: #t+ mygroup \n请使用#help ignore进行查询。")
                return
            
            groupname = code.code[2]
            cnts = self.enableGroup(groupname, False)
            self.info(f"组 {groupname} 中的 {cnts[0]} 个别名，{cnts[1]} 个触发器，{cnts[2]} 个命令，{cnts[3]} 个定时器，{cnts[4]} 个GMCP触发器均已禁用。")

    def handle_repeat(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #repeat / #rep 的执行函数，重复向session输出上一次人工输入的命令。
        该函数不应该在代码中直接调用。

        使用:
            - #repeat

        注:
            这条命令并没有啥实质性应用场景
        '''

        if self.connected and self.last_command:
            self.exec_command(self.last_command)
        else:
            self.info("当前会话没有连接或没有键入过指令，repeat无效")

    async def handle_num(self, times, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #{num} 的执行函数，重复执行多次命令。
        该函数不应该在代码中直接调用。

        使用:
            - #{num} {code}: 执行code代码num次
            - {num}必须大于等于1
            - 该命令可以嵌套使用
        
        参数:
            :num:  重复执行的次数
            :code: 重复执行的代码
    
        示例:
            - ``#3 get m1b from nang`` : 从锦囊中取出3次地*木灵
            - ``#3 {#3 get m1b from nang;#wa 500;combine gem;#wa 4000};xixi`` : 执行三次合并地*木灵宝石的操作，中间留够延时等待时间，全部结束后发出xixi。

        相关命令:
            - #all
            - #session
        '''

        cmd = CodeBlock(" ".join(code.code[2:]))

        if self.connected:
            for i in range(0, times):
                await cmd.async_execute(self, *args, **kwargs)

    def handle_gmcp(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #gmcp 的执行函数，操作GMCPTrigger。该命令可以不带参数、带一个参数或者两个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #gmcp: 显示本会话所有GMCPTrigger
            - #gmcp {gmcp_key}: 显示本会话中name为{gmcp_key}的GMCPTrigger信息
            - #gmcp {gmcp_key} {on/off/del}: 使能/禁用/删除本会话中name为{gmcp_key}的GMCPTrigger
            - 由于GMCPTrigger的特殊性，其只能使用脚本代码创建

        参数:
            :gmcp_key:  GMCPTrigger的关键字name
            :on:      使能
            :off:     禁用
            :del:     删除
    
        示例:
            - ``#gmcp`` : 无参数, 打印列出当前会话中所有的命令清单
            - ``#gmcp GMCP.Move`` : 一个参数, 列出名称为 GMCP.Move 的 GMCPTrigger 对象的详细信息
            - ``#gmcp GMCP.Move on`` : 两个参数，启用名称为 GMCP.Move 的 GMCPTrigger 对象（enabled = True）
            - ``#gmcp GMCP.Move off`` : 两个参数， 禁用名称为 GMCP.Move 的 GMCPTrigger 对象（enabled = False）
            - ``#gmcp GMCP.Move del`` : 两个参数，删除名称为 GMCP.Move 的 GMCPTrigger 对象
        
        相关命令:
            - #alias
            - #trigger
            - #timer
        '''

        self._handle_objs("GMCPs", self._gmcp, *code.code[2:])

    def handle_message(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #message / #mess 的执行函数，弹出对话框显示给定信息。
        该函数不应该在代码中直接调用。

        使用:
            - #mess {msg}: 以弹出对话框显示{msg}指定的信息

        参数:
            :msg:  需弹出的显示信息

        示例:
            - ``#mess 这是一行测试`` : 使用弹出窗口显示“这是一行测试”
            - ``#mess %line`` : 使用弹出窗口显示系统变量%line的值
        '''

        title = "来自会话 {} 的消息".format(self.name)

        new_cmd_text, new_code = code.expand(self, *args, **kwargs)  
        index = new_cmd_text.find(" ")
        self.application.show_message(title, new_cmd_text[index:], False)


    def handle_all(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #all 的执行函数，向所有会话发送统一命令。
        该函数不应该在代码中直接调用。

        使用:
            - #all {code}: 向所有会话发送code命令
        
        参数:
            :code: 重复执行的代码
    
        示例:
            - ``#all #cls`` : 所有会话统一执行#cls命令
            - ``#all quit`` : 所有会话的角色统一执行quit退出

        相关命令:
            - #num
            - #session
        '''
        
        new_cmd  = " ".join(code.code[2:])
        for ss in self.application.sessions.values():
            if isinstance(ss, Session):
                ss.exec_command(new_cmd)
                
    def clean(self):
        "清除会话有关任务项和事件标识"
        try:
            # 加载时，取消所有任务，复位所有含async的对象, 保留变量
            for tm in self._timers.values():
                if isinstance(tm, Timer):
                    tm.reset()
            
            for tri in self._triggers.values():
                if isinstance(tri, Trigger):
                    tri.reset()

            for ali in self._aliases.values():
                if isinstance(ali, Alias):
                    ali.reset()

            for gmcp in self._gmcp.values():
                if isinstance(gmcp, GMCPTrigger):
                    gmcp.reset()

            for cmd in self._commands.values():
                if isinstance(cmd, Command):
                    cmd.reset()
            
            for task in self._tasks:
                if isinstance(task, asyncio.Task) and (not task.done()):
                    task.cancel()

            self._tasks.clear()
        except asyncio.CancelledError:
            pass

    def reset(self):
        "复位：清除所有异步项和等待对象，卸载所有模块，清除所有会话有关对象"
        self.clean()

        modules = self._modules.values()
        self.unload_module(modules)

        self._timers.clear()
        self._commands.clear()
        self._triggers.clear()
        self._gmcp.clear()
        self._aliases.clear()
        self._variables.clear()
        self._tasks.clear()

    def load_module(self, module_names):
        "当名称为元组/列表时，加载指定名称的系列模块，当名称为字符串时，加载单个模块"
        if isinstance(module_names, (list, tuple)):
            for mod in module_names:
                mod = mod.strip()
                self._load_module(mod)

        elif isinstance(module_names, str):
            mod = module_names.strip()
            self._load_module(mod)

    def _load_module(self, module_name):
        "加载指定名称模块"
        try:
            if module_name not in self._modules.keys():
                mod = importlib.import_module(module_name)
                if hasattr(mod, 'Configuration'):
                    config = mod.Configuration(self)
                    self._modules[module_name] = {"module": mod, "config": config}
                    self.info(f"主配置模块 {module_name} 加载完成.")
                else:
                    self._modules[module_name] = {"module": mod, "config": None}
                    self.info(f"子配置模块 {module_name} 加载完成.")

            else:
                mod = self._modules[module_name]["module"]
                config = self._modules[module_name]["config"]
                if config: del config
                mod = importlib.reload(mod)
                if hasattr(mod, 'Configuration'):
                    config = mod.Configuration(self)
                    self._modules[module_name] = {"module": mod, "config": config}
                    self.info(f"主配置模块 {module_name} 重新加载完成.")
                else:
                    self._modules[module_name] = {"module": mod, "config": None}
                    self.info(f"子配置模块 {module_name} 重新加载完成.")

        except Exception as e:
            import traceback
            self.error(f"模块 {module_name} 加载失败，异常为 {e}, 类型为 {type(e)}.")
            self.error(f"异常追踪为： {traceback.format_exc()}")

    def unload_module(self, module_names):
        "当名称为元组/列表时，卸载指定名称的系列模块，当名称为字符串时，卸载单个模块"
        if isinstance(module_names, (list, tuple)):
            for mod in module_names:
                mod = mod.strip()
                self._unload_module(mod)

        elif isinstance(module_names, str):
            mod = module_names.strip()
            self._unload_module(mod)

    def _unload_module(self, module_name):
        "卸载指定名称模块。卸载支持需要模块的Configuration实现__del__方法"
        if module_name in self._modules.keys():
            mod = self._modules[module_name]["module"]
            config = self._modules[module_name]["config"]
            if config: 
                if hasattr(config, "unload"):
                    unload = getattr(config, "unload", None)
                    if callable(unload):
                        unload(config)

                del config
            del mod
            self._modules.pop(module_name)
            self.info(f"配置模块 {module_name} 已成功卸载.")

        else:
            self.warning(f"指定模块名称 {module_name} 并未加载.")

    def reload_module(self, module_names = None):
        "重新加载指定名称模块，可以字符串指定单个或以列表形式指定多个模块。若未指定名称，则重新加载所有已加载模块"
        if module_names is None:
            self.clean()
            mods = list(self._modules.keys())
            self.load_module(mods)

            self.info(f"所有配置模块全部重新加载完成.")

        elif isinstance(module_names, (list, tuple)):
            for mod in module_names:
                mod = mod.strip()
                if mod in self._modules.keys():
                    self.load_module(mod)
                else:
                    self.warning(f"指定模块名称 {mod} 并未加载，无法重新加载.")

        elif isinstance(module_names, str):
            if module_names in self._modules.keys():
                mod = module_names.strip()
                self.load_module(mod)
            else:
                self.warning(f"指定模块名称 {module_names} 并未加载，无法重新加载.")
        

    def handle_load(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #load 的执行函数，为当前会话执行模块加载操作。当要加载多个模块时，使用空格或英文逗号隔开。
        该函数不应该在代码中直接调用。

        使用:
            - #load {mod1}: 加载指定名称的模块
            - #load {mod1} {mod2} ... {modn}: 加载指定名称的多个模块
            - #load {mod1},{mod2},...{modn}: 加载指定名称的多个模块
            - 注: 多个模块加载时，将依次逐个加载。因此若模块之间有依赖关系请注意先后顺序
        
        参数:
            :modx: 模块名称
    
        示例:
            - ``#load myscript`` : 加载myscript模块，首先会从执行PyMUD应用的当前目录下查找myscript.py文件并进行加载
            - ``#load pymud.pkuxkx`` : 加载pymud.pkuxkx模块。相当于脚本中的 import pymud.pkuxkx 命令
            - ``#load myscript1 myscript2`` : 依次加载myscript1和myscript2模块
            - ``#load myscript1,myscript2`` : 多个脚本之间也可以用逗号分隔

        相关命令:
            - #unload
            - #reload
            - #module
        '''

        modules = ",".join(code.code[2:]).split(",")
        self.load_module(modules)

    def handle_reload(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #reload 的执行函数，重新加载模块/插件。
        该函数不应该在代码中直接调用。

        使用:
            - #reload: 重新加载所有已加载模块
            - #reload {modname}: 重新加载名称为modname的模块
            - #reload {plugins}: 重新加载名称为plugins的插件
            - #reload {mod1} {mod2} ... {modn}: 重新加载指定名称的多个模块/插件
            - #reload {mod1},{mod2},...{modn}: 重新加载指定名称的多个模块/插件
        
        参数:
            :modname: 模块名称
            :plugins: 插件名称
            :modn:    模块名称
    
        注意:
            1. #reload只能重新加载#load方式加载的模块（包括在pymud.cfg中指定的），但不能重新加载import xxx导入的模块。
            2. 若加载的模块脚本中有语法错误，#reload可能无法生效。此时需要退出PyMUD重新打开
            3. 若加载时依次加载了不同模块，且模块之间存在依赖关系，那么重新加载时，应按原依赖关系顺序逐个重新加载，否则容易找不到依赖或依赖出错

        示例:
            - ``#reload`` : 重新加载所有已加载模块
            - ``#reload mymodule`` : 重新加载名为mymodule的模块
            - ``#reload myplugins`` : 重新加载名为myplugins的插件
            - ``#reload mymodule myplugins`` : 重新加载名为mymodule的模块和名为myplugins的插件。

        相关命令:
            - #load
            - #unload
            - #module
        '''

        args = list()
        if isinstance(code, CodeLine):
            args = code.code[2:]

        if len(args) == 0:
            self.reload_module()

        elif len(args) >= 1:
            modules = ",".join(args).split(",")
            for mod in modules:
                mod = mod.strip()
                if mod in self._modules.keys():
                    self.reload_module(mod)

                elif mod in self.plugins.keys():
                    self.application.reload_plugin(self.plugins[mod])

                else:
                    self.warning(f"指定名称 {mod} 既未找到模块，也未找到插件，重新加载失败..")

    def handle_unload(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #unload 的执行函数，卸载模块。
        该函数不应该在代码中直接调用。

        使用:
            - #unload {modname}: 卸载指定名称的已加载模块
            - #unload {mod1} {mod2} ... {modn}: 卸载指定名称的多个模块/插件
            - #unload {mod1},{mod2},...{modn}: 卸载加载指定名称的多个模块/插件
            - 注意: 卸载模块时并不会自动清理模块所创建的对象，而是调用模块Configuration类的unload方法，
              若需要清理模块创建的对象，请将清理工作代码显式放在此方法中 。
        
        参数:
            :modname: 模块名称
            :modn:    模块名称
    
        示例:
            - ``#unload mymodule``: 卸载名为mymodule的模块（并调用其中Configuration类的unload方法【若有】）
        
        相关命令:
            - #load
            - #reload
            - #module
        '''

        args = code.code[2:]

        if len(args) == 0:
            modules = self._modules.values()
            self.unload_module(modules)
            self.reset()

        elif len(args) >= 1:
            modules = ",".join(args).split(",")
            self.unload_module(modules)

    def handle_modules(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #modules / #mods 的执行函数，显示加载模块清单。该命令不带参数。
        该函数不应该在代码中直接调用。

        使用:
            - #mods: 显示当前会话所加载的所有模块清单

        相关命令:
            - #load
            - #unload
            - #reload
        '''

        count = len(self._modules.keys())
        if count == 0:
            self.info("当前会话并未加载任何模块。", "MODULES")
        else:
            self.info(f"当前会话已加载 {count} 个模块，包括（按加载顺序排列）：{list(self._modules.keys())}", "MODULES")
    
    def handle_reset(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #reset 的执行函数，复位全部脚本。该命令不带参数。
        复位操作将复位所有的触发器、命令、未完成的任务，并清空所有触发器、命令、别名、变量。
        该函数不应该在代码中直接调用。

        使用:
            - #reset: 复位全部脚本

        相关命令:
            - #load
            - #unload
            - #reload
        '''
        
        self.reset()

    def handle_save(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #save 的执行函数，保存当前会话变量（系统变量除外）至文件。该命令不带参数。
        该函数不应该在代码中直接调用。

        使用:
            - #save: 保存当前会话变量

        注意:
            1. 文件保存在当前目录下，文件名为 {会话名}.mud
            2. 变量保存使用了python的pickle模块，因此所有变量都应是类型自省的
            3. 虽然变量支持所有的Python类型，但是仍然建议仅在变量中使用可以序列化的类型。
            4. namedtuple不建议使用，因为加载后在类型匹配比较时会失败，不认为两个相同定义的namedtuple是同一种类型。
        
        相关命令:
            - #variable
        '''

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
            self.info(f"会话变量信息已保存到{file}")

    def handle_clear(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #clear / #cls 的执行函数，清空当前会话缓冲与显示。
        该函数不应该在代码中直接调用。

        使用:
            - #cls: 清空当前会话缓冲及显示
        '''

        self.buffer.text = ""

    def handle_test(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #test 的执行函数，触发器测试命令。类似于zmud的#show命令。
        该函数不应该在代码中直接调用。

        使用:
            - #test {some_text}: 测试服务器收到{some_text}时的触发器响应情况

        示例:
            - ``#test 你深深吸了口气，站了起来。`` ： 模拟服务器收到“你深深吸了口气，站了起来。”时的情况进行触发测试
            - ``#test %copy``: 复制一句话，模拟服务器再次收到复制的这句内容时的情况进行触发器测试

        注意:
            - #test命令测试触发器时，enabled为False的触发器不会响应。
        '''

        new_cmd_text, new_code = code.expand(self, *args, **kwargs)
        line = new_cmd_text[6:]       # 取出#test 之后的所有内容

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

    def handle_plugins(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #plugins 的执行函数，显示插件信息。该命令可以不带参数、带一个参数。
        该函数不应该在代码中直接调用。

        使用:
            - #plugins: 显示当前会话所加载的所有插件清单
            - #plugins {myplug}: 显示名称为myplug的插件的详细信息

        相关命令:
            - #modules
        '''
        
        args = code.code[2:]

        if len(args) == 0:
            count = len(self.plugins.keys())
            if count == 0:
                self.info("PYMUD当前并未加载任何插件。", "PLUGINS")
            else:
                self.info(f"PYMUD当前已加载 {count} 个插件，分别为：", "PLUGINS")
                for name, plugin in self.plugins.items():
                    self.info(f"{plugin.desc['DESCRIPTION']}, 版本 {plugin.desc['VERSION']} 作者 {plugin.desc['AUTHOR']} 发布日期 {plugin.desc['RELEASE_DATE']}", f"PLUGIN {name}")
        
        elif len(args) == 1:
            name = args[0]
            if name in self.plugins.keys():
                plugin = self.plugins[name]
                self.info(f"{plugin.desc['DESCRIPTION']}, 版本 {plugin.desc['VERSION']} 作者 {plugin.desc['AUTHOR']} 发布日期 {plugin.desc['RELEASE_DATE']}", f"PLUGIN {name}")
                self.writetobuffer(plugin.help)

    def handle_replace(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #replace 的执行函数，修改显示内容，将当前行原本显示内容替换为msg显示。不需要增加换行符。
        该函数不应该在代码中直接调用。

        使用:
            - #replace {new_display}: 将当前行显示替换为{new_display}

        参数:
            - :new_display: 替换后的显示，可支持ANSI颜色代码

        示例:
            - ``#replace %raw - 捕获到此行`` : 将捕获的当前行信息后面增加标注

        注意:
            - 应在触发器的同步处理中使用。多行触发器时，替代只替代最后一行。

        相关命令:
            - #gag
        '''
        
        new_text, new_code = code.expand(self, *args, **kwargs)
        self.replace(new_text[9:])
        
    def handle_gag(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #gag 的执行函数，在主窗口中不显示当前行内容，一般用于触发器中。
        该函数不应该在代码中直接调用。

        使用:
            - #gag

        注意:
            - 一旦当前行被gag之后，无论如何都不会再显示此行内容，但对应的触发器仍会生效

        相关命令:
            - #replace
        '''

        self.display_line = ""

    def handle_py(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #py 的执行函数，执行 Python 语句。
        该函数不应该在代码中直接调用。

        使用:
            - #py {py_code}: 在当前上下文中执行py_code
            - 环境为当前上下文环境，此时self代表当前会话

        示例:
            - ``#py self.info("hello")`` : 相当于在当前会话中调用 ``session.info("hello")``
            - ``#py self.enableGroup("group1", False)`` : 相当于调用 ``session.enableGroup("group1", False)``
        '''

        try:
            exec(code.commandText[4:])
        except Exception as e:
            self.error(f"Python执行错误：{e}")

    def handle_info(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #info 的执行函数，使用 session.info 输出一行，主要用于测试。
        该函数不应该在代码中直接调用。

        使用:
            - #info {msg}

        相关命令:
            - #warning
            - #error
        '''

        new_text, new_code = code.expand(self, *args, **kwargs)
        self.info(new_text[6:])

    def handle_warning(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #warning 的执行函数，使用 session.warning 输出一行，主要用于测试。
        该函数不应该在代码中直接调用。

        使用:
            - #warning {msg}

        相关命令:
            - #info
            - #error
        '''
        
        new_text, new_code = code.expand(self, *args, **kwargs)
        self.warning(new_text[6:])

    def handle_error(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #error 的执行函数，使用 session.error 输出一行，主要用于测试。
        该函数不应该在代码中直接调用。

        使用:
            - #error {msg}

        相关命令:
            - #info
            - #warning
        '''
        
        new_text, new_code = code.expand(self, *args, **kwargs)
        self.error(new_text[6:])

    def info2(self, msg, title = "PYMUD INFO", style = Settings.INFO_STYLE):
        if Settings.client["newline"] in msg:
            new_lines = list()
            msg_lines = msg.split(Settings.client["newline"])
            for line in msg_lines:
                new_lines.append("{}{}".format(style, line))

            msg = Settings.client["newline"].join(new_lines)
                
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
