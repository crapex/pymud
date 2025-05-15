import asyncio, logging, re, math, os, pickle, datetime, importlib, importlib.util, sysconfig, time, dataclasses
from collections.abc import Iterable
from collections import OrderedDict
import logging, queue
from logging import FileHandler
from logging.handlers import QueueHandler, QueueListener
from wcwidth import wcswidth, wcwidth
from .logger import Logger
from .extras import SessionBuffer, DotDict
from .protocol import MudClientProtocol
from .modules import ModuleInfo
from .objects import BaseObject, Trigger, Alias, Command, Timer, SimpleAlias, SimpleTrigger, SimpleTimer, GMCPTrigger, CodeBlock, CodeLine
from .settings import Settings


class Session:
    """
    会话管理主对象，每一个角色的所有处理实现均在该类中实现。

    **Session对象由PyMudApp对象进行创建和管理，不需要手动创建。**

    :param app: 对应的PyMudApp对象
    :param name: 本会话的名称
    :param host: 本会话连接的远程服务器地址
    :param port: 本会话连接的远程服务器端口
    :param encoding: 远程服务器的编码
    :param after_connect: 当连接到远程服务器后执行的操作
    :param loop: asyncio的消息循环队列
    :param kwargs: 关键字参数清单，当前支持的关键字 **scripts** : 需加载的脚本清单

    """
    #_esc_regx = re.compile("\x1b\\[[^mz]+[mz]")
    #_esc_regx = re.compile(r"\x1b\[[\d;]+[abcdmz]", flags = re.IGNORECASE)
    PLAIN_TEXT_REGX = re.compile("\x1b\\[[0-9;]*[a-zA-Z]", flags = re.IGNORECASE | re.ASCII)

    _sys_commands = (
        "help",
        "exit",
        "close",
        "connect",      # 连接到服务器
        "disconnect",   # 从服务器断开连接

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

        "log",          # 记录处置
    )

    _commands_alias = {
        "ali" : "alias",
        "cmd" : "command",
        "ti"  : "timer",
        "tri" : "trigger",
        "var" : "variable",
        "rep" : "repeat",
        "con" : "connect",
        "dis" : "disconnect",
        "wa"  : "wait",
        "mess": "message",
        "action": "trigger",
        "cls" : "clear",
        "mods": "modules",
        "ig"  : "ignore",
        "t+"  : "ignore",
        "t-"  : "ignore",
        "show": "test",
    }

    def __init__(self, app, name, host, port, encoding = None, after_connect = None, loop = None, **kwargs):
        self.pyversion = sysconfig.get_python_version()   
        self.loop = loop or asyncio.get_running_loop()    
        self.syslog = logging.getLogger("pymud.Session")

        from .pymud import PyMudApp
        if isinstance(app, PyMudApp):
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

        self._activetime = time.time()

        self.initialize()

        self._loggers = dict()
        self.log = self.getLogger(name)

        self.host = host
        self.port = port
        self.encoding = encoding or self.encoding
        self.after_connect = after_connect

        self._modules = OrderedDict()

        # 将变量加载和脚本加载调整到会话创建时刻
        if Settings.client["var_autoload"]:
                file = f"{self.name}.mud"
                if os.path.exists(file):
                    with open(file, "rb") as fp:
                        try:
                            vars = pickle.load(fp)
                            self._variables.update(vars)
                            self.info(Settings.gettext("msg_var_autoload_success", file))
                        except Exception as e:
                            self.warning(Settings.gettext("msg_var_autoload_fail", file, e))

        
        if self._auto_script:
            self.info(Settings.gettext("msg_auto_script", self._auto_script))
            self.load_module(self._auto_script)

        if Settings.client["auto_connect"]:
            self.open()

    def __del__(self):
        self.clean()
        self.closeLoggers()

    def initialize(self):
        "初始化Session有关对象。 **无需脚本调用。**"
        self._line_buffer = bytearray()
        
        self._triggers = DotDict()
        self._aliases  = DotDict()
        self._commands = DotDict()
        self._timers   = DotDict()
        self._gmcp     = DotDict()

        self._variables = DotDict()

        #self._tasks    = []
        self._tasks    = set()

        self._command_history = []

    def open(self):
        "创建到远程服务器的连接，同步方式。通过调用异步connect方法实现。"
        asyncio.ensure_future(self.connect(), loop = self.loop)

    async def connect(self):
        "创建到远程服务器的连接，异步非阻塞方式。"
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
            self.error(Settings.gettext("msg_connection_fail", now, exec))
            self._state     = "EXCEPTION"

            if Settings.client["auto_reconnect"]:
                wait = Settings.client.get("reconnect_wait", 15)
                asyncio.ensure_future(self.reconnect(wait), loop = self.loop)

    async def reconnect(self, timeout = 15):
        """
        重新连接到远程服务器，异步非阻塞方式。该方法在 `Settings.client['auto_reconnect']` 设置为真时，断开后自动调用
        
        :param timeout: 重连之前的等待时间，默认15s，可由 `Settings.client['reconnect_wait']` 设置所覆盖
        """
        self.info(Settings.gettext("msg_auto_reconnect", timeout))
        await asyncio.sleep(timeout)
        await self.create_task(self.connect())

    def onConnected(self):
        "当连接到服务器之后执行的操作。包括打印连接时间，执行自定义事件(若设置)等。"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.info(Settings.gettext("msg_connected", now))
        if isinstance(self.after_connect, str):
            self.writeline(self.after_connect)

        event_connected = self._events["connected"]
        if callable(event_connected):
            event_connected(self)

    def disconnect(self):
        "断开到服务器的连接。"
        if self.connected:
            self.write_eof()

    def onDisconnected(self, protocol):
        "当从服务器连接断开时执行的操作。包括保存变量(若设置)、打印断开时间、执行自定义事件(若设置)等。"
        # 断开时自动保存变量数据
        if Settings.client["var_autosave"]:
            self.handle_save()
        
        self.clean()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.info(Settings.gettext("msg_disconnected", now))

        event_disconnected = self._events["disconnected"]
        if callable(event_disconnected):
            event_disconnected(self)

        if Settings.client["auto_reconnect"]:
            wait = Settings.client.get("reconnect_wait", 15)
            asyncio.ensure_future(self.reconnect(wait), loop = self.loop)

    @property
    def connected(self) -> bool:
        "只读属性，返回服务器端的连接状态"
        if self._protocol:
            con = self._protocol.connected
        else:
            con = False

        return con

    @property
    def duration(self) -> float:
        "只读属性，返回服务器端连接的时间，以秒为单位"
        dura = 0
        if self._protocol and self._protocol.connected:
            dura = self._protocol.duration

        return dura

    @property
    def idletime(self) -> float:
        "只读属性，返回当前会话空闲时间（即最后一次向服务器写入数据到现在的时间），以秒为单位。当服务器未连接时，返回-1"
        idle = -1
        if self._protocol and self._protocol.connected:
            idle = time.time() - self._activetime

        return idle

    @property
    def status_maker(self):
        """
        可读写属性，会话状态窗口的内容生成器，应为一个可返回 `AnyFormattedText` 对象的不带额外参数的方法
        
        示例:
            .. code:: python

                class Configuration:
                    def __init__(self, session):
                        self.session = session
                        self.session.status_maker = self.mystatus

                    def mystatus(self):
                        '可返回AnyFormattedText类型的对象。具体参见 prompt_toolkit 。'
                        return "this is a test status"
        """
        return self._status_maker
    
    @status_maker.setter
    def status_maker(self, value):
        if callable(value):
            self._status_maker = value

    @property
    def event_connected(self):
        """
        可读写属性，自定义的会话连接事件，应为一个带一个额外参数 Session 的方法

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session
                        self.session.event_connected = self.onSessionConnected

                    def onSessionConnected(self, session):
                        session.info("Connected!")
        """
        return self._events["connected"]
    
    @event_connected.setter
    def event_connected(self, event):
        self._events["connected"] = event

    @property
    def event_disconnected(self):
        """
        可读写属性，自定义的会话断开事件，应为一个带一个参数 Session 的方法
        
        使用方法同 event_connected
        """
        return self._events["disconnected"]
    
    @event_disconnected.setter
    def event_disconnected(self, event):
        self._events["disconnected"] = event

    def getLogger(self, name, mode = 'a', encoding = 'utf-8', encoding_errors = 'ignore', raw = False) -> Logger:
        """
        根据指定名称和参数获取并返回一个记录器。若指定名称不存在，则创建一个该名称记录器。
        
        :param name: 指定的记录器名称
        :param mode: 记录器的模式，可接受值为 a, w, n。 具体请参见 Logger 对象中 mode 参数
        :param encoding: 记录文件的编码格式
        :param encoding_errors: 编码错误的处理方式
        :param raw: 是否以带ANSI标记的原始格式进行记录

        :return 指定名称的记录器 Logger 对象
        """
        if name not in self.application.loggers.keys():
            logger = Logger(name, mode, encoding, encoding_errors, raw)
            self._loggers[name] = logger
            self.application.loggers[name] = logger

        else:
            if name not in self._loggers.keys():
                self.warning(Settings.gettext("msg_duplicate_logname", name))

            logger = self.application.loggers[name]
            logger.mode = mode
            logger.raw = raw

        return logger

    def closeLoggers(self):
        "移除本会话所有相关Logger"
        for name in self._loggers.keys():
            if isinstance(self._loggers[name], Logger):
                self._loggers[name].enabled = False
            
            if name in self.application.loggers.keys():
                self.application.loggers.pop(name)

    @property
    def modules(self) -> OrderedDict:
        """
        只读属性，返回本会话加载的所有模块，类型为顺序字典 OrderedDict

        在字典中，关键字为模块名，值为模块本身与配置对象的二级字典，包含两个关键字， module 与 config

        如，存在一个名为 my.py的模块文件，则加载后，session.modules['my'] 可以访问该模块有关信息。其中:

        - `session.modules['my']['module']` 访问模块对象
        - `session.modules['my']['config']` 访问该该模块文件中的Configuration类的实例（若有定义）
        """
        return self._modules

    @property
    def plugins(self) -> DotDict:
        """
        只读属性，为PYMUD插件的辅助点访问器

        如，存在一个名为myplugin.py的插件文件并已正常加载，该文件中定义了 PLUGIN_NAME 为 "myplugin"，则可以通过本属性及插件名访问该插件

        .. code:: Python

            plugin = session.plugins.myplugin  # plugin为 Plugin类型的对象实例
        """
        return self.application.plugins

    @property
    def vars(self):
        """
        本会话内变量的辅助点访问器，可以通过vars+变量名快速访问该变量值

        .. code:: Python

            # 以下两个获取变量值的方法等价
            exp = session.vars.exp
            exp = session.getVariable('exp')

            # 以下两个为变量赋值的方法等价
            session.vars.exp = 10000
            session.setVariable('exp', 10000)
        """
        return self._variables

    @property
    def globals(self):
        """
        全局变量的辅助点访问器，可以通过globals+变量名快速访问该变量值

        全局变量与会话变量的区别在于，全局变量在所有会话之间是共享和统一的
        
        .. code:: Python

            # 以下两个获取全局变量值的方法等价
            hooked = session.globals.hooked
            hooked = session.getGlobal('hooked')

            # 以下两个为全局变量赋值的方法等价
            session.globals.hooked = True
            session.setGlobal('hooked', True)
        """
        return self.application.globals

    @property
    def tris(self):
        """
        本会话的触发器的辅助点访问器，可以通过tris+触发器id快速访问触发器

        .. code:: Python
            
            session.tris.mytri.enabled = False
        """
        return self._triggers

    @property
    def alis(self):
        """
        本会话的别名辅助点访问器，可以通过alis+别名id快速访问别名
        
        .. code:: Python
            
            session.alis.myali.enabled = False
        """
        return self._aliases
    
    @property
    def cmds(self):
        """
        本会话的命令辅助点访问器，可以通过cmds+命令id快速访问命令
        
        .. code:: Python
            
            session.cmds.mycmd.enabled = False
        """
        return self._commands

    @property
    def timers(self):
        """
        本会话的定时器辅助点访问器，可以通过timers+定时器id快速访问定时器
        
        .. code:: Python
            
            session.timers.mytimer.enabled = False
        """
        return self._timers

    @property
    def gmcp(self):
        "本会话的GMCP辅助访问器"
        return self._gmcp

    def get_status(self):
        "返回状态窗口内容的真实函数。 **脚本中无需调用。**"
        text = Settings.gettext("msg_default_statuswindow", self.name, self.connected)
        if callable(self._status_maker):
            text = self._status_maker()
            
        return text

    def getPlainText(self, rawText: str, trim_newline = False) -> str:
        """
        将带有VT100或者MXP转义字符的字符串转换为正常字符串（删除所有转义）。 **脚本中无需调用。**

        :param rawText: 原始文本对象
        :param trim_newline: 返回值是否删除末尾的回车符和换行符

        :return: 经处理后的纯文本字符串
        
        """
        plainText = Session.PLAIN_TEXT_REGX.sub("", rawText)
        if trim_newline:
            plainText = plainText.rstrip("\n").rstrip("\r")

        return plainText

    def writetobuffer(self, data, newline = False):
        """
        将数据写入到用于本地显示的缓冲中。 **脚本中无需调用。**
        
        :param data: 写入的数据, 应为 str 类型
        :param newline: 是否额外增加换行符
        """
        self.buffer.insert_text(data)
        self.log.log(data)

        if len(data) > 0 and (data[-1] == "\n"):
            self._line_count += 1

        if newline:
            self.buffer.insert_text(self.newline_cli)
            self._line_count += 1
            self.log.log(self.newline_cli)

    def clear_half(self):
        """
        清除半数缓冲。 **脚本中无需调用。**

        半数的数量由 Settings.client['buffer_lines'] 确定，默认为5000行。
        """
        if (Settings.client["buffer_lines"] > 0) and (self._line_count >= 2 * Settings.client["buffer_lines"]) and self.buffer.document.is_cursor_at_the_end:
            self._line_count = self.buffer.clear_half()

    def feed_data(self, data) -> None:
        """
        由协议对象调用，将收到的远程数据加入会话缓冲。永远只会传递1个字节的数据，以bytes形式。 **脚本中无需调用。**
        
        :param data: 传入的数据， bytes 格式
        """
        self._line_buffer.extend(data)

        if (len(data) == 1) and (data[0] == ord("\n")):
            self.go_ahead()

    def feed_eof(self) -> None:
        """
        由协议对象调用，处理收到远程 eof 数据，即远程断开连接。 **脚本中无需调用。**
        """
        self._eof = True
        if self.connected:
            self._transport.write_eof()
        self.state = "DISCONNECTED"
        self.syslog.info(f"服务器断开连接! {self._protocol.__repr__}")
    
    def feed_gmcp(self, name, value) -> None:
        """
        由协议对象调用，处理收到远程 GMCP 数据。 **脚本中无需调用。**

        :param name: 收到的GMCP数据的 name
        :param value: 收到的GMCP数据的 value。 该数据值类型为 字符串形式执行过eval后的结果

        **注** 当未通过GMCPTrigger对某个name的GMCP数据进行处理时，会通过session.info将该GMCP数据打印出来以供调试。
        当已有GMCPTrigger处理该name的GMCP数据时，则不会再打印此信息。
        """

        nothandle = True
        if name in self._gmcp.keys():
            gmcp = self._gmcp[name]
            if isinstance(gmcp, GMCPTrigger):
                gmcp(value)
                nothandle = False

        if nothandle:
            self.info(f"{name}: {value}", "GMCP")

    def feed_msdp(self, name, value) -> None:
        """
        由协议对象调用，处理收到远程 MSDP 数据。 **脚本中无需调用。**

        :param name: 收到的MSDP数据的 name
        :param value: 收到的MSDP数据的 value

        **注** 由于北大侠客行不支持MSDP，因此该函数体并未实现
        """
        pass

    def feed_mssp(self, name, value) -> None:
        """
        由协议对象调用，处理收到远程 MSSP 数据。 **脚本中无需调用。**

        :param name: 收到的MSSP数据的 name
        :param value: 收到的MSSP数据的 value

        **注** 由于北大侠客行不支持MSSP，因此该函数体并未实现
        """

    def go_ahead(self) -> None:
        """
        对当前接收缓冲内容进行处理并放到显示缓冲中。 **脚本中无需调用。**
        
        触发器的响应在该函数中进行处理。
        """
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
                self.warning(Settings.gettext("msg_mxp_not_support"))
    
        # 全局变量%line
        self.setVariable("%line", tri_line)
        # 全局变量%raw
        self.setVariable("%raw", raw_line.rstrip("\n").rstrip("\r"))

        # 此处修改，为了处理#replace和#gag命令
        # 将显示行数据暂存到session的display_line中，可以由trigger改变显示内容
        self.display_line = raw_line

        if not self._ignore:
            # 修改实现，形成列表时即排除非使能状态触发器，加快响应速度

            all_tris = [tri for tri in self._triggers.values() if isinstance(tri, Trigger) and tri.enabled]
            all_tris.sort(key = lambda tri: tri.priority)

            for tri in all_tris:
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
        """
        由协议对象调用，处理异常。 **脚本中无需调用。**

        :param exc: 异常对象
        """
        self.error(Settings.gettext("msg_connection_fail", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exc))


    def create_task(self, coro, *args, name: str = None) -> asyncio.Task:
        """
        创建一个任务，并将其加入到会话的任务管理队列中。

        加入会话管理的任务，在任务完成（结束或中止）后，会自动从管理队列中移除。

        :param coro: 一个async定义的协程对象或者其他可等待对象
        :param name: 任务的名称定义，可选项。该属性仅在3.10及以后的Python版本中支持

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session
                        self.session.create_task(self.async_example())

                    async def async_example(self):
                        await asyncio.sleep(1)
                        self.session.info("show a message after 1 second")
        """
        if self.pyversion in ["3.7", "3.8", "3.9"]:
            task = self.loop.create_task(coro)
        else:
            task = self.loop.create_task(coro, name = name)

        task.add_done_callback(self._tasks.discard)
        self._tasks.add(task)

        return task

    def remove_task(self, task: asyncio.Task, msg = None):
        """
        清除一个受本会话管理的任务。若任务未完成，则取消该任务。

        由于加入会话管理的任务，在任务完成后会自动从管理队列中移除，因此该方法主要用来取消未完成的任务。

        :param task: 由本会话管理的一个 asyncio.Task 对象
        :param msg: 本意是用来反馈 task.cancel() 时的消息，但为了保持兼容低版本Python环境，该参数并未使用。
        """
        result = task.cancel()
        self._tasks.discard(task)

        return result

    def clean_finished_tasks(self):
        # 清理已经完成的任务。
        # 自PyMUD 0.19.2post2版之后，清理完成任务在该任务完成时刻自动调用，因此本函数不再使用，保留的目的是为了向前兼容。

        self._tasks = set([t for t in self._tasks if not t.done()])

    def write(self, data) -> None:
        """
        向服务器写入数据（RAW格式字节数组/字节串）。 **一般不应在脚本中直接调用。**

        :param data: 向传输中写入的数据, 应为 bytes, bytearray, memoryview 类型
        """
        if self._transport and not self._transport.is_closing():
            self._transport.write(data)
    
    def writeline(self, line: str) -> None:
        """
        向服务器中写入一行，用于向服务器写入不经别名或命令解析时的数据。将自动在行尾添加换行符。
        
        - 如果line中包含分隔符（由Settings.client.seperator指定，默认为半角分号;）的多个命令，将逐行依次写入。
        - 当 Settings.cleint["echo_input"] 为真时，向服务器写入的内容同时在本地缓冲中回显。

        :param line: 字符串行内容

        示例:
            .. code:: Python

                session.writeline("open door")
        """
        if self.seperator in line:
            lines = line.split(self.seperator)
            for ln in lines:
                if Settings.client["echo_input"]:
                    self.writetobuffer(f"\x1b[32m{ln}\x1b[0m", True)
                else:
                    self.log.log(f"\x1b[32m{ln}\x1b[0m\n")

                cmd = ln + self.newline
                self.write(cmd.encode(self.encoding, Settings.server["encoding_errors"]))
                
        else:
            if Settings.client["echo_input"]:
                self.writetobuffer(f"\x1b[32m{line}\x1b[0m", True)
            else:
                self.log.log(f"\x1b[32m{line}\x1b[0m\n")

            cmd = line + self.newline
            self.write(cmd.encode(self.encoding, Settings.server["encoding_errors"]))

        self._activetime = time.time()
    
    async def waitfor(self, line: str, awaitable, wait_time = 0.05) -> None:
        """
        调用writline向服务器中写入一行后，等待到可等待对象再返回。
        
        :param line: 使用writeline写入的行
        :param awaitable: 等待的可等待对象
        :param wait_time: 写入行前等待的延时，单位为s。默认0.05

        由于异步的消息循环机制，如果在写入命令之后再创建可等待对象，则有可能服务器响应在可等待对象的创建之前
        此时使用await就无法等待到可等待对象的响应，会导致任务出错。
        一种解决方式是先创建可等待对象，然后写入命令，然后再等待可等待对象，但这种情况下需要写入三行代码，书写麻烦
        因此该函数是用于简化此类使用时的写法。

        示例:
            await session.waitfor('a_cmd', self.create_task(a_tri.triggered()))
            done, pending = await session.waitfor('a_cmd', asyncio.wait([self.create_task(a_tri.triggered()), self.create_task(b_tri.triggered())], return_when = 'FIRST_COMPLETED'))
        """
        await asyncio.sleep(wait_time)
        self.writeline(line)
        return await awaitable

    def exec(self, cmd: str, name = None, *args, **kwargs):
        r"""
        在名称为name的会话中使用exec_command执行MUD命令。当不指定name时，在当前会话中执行。

        - exec 与 writeline 都会向服务器写入数据。其差异在于，exec执行的内容，会先经过Alias处理和Command处理，实际向远程发送内容与cmd可以不一致。
        - exec 在内部通过调用 exec_command 实现， exec 可以实现与 exec_command 完全相同的功能
        - exec 是后来增加的函数，因此保留 exec_command 的目的是为了脚本的向前兼容
        
        :param cmd: 要执行的命令
        :param name: 要执行命令的会话的名称，当不指定时，在当前会话执行。
        :param args: 保留兼容与扩展性所需，脚本中调用时无需指定
        :param kwargs: 保留兼容与扩展性所需，脚本中调用时无需指定

        示例:
            .. code:: Python

                session.addAlias(SimpleAlias(self.session, r"^cb\s(\S+)\s(\S+)", "#3 get %1 from jinnang;#wa 250;combine gem;#wa 250;pack gem", id = "ali_combine"))
                session.exec("cb j1a")
        """
        name = name or self.name
        if name in self.application.sessions.keys():
            session = self.application.sessions[name]
            session.exec_command(cmd, *args, **kwargs)
        else:
            self.error(Settings.gettext("msg_no_session", name))

    async def exec_async(self, cmd: str, name = None, *args, **kwargs):
        """
        exec的异步形式。在名称为name的会话中使用exec_command_async执行MUD命令。当不指定name时，在当前会话中执行。

        - exec_async 在内部通过调用 exec_command_async 实现， exec_async 可以实现与 exec_command_async 完全相同的功能
        - exec_async 是后来增加的函数，因此保留 exec_command_async 的目的是为了脚本的向前兼容
        - 异步调用时，该函数要等待对应的代码执行完毕后才会返回。可以用于确保命令执行完毕。
        """
        name = name or self.name
        if name in self.application.sessions.keys():
            session = self.application.sessions[name]
            return await session.exec_command_async(cmd, *args, **kwargs)
        else:
            self.error(Settings.gettext("msg_no_session", name))

    def exec_code(self, cl: CodeLine, *args, **kwargs):
        """
        执行解析为CodeLine形式的MUD命令（必定为单个命令）。一般情况下，脚本中不应调用该方法，而应使用exec/exec_command。
        
        这是命令执行的最核心执行函数，所有真实调用的起源（同步调用情况下）

        :param cl: CodeLine形式的执行代码
        :param args: 保留兼容与扩展性所需
        :param kwargs: 保留兼容与扩展性所需
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
                    self.warning(Settings.gettext("msg_num_positive"))
            
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
                    self.warning(Settings.gettext("msg_cmd_not_recognized", cl.commandText))

        else:
            cmdtext, code = cl.expand(self, *args, **kwargs)
            self.exec_text(cmdtext)

    async def exec_code_async(self, cl: CodeLine, *args, **kwargs):
        """
        该方法为exec_code的异步形式实现。一般情况下，脚本中不应调用该方法，而应使用 exec_command_async。
        
        这是命令执行的最核心执行函数，所有真实调用的起源（异步调用情况下）。

        异步调用时，该函数要等待对应的代码执行完毕后才会返回。可以用于确保命令执行完毕。

        :param cl: CodeLine形式的执行代码
        :param args: 保留兼容与扩展性所需
        :param kwargs: 保留兼容与扩展性所需
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
                    self.warning(Settings.gettext("msg_num_positive"))
            
            elif cmd in self.application.sessions.keys():
                name = cmd
                sess_cmd  = " ".join(cl.code[2:])
                session = self.application.sessions[name]
                if len(sess_cmd) == 0:
                    session.writeline("")
                else:
                    try:
                        cb = CodeBlock(sess_cmd)
                        return await cb.async_execute(session, *args, **kwargs)
                    except Exception as e:
                        return await session.exec_command_async(sess_cmd)
            
            else:
                if cmd in self._commands_alias.keys():
                    cmd = self._commands_alias[cmd]

                handler = self._cmds_handler.get(cmd, None)
                if handler and callable(handler):
                    if asyncio.iscoroutinefunction(handler):
                        await self.create_task(handler(code = cl, *args, **kwargs))
                    else:
                        handler(code = cl, *args, **kwargs)
                else:
                    self.warning(Settings.gettext("msg_cmd_not_recognized", cl.commandText))

        else:
            cmdtext, code = cl.expand(self, *args, **kwargs)
            return await self.exec_text_async(cmdtext)
            
    def exec_text(self, cmdtext: str):
        """
        执行文本形式的MUD命令。必定为单个命令，且确定不是#开头的，同时不进行参数替代

        一般情况下，脚本中不应调用该方法，而应使用 exec/exec_command。

        :param cmdtext: 纯文本命令
        """
        isNotCmd = True

        # fix bugs, commands filter for enabled and sorted for priority
        avai_cmds = [cmd for cmd in self._commands.values() if isinstance(cmd, Command) and cmd.enabled]
        avai_cmds.sort(key = lambda cmd: cmd.priority)

        for command in self._commands.values():
            state = command.match(cmdtext)
            if state.result == Command.SUCCESS:
                # 命令的任务名称采用命令id，以便于后续查错
                self.create_task(command.execute(cmdtext), name = "task-{0}".format(command.id))
                isNotCmd = False
                break

        # 再判断是否是别名
        if isNotCmd:
            notAlias = True

            # fix bugs, aliases filter for enabled and sorted for priority, and add oneShot, keepEval judge
            avai_alis = [ali for ali in self._aliases.values() if isinstance(ali, Alias) and ali.enabled]
            avai_alis.sort(key = lambda ali: ali.priority)
 
            for alias in avai_alis:               
                state = alias.match(cmdtext)
                if state.result == Alias.SUCCESS:
                    notAlias = False
                    if alias.oneShot:
                        self.delAlias(alias.id)

                    if not alias.keepEval:
                        break

            # 都不是则是普通命令，直接发送
            if notAlias:
                self.writeline(cmdtext)

    async def exec_text_async(self, cmdtext: str):
        """
        该方法为 exec_text 的异步形式实现。一般情况下，脚本中不应调用该方法，而应使用 exec_async/exec_command_async。

        异步调用时，该函数要等待对应的代码执行完毕后才会返回。可以用于确保命令执行完毕。
        """
        result = None
        isNotCmd = True

        # fix bugs, commands filter for enabled and sorted for priority
        avai_cmds = [cmd for cmd in self._commands.values() if isinstance(cmd, Command) and cmd.enabled]
        avai_cmds.sort(key = lambda cmd: cmd.priority)

        for command in avai_cmds:
            state = command.match(cmdtext)
            if state.result == Command.SUCCESS:
                # 命令的任务名称采用命令id，以便于后续查错
                result = await self.create_task(command.execute(cmdtext), name = "task-{0}".format(command.id))
                isNotCmd = False
                break

        # 再判断是否是别名
        if isNotCmd:
            notAlias = True

            # fix bugs, aliases filter for enabled and sorted for priority, and add oneShot, keepEval judge
            avai_alis = [ali for ali in self._aliases.values() if isinstance(ali, Alias) and ali.enabled]
            avai_alis.sort(key = lambda ali: ali.priority)
 
            for alias in avai_alis:               
                state = alias.match(cmdtext)
                if state.result == Alias.SUCCESS:
                    notAlias = False
                    if alias.oneShot:
                        self.delAlias(alias.id)

                    if not alias.keepEval:
                        break

            # 都不是则是普通命令，直接发送
            if notAlias:
                self.writeline(cmdtext)

        return result

    def exec_command(self, line: str, *args, **kwargs) -> None:
        """
        在当前会话中执行MUD命令。多个命令可以用分隔符隔开。

        - 此函数中，多个命令是一次性发送到服务器的，并未进行等待确认上一条命令执行完毕。
        - 若要等待每一个命令执行完毕后再进行下一个命令，则应使用本函数的异步形式 exec_command_async
        - 本函数和writeline的区别在于，本函数会先进行Command和Alias解析，若不是再使用writeline发送
        - 当line不包含Command和Alias时，等同于writeline
        - 本函数使用方法与 exec 相同，差异在于不能指定会话名
        - exec 是后来增加的函数，因此保留 exec_command 的目的是为了脚本的向前兼容

        :param line: 需指定的内容
        :param args: 保留兼容性与扩展性需要
        :param kwargs: 保留兼容性与扩展性需要
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
        """
        延时一段时间之后，执行命令exec_command

        :param wait: float, 延时等待时间，单位为秒。
        :param line: str, 延时等待结束后执行的内容
        """
        async def delay_task():
            await asyncio.sleep(wait)
            self.exec_command(line)
        
        self.create_task(delay_task())

    async def exec_command_async(self, line: str, *args, **kwargs):
        """
        exec_command 的异步形式。在当前会话中执行MUD命令。多个命令可以用分隔符隔开。

        - 异步时，多个命令是逐个发送到服务器的，每一命令都等待确认上一条命令执行完毕，且多命令之间会插入一定时间等待
        - 多个命令之间的间隔等待时间由 Settings.client["interval"] 指定，单位为 ms
        - 本函数使用方法与 exec_async 相同，差异在于不能指定会话名
        - exec_async 是后来增加的函数，因此保留 exec_command_async 的目的是为了脚本的向前兼容
        """

        ## 以下为函数执行本体
        result = None
        if (not "#" in line) and (not "@" in line) and (not "%" in line):
            cmds = line.split(self.seperator)
            for cmd in cmds:
                result = await self.exec_text_async(cmd)
                if Settings.client["interval"] > 0:
                    await asyncio.sleep(Settings.client["interval"] / 1000.0)
        else:
            cb = CodeBlock(line)
            result = await cb.async_execute(self)

        return result

    def write_eof(self) -> None:
        """
        向服务器发送 eof 信息，即与服务器断开连接。 **脚本中无需调用。**
        
        若要在脚本中控制断开与服务器的连接，请使用 session.disconnect()
        """
        self._transport.write_eof()
    
    def getUniqueNumber(self):
        """
        获取本session中的唯一数值。该方法用来为各类对象生成随机不重复ID

        :return: 返回为整数，返回结果在本会话中唯一。
        """
        self._uid += 1
        return self._uid

    def getUniqueID(self, prefix):
        """
        根据唯一编号获取本session中的唯一名称, 格式为: prefix_uid

        :param prefix: 为唯一数值增加的前缀
        :return: 形式为 prefix_uid 的唯一标识
        """
        return "{0}_{1}".format(prefix, self.getUniqueNumber())

    def enableGroup(self, group: str, enabled = True):
        """
        使能或禁用Group中所有对象, 返回组内各对象个数。
        
        :param group: 组名，即各对象的 group 属性的值
        :param enabled: 使能/禁用开关。为True时表示使能， False为禁用
        :return: 5个整数的列表，依次表示改组内操作的 别名，触发器，命令，定时器，GMCP 的个数
        """
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

    def _addObjects(self, objs):
        if isinstance(objs, list) or isinstance(objs, tuple):
            for item in objs:
                self._addObject(item)

        elif isinstance(objs, dict):
            for key, item in objs.items():
                if isinstance(item, BaseObject):
                    if key != item.id:
                        self.warning(Settings.gettext("msg_id_not_consistent", item, key, item.id))

                    self._addObject(item)

    def _addObject(self, obj):
        if isinstance(obj, Alias):
            self._aliases[obj.id] = obj
        elif isinstance(obj, Command):
            self._commands[obj.id] = obj
        elif isinstance(obj, Trigger):
            self._triggers[obj.id] = obj
        elif isinstance(obj, Timer):
            self._timers[obj.id] = obj
        elif isinstance(obj, GMCPTrigger):
            self._gmcp[obj.id] = obj

    def addObject(self, obj: BaseObject):
        """
        向会话中增加单个对象，可直接添加 Alias, Trigger, GMCPTrigger, Command, Timer 或它们的子类

        :param obj: 特定对象本身，可以为 Alias, Trigger, GMCPTrigger, Command, Timer 或其子类

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session
                    
                        self.session.addObject(SimpleAlias(session, r'^gta$', 'get all'),)
                        self.session.addObject(SimpleTrigger(session, r'^[> ]*你嘻嘻地笑了起来.+', 'haha'))
                        self.session.addObject(SimpleTimer(session, 'xixi', timeout = 10))

        """
        self._addObject(obj)

    def addObjects(self, objs):
        """
        向会话中增加多个对象，可直接添加 Alias, Trigger, GMCPTrigger, Command, Timer 或它们的子类的元组、列表或者字典(保持兼容性)

        :param objs: 多个特定对象组成的元组、列表或者字典，可以为 Alias, Trigger, GMCPTrigger, Command, Timer 或其子类

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session
                    
                        self.objs = [
                            SimpleAlias(session, r'^gta$', 'get all;xixi'),
                            SimpleTrigger(session, r'^[> ]*你嘻嘻地笑了起来.+', 'haha'),
                            SimpleTimer(session, 'xixi', timeout = 10)
                        ]

                        self.session.addObjects(self.objs)

        """
        self._addObjects(objs)

    def _delObject(self, id, cls: type):
        if cls == Alias:
            self._aliases.pop(id, None)
        elif cls == Command:
            cmd = self._commands.pop(id, None)
            if isinstance(cmd, Command):
                cmd.reset()
                cmd.unload()
                cmd.__unload__()

        elif cls == Trigger:
            self._triggers.pop(id, None)
        elif cls == Timer:
            timer = self._timers.pop(id, None)
            if isinstance(timer, Timer):
                timer.enabled = False
        elif cls == GMCPTrigger:
            self._gmcp.pop(id, None)


    def _delObjects(self, ids: Iterable, cls: type):
        "删除多个指定元素"
        for id in ids:
            self._delObject(id, cls)

    def delObject(self, obj):
        """
        从会话中移除一个对象，可直接删除 Alias, Trigger, GMCPTrigger, Command, Timer 或它们的子类本身
        
        ** 注 ** 现在 delObject 和 delObjects 使用结果相同，都可以清除单个对象、对个对象的list, tuple或dict, 可以有效防止代码写错

        :param obj: 要删除的多个特定对象组成的元组、列表或者字典，可以为 Alias, Trigger, GMCPTrigger, Command, Timer 或其子类

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session

                        ali = SimpleAlias(session, r'^gta$', 'get all', id = 'my_ali1')
                        
                        # 以下几种方式均可将该别名添加到会话
                        session.addObject(ali)
                        session.addAlias(ali)

                        # 以下三种方式均可以删除该别名
                        session.delObject(ali)
                        session.delAlias(ali)
                        session.delAlias("my_ali1")

        """
        if isinstance(obj, Alias):
            self._aliases.pop(obj.id, None)
        elif isinstance(obj, Command):
            obj.reset()
            obj.unload()
            obj.__unload__()
            self._commands.pop(obj.id, None)
        elif isinstance(obj, Trigger):
            self._triggers.pop(obj.id, None)
        elif isinstance(obj, Timer):
            obj.enabled = False
            self._timers.pop(obj.id, None)
        elif isinstance(obj, GMCPTrigger):
            self._gmcp.pop(obj.id, None)

        elif isinstance(obj, (list, tuple, dict)):
            self.delObjects(obj)

    def delObjects(self, objs):
        """
        从会话中移除一组对象，可直接删除多个 Alias, Trigger, GMCPTrigger, Command, Timer
        
        ** 注 ** 现在 delObject 和 delObjects 使用结果相同，都可以清除单个对象、对个对象的list, tuple或dict, 可以有效防止代码写错

        :param objs: 要删除的一组对象的元组、列表或者字典(保持兼容性)，其中对象可以为 Alias, Trigger, GMCPTrigger, Command, Timer 或它们的子类

        示例:

        .. code:: Python

            class Configuration:
                def __init__(self, session):
                    self.session = session
                
                    self.objs = [
                        SimpleAlias(session, r'^gta$', 'get all;xixi'),
                        SimpleTrigger(session, r'^[> ]*你嘻嘻地笑了起来.+', 'haha'),
                        SimpleTimer(session, 'xixi', timeout = 10)
                    ]

                    self.session.addObjects(self.objs)

                def __unload__(self):
                    "卸载本模块时，删除所有本模块添加的对象"
                    self.session.delObjects(self.objs)

        """
        if isinstance(objs, list) or isinstance(objs, tuple):
            for item in objs:
                self.delObject(item)

        elif isinstance(objs, dict):
            for key, item in objs.items():
                self.delObject(item)

        elif isinstance(objs, BaseObject):
            self.delObject(objs)

    def addAliases(self, alis):
        """
        向会话中增加多个别名

        :param alis: 多个别名的字典。字典 key 应为每个别名的 id。

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session
                        self._aliases = dict()

                        self._initAliases()

                    def _initAliases(self):
                        self._aliases['my_ali1'] = SimpleAlias(self.session, "n", "north", id = "my_ali1")
                        self._aliases['my_ali2'] = SimpleAlias(self.session, "s", "south", id = "my_ali2")
                        self.session.addAliases(self._aliases)
        """
        self._addObjects(alis)

    def addCommands(self, cmds):
        """
        向会话中增加多个命令。使用方法与 addAliases 类似。

        :param cmds: 多个命令的字典。字典 key 应为每个命令的 id。
        """
        self._addObjects(cmds)

    def addTriggers(self, tris):
        """
        向会话中增加多个触发器。使用方法与 addAliases 类似。

        :param tris: 多个触发器的字典。字典 key 应为每个触发器的 id。
        """
        self._addObjects(tris)

    def addGMCPs(self, gmcps):
        """
        向会话中增加多个GMCPTrigger。使用方法与 addAliases 类似。

        :param gmcps: 多个GMCPTrigger的字典。字典 key 应为每个GMCPTrigger的 id。
        """
        self._addObjects(gmcps)

    def addTimers(self, tis):
        """
        向会话中增加多个定时器。使用方法与 addAliases 类似。

        :param tis: 多个定时器的字典。字典 key 应为每个定时器的 id。
        """
        self._addObjects(tis)

    def addAlias(self, ali):
        """
        向会话中增加一个别名。

        :param ali: 要增加的别名对象，应为 Alias 类型或其子类
        """
        self._addObject(ali)

    def addCommand(self, cmd):
        """
        向会话中增加一个命令。

        :param cmd: 要增加的命令对象，应为 Command 类型或其子类
        """
        self._addObject(cmd)

    def addTrigger(self, tri: Trigger):
        """
        向会话中增加一个触发器。

        :param tri: 要增加的触发器对象，应为 Trigger 类型或其子类
        """
        self._addObject(tri)

    def addTimer(self, ti: Timer):
        """
        向会话中增加一个定时器。

        :param ti: 要增加的定时器对象，应为 Timer 类型或其子类
        """
        self._addObject(ti)

    def addGMCP(self, gmcp: GMCPTrigger):
        """
        向会话中增加一个GMCP触发器。

        :param gmcp: 要增加的GMCP触发器对象，应为 GMCPTrigger 类型或其子类
        """

        self._addObject(gmcp)

    def delAlias(self, ali):
        """
        从会话中移除一个别名，可接受 Alias 对象或其 id
        
        :param ali: 要删除的别名指代，可以为别名 id 或者别名自身

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session

                        ali = Alias(session, "s", "south", id = "my_ali1")
                        session.addAlias(ali)

                        # 以下两行语句均可以删除该别名
                        session.delAlias("my_ali1")
                        session.delAlias(ali)
        """
        if isinstance(ali, Alias):
            self._delObject(ali.id, Alias)
        elif isinstance(ali, str) and (ali in self._aliases.keys()):
            self._delObject(ali, Alias)

    def delAliases(self, ali_es: Iterable):
        """
        从会话中移除一组别名，可接受 Alias 对象或其 id 的迭代器
        
        :param ali_es: 要删除的一组别名指代，可以为别名 id 或者别名自身的列表

        示例:
            .. code:: Python

                class Configuration:
                    def __init__(self, session):
                        self.session = session
                        self._aliases = dict()

                        self._aliases["my_ali1"] = Alias(session, "s", "south", id = "my_ali1")
                        self._aliases["my_ali2"] = Alias(session, "n", "north", id = "my_ali2")
                        
                        session.addAliases(self._aliase)

                        # 以下两行语句均可以删除两个别名
                        session.delAliases(self._aliases)
                        session.delAliases(self._aliases.keys())
        """
        for ali in ali_es:
            self.delAlias(ali)

    def delCommand(self, cmd):
        """
        从会话中移除一个命令，可接受 Command 对象或其 id。使用方法与 delAlias 类似
        
        :param cmd: 要删除的命令指代，可以为命令id或者命令自身
        """
        if isinstance(cmd, Command):
            cmd.reset()
            self._delObject(cmd.id, Command)
        elif isinstance(cmd, str) and (cmd in self._commands.keys()):
            self._commands[cmd].reset()
            self._delObject(cmd, Command)

    def delCommands(self, cmd_s: Iterable):
        """
        从会话中移除一组命令，可接受可接受 Command 对象或其 id 的迭代器。使用方法与 delAliases 类似
        
        :param cmd_s: 要删除的命令指代，可以为命令 id 或者命令自身的列表
        """
        for cmd in cmd_s:
            self.delCommand(cmd)

    def delTrigger(self, tri):
        """
        从会话中移除一个触发器，可接受 Trigger 对象或其的id。使用方法与 delAlias 类似
        
        :param tri: 要删除的触发器指代，可以为触发器 id 或者触发器自身
        """

        if isinstance(tri, Trigger):
            self._delObject(tri.id, Trigger)
        elif isinstance(tri, str) and (tri in self._triggers.keys()):
            self._delObject(tri, Trigger)

    def delTriggers(self, tri_s: Iterable):
        """
        从会话中移除一组触发器，可接受可接受 Trigger 对象或其 id 的迭代器。使用方法与 delAliases 类似
        
        :param tri_s: 要删除的触发器指代，可以为触发器 id 或者触发器自身的列表
        """
        for tri in tri_s:
            self.delTrigger(tri)

    def delTimer(self, ti):
        """
        从会话中移除一个定时器，可接受 Timer 对象或其的id。使用方法与 delAlias 类似
        
        :param ti: 要删除的定时器指代，可以为定时器 id 或者定时器自身
        """

        if isinstance(ti, Timer):
            ti.enabled = False
            self._delObject(ti.id, Timer)
        elif isinstance(ti, str) and (ti in self._timers.keys()):
            self._timers[ti].enabled = False
            self._delObject(ti, Timer)

    def delTimers(self, ti_s: Iterable):
        """
        从会话中移除一组定时器，可接受可接受 Timer 对象或其 id 的迭代器。使用方法与 delAliases 类似
        
        :param ti_s: 要删除的定时器指代，可以为定时器 id 或者定时器自身的列表
        """
        for ti in ti_s:
            self.delTimer(ti)

    def delGMCP(self, gmcp):
        """
        从会话中移除一个GMCP触发器，可接受 GMCPTrigger 对象或其的id。使用方法与 delAlias 类似
        
        :param gmcp: 要删除的GMCP触发器指代，可以为GMCP触发器 id 或者GMCP触发器自身
        """
        if isinstance(gmcp, GMCPTrigger):
            self._delObject(gmcp.id, GMCPTrigger)
        elif isinstance(gmcp, str) and (gmcp in self._gmcp.keys()):
            self._delObject(gmcp, GMCPTrigger)

    def delGMCPs(self, gmcp_s: Iterable):
        """
        从会话中移除一组GMCP触发器，可接受可接受 GMCPTrigger 对象或其 id 的迭代器。使用方法与 delAliases 类似
        
        :param gmcp_s: 要删除的GMCP触发器指代，可以为 id 或者GMCP触发器自身的列表
        """
        for gmcp in gmcp_s:
            self.delGMCP(gmcp)

    def replace(self, newstr):
        """
        将当前行内容显示替换为newstr。该方法仅在用于触发器的同步处置中才能正确相应

        :param newstr: 替换后的内容
        """
        if len(newstr) > 0:
            newstr += Settings.client["newline"]
        self.display_line = newstr


    ## ###################
    ## 变量 Variables 处理
    ## ###################
    def delVariable(self, name):
        """
        删除一个变量。删除变量是从session管理的变量列表中移除关键字，而不是设置为 None
        
        :param name: 变量名
        """
        assert isinstance(name, str), Settings.gettext("msg_shall_be_string", "name")
        if name in self._variables.keys():
            self._variables.pop(name)

    def setVariable(self, name, value):
        """
        设置一个变量的值。可以使用vars快捷点访问器实现同样效果。
        
        :param name: 变量名。变量名必须为一个字符串
        :param value: 变量的值。变量值可以为任意 Python 类型。但为了要保存变量数据到硬盘，建议使用可序列化类型。

        示例:
            .. code:: Python

                # 以下两种方式等价
                session.setVariable("myvar1", "the value")
                session.vars.myvar1 = "the value"
        """
        assert isinstance(name, str), Settings.gettext("msg_shall_be_string", "name")
        self._variables[name] = value

    def getVariable(self, name, default = None):
        """
        获取一个变量的值。可以使用vars快捷点访问器实现类似效果，但vars访问时，默认值总为None。
        
        :param name: 变量名。变量名必须为一个字符串
        :param default: 当会话中不存在该变量时，返回的值。默认为 None。
        :return: 变量的值，或者 default

        示例:
            .. code:: Python

                # 以下两种方式等价
                myvar = session.getVariable("myvar1", None)
                myvar = session.vars.myvar1
        """
        """获取一个变量的值. 当name指定的变量不存在时，返回default"""
        assert isinstance(name, str), Settings.gettext("msg_shall_be_string", "name")
        return self._variables.get(name, default)
    
    def setVariables(self, names, values):
        """
        同时设置一组变量的值。要注意，变量名称和值的数量要相同。当不相同时，抛出异常。

        :param names: 所有变量名的元组或列表
        :param values: 所有变量对应值的元祖或列表

        示例:
            .. code:: Python

                hp_key   = ("qi", "jing", "neili", "jingli")
                hp_value = [1000, 800, 1100, 1050]

                session.setVariables(hp_key, hp_value)
        """
        assert isinstance(names, tuple) or isinstance(names, list), Settings.gettext("msg_shall_be_list_or_tuple", "names")
        assert isinstance(values, tuple) or isinstance(values, list), Settings.gettext("msg_shall_be_list_or_tuple", "values")
        assert (len(names) > 0) and (len(values) > 0) and (len(names) == len(values)), Settings.gettext("msg_names_and_values")
        for index in range(0, len(names)):
            name  = names[index]
            value = values[index]
            self.setVariable(name, value)

    def getVariables(self, names):
        """
        同时获取一组变量的值。

        :param names: 所有变量名的元组或列表
        :return: 返回所有变量值的元组。可在获取值时直接解包。

        示例:
            .. code:: Python

                qi, jing, neili, jingli = session.getVariables(["qi", "jing", "neili", "jingli"])
        """
        assert isinstance(names, tuple) or isinstance(names, list), Settings.gettext("msg_shall_be_list_or_tuple", "names")
        assert len(names) > 0, Settings.gettext("msg_not_null", "names")
        values = list()
        for name in names:
            value = self.getVariable(name)
            values.append(value)
        
        return tuple(values)
    
    def updateVariables(self, kvdict: dict):
        """
        使用字典更新一组变量的值。若变量不存在将自动添加。

        :param kvdict: 变量/值的字典

        示例:
            .. code:: Python
                
                newvars = {"qi": 1000, "jing": 800, "neili": 1100, "jingli": 1050}
                session.updateVariables(newvars)
        """

        self._variables.update(kvdict)

    ## ###################
    ## 全局变量 Globals 处理
    ## ###################
    def delGlobal(self, name):
        """
        删除一个全局变量，使用方式与会话变量variable相同

        :param name: 全局变量的名称
        """
        assert isinstance(name, str), Settings.gettext("msg_shall_be_string", "name")
        self.application.del_globals(name)

    def setGlobal(self, name, value):
        """
        设置一个全局变量的值，使用方式与会话变量variable相同
        
        :param name: 全局变量的名称
        :param value: 全局变量的值
        """
        assert isinstance(name, str), Settings.gettext("msg_shall_be_string", "name")
        self.application.set_globals(name, value)

    def getGlobal(self, name, default = None):
        """
        获取一个全局变量的值，使用方式与会话变量variable相同
        
        :param name: 全局变量的名称
        :param default: 当全局变量不存在时的返回值
        :return: 全局变量的值，或者 default
        """

        assert isinstance(name, str), Settings.gettext("msg_shall_be_string", "name")
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
                docstring = Settings.gettext("msg_topic_not_found", topic)
            
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

        #self.application.close_session()
        self.application.act_close_session()

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
            - #disconnect
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
                time_msg += f"{hour} {Settings.gettext('Hour')}"
            if min > 0:
                time_msg += f"{min} {Settings.gettext('Minute')}"
            time_msg += f"{math.ceil(sec)} {Settings.gettext('Second')}"

            self.info(Settings.gettext("msg_connection_duration",time_msg))

    def handle_disconnect(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #disconnect / #dis 的执行函数，断开到远程服务器的连接（仅当远程服务器已连接时有效）。
        该函数不应该在代码中直接调用。
        
        相关命令:
            - #connect
            - #close
        '''

        self.disconnect()

    def getMaxLength(self, iter: Iterable):
        return wcswidth(sorted(iter, key = lambda s: wcswidth(s), reverse = True)[0])

    def splitByPrintableWidth(self, str, printable_length):
        strlist = []
        startindex = 0
        remain = False
        split_str = ""
        for idx in range(1, len(str)):
            remain = True
            split_str = str[startindex:idx]
            if wcswidth(split_str) >= printable_length:
                strlist.append(split_str)
                startindex = idx
                remain = False

        if remain:
            strlist.append(str[startindex:])

        return strlist

    def buildDisplayLines(self, vars: DotDict, title: str):
        MIN_MARGIN = 4
        KEY_WIDTH = (self.getMaxLength(vars.keys()) // 4) * 4 + 4
        VALUE_WIDTH = 20
        VAR_WIDTH = KEY_WIDTH + 3 + VALUE_WIDTH
        display_lines = []
        vars_simple = {}
        vars_complex = {}

        for k, v in vars.items():
            if k in ("%line", "%raw", "%copy"):
                continue

            if dataclasses.is_dataclass(v) or (isinstance(v, Iterable) and not isinstance(v, str)):
                vars_complex[k] = v
            else:
                vars_simple[k] = v

        totalWidth = self.application.get_width() - 2

        # draw title
        left_margin = (totalWidth - len(title)) // 2
        right_margin = totalWidth - len(title) - left_margin
        title_line = "{}{}{}".format("=" * left_margin, title, "=" * right_margin)
        display_lines.append(title_line)

        # draw simple vars
        vars_per_line = totalWidth // VAR_WIDTH
        left_margin   = (totalWidth - vars_per_line * VAR_WIDTH) // 2
        left_margin = min(MIN_MARGIN, left_margin)
        right_margin = totalWidth - vars_per_line * VAR_WIDTH - left_margin
        right_margin = min(left_margin, right_margin)

        line = " " * left_margin
        cursor = left_margin
        var_count = 0

        var_keys = sorted(vars_simple.keys())
        for key in var_keys:
            if len(key) < KEY_WIDTH:
                name = key.rjust(KEY_WIDTH)
            else:
                name = key.rjust(KEY_WIDTH + VAR_WIDTH)

            value_dis = vars_simple[key].__repr__()
            var_display = "{0} = {1}".format(name, value_dis)
            
            if (cursor + wcswidth(var_display) > totalWidth) or (var_count >= vars_per_line):
                display_lines.append(line)

                line = " " * left_margin
                cursor = left_margin
                var_count = 0

            line += var_display
            cursor += wcswidth(var_display)
            var_count += 1

            # 下一处判定
            for x in range(vars_per_line, 0, -1):
                next_start = left_margin + (vars_per_line - x) * VAR_WIDTH
                if cursor < next_start:
                    line += " " * (next_start - cursor)
                    cursor = next_start

                    if (vars_per_line - x) > var_count:
                        var_count = (vars_per_line - x)
                    break

        if cursor > left_margin:
            display_lines.append(line)

        var_keys = sorted(vars_complex.keys())
        for key in var_keys:
            name = key.rjust(KEY_WIDTH)
            value_dis = vars_complex[key].__repr__()
            allow_len = totalWidth - left_margin - KEY_WIDTH - 3 - right_margin
            line = "{0}{1} = ".format(" " * left_margin, name.rjust(KEY_WIDTH))
            if wcswidth(value_dis) > allow_len:
                value = vars_complex[key]
                if isinstance(value, dict):
                    max_len = self.getMaxLength(value.keys())
                    line += '{'
                    display_lines.append(line)
                    line = " " * (left_margin + KEY_WIDTH + 4)
                    for k, v in value.items():
                        subvalue_dis = "{},".format(v.__repr__())
                        allow_len_subvalue = allow_len - max_len - 4
                        if wcswidth(subvalue_dis) > allow_len_subvalue:
                            subvalue_lines = self.splitByPrintableWidth(subvalue_dis, allow_len_subvalue)
                            line += "{0}: ".format(k.ljust(max_len))
                            for subline in subvalue_lines:
                                line += subline
                                display_lines.append(line)
                                line = " " * (left_margin + KEY_WIDTH + 4 + max_len + 2)

                            line = " " * (left_margin + KEY_WIDTH + 4)
                        else:
                            val_line = "{0}: {1}".format(k.ljust(max_len), subvalue_dis)
                            line += val_line
                            display_lines.append(line)
                            line = " " * (left_margin + KEY_WIDTH + 4)
                    line = line[:-1] + '}'
                    display_lines.append(line)
                elif isinstance(value, list):
                    line += '['
                    for v in value:
                        val_line = "{0},".format(v.__repr__())
                        line += val_line
                        display_lines.append(line)
                        line = " " * (left_margin + KEY_WIDTH + 4)
                    line = line[:-1] + ']'
                    display_lines.append(line)
                else:
                    value_lines = self.splitByPrintableWidth(value_dis, allow_len)
                    for val_line in value_lines:
                        line += val_line
                        display_lines.append(line)
                        line = " " * (left_margin + KEY_WIDTH + 3)
            else:   
                line = "{0}{1} = {2}".format(" " * left_margin, key.rjust(KEY_WIDTH), vars_complex[key].__repr__())
                display_lines.append(line)
                                            
        display_lines.append("=" * totalWidth)

        return display_lines
            
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

        new_cmd_text, new_code = code.expand(self, *args, **kwargs)
        args = new_code[2:]

        #args = code.code[2:]

        if len(args) == 0:
            lines = self.buildDisplayLines(self._variables, f"  VARIABLE LIST IN SESSION {self.name}  ")
            
            for line in lines:
                self.writetobuffer(line, newline = True)

        elif len(args) == 1:
            if args[0] in self._variables.keys():
                obj = self.getVariable(args[0])
                var_dict = {args[0] : obj}
                lines = self.buildDisplayLines(var_dict, f" VARIABLE [{args[0]}] IN SESSION {self.name} ")

                for line in lines:
                    self.writetobuffer(line, newline = True)
                    
            else:
                self.warning(Settings.gettext("msg_no_object", args[0], Settings.gettext("variable")))
            
        elif len(args) == 2:
            val = None
            try:
                val = eval(args[1])
            except:
                val = args[1]

            self.setVariable(args[0], val)
            self.info(Settings.gettext("msg_object_value_setted", Settings.gettext("variable"), args[0], val.__repr__()))

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

        new_cmd_text, new_code = code.expand(self, *args, **kwargs)
        args = new_code[2:]
        #args = code.code[2:]

        if len(args) == 0:
            lines = self.buildDisplayLines(self.application.globals, f" GLOBAL VARIABLES LIST ")
            
            for line in lines:
                self.writetobuffer(line, newline = True)

        elif len(args) == 1:
            var = args[0]
            if var in self.application.globals.keys():
                # self.info("{0:>20} = {1:<22}".format(var, self.application.get_globals(var).__repr__()), "全局变量")

                var_dict = {var : self.application.get_globals(var)}
                lines = self.buildDisplayLines(var_dict, f" GLOBAL VARIABLE [{var}] ")

                for line in lines:
                    self.writetobuffer(line, newline = True)
            else:
                self.warning(Settings.gettext("msg_no_global_object", var, Settings.gettext("variable")))
            
        elif len(args) == 2:
            val = None
            try:
                val = eval(args[1])
            except:
                val = args[1]
            self.application.set_globals(args[0], val)
            self.info(Settings.gettext("msg_object_value_setted", Settings.gettext("globalvar"), args[0], val.__repr__()))

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
                self.warning(Settings.gettext("msg_object_not_exists", args[0], name))

        elif len(args) == 2:
            # 当第一个参数为对象obj名称时，对对象进行处理
            if args[0] in objs.keys():
                obj = objs[args[0]]
                if args[1] == "on":
                    obj.enabled = True
                    self.info(Settings.gettext("msg_object_enabled", obj.__repr__()))
                elif args[1] == "off":
                    obj.enabled = False
                    self.info(Settings.gettext("msg_object_disabled", obj.__repr__()))
                elif args[1] == "del":
                    obj.enabled = False
                    objs.pop(args[0])
                    self.info(Settings.gettext("msg_object_deleted", obj.__repr__()))
                else:
                    self.error(Settings.gettext("msg_invalid_param", name.lower()))
            
            else:
                pattern, code = args[0], args[1]
                if (len(pattern)>=2) and (pattern[0] == '{') and (pattern[-1] == '}'):
                    pattern = pattern[1:-1]

                name = name.lower()
                if name == "alias":
                    ali = SimpleAlias(self, pattern, code)
                    self.addAlias(ali)
                    self.info(Settings.gettext("msg_alias_created", ali.id, ali.__repr__()))
                elif name == "trigger":
                    tri = SimpleTrigger(self, pattern, code)
                    self.addTrigger(tri)
                    self.info(Settings.gettext("msg_trigger_created", tri.id, tri.__repr__()))
                elif name == "timer":
                    if pattern.isnumeric():
                        timeout = float(pattern)
                        if timeout > 0:
                            ti  = SimpleTimer(self, code, timeout = timeout)
                            self.addTimer(ti)
                            self.info(Settings.gettext("msg_timer_created", ti.id, ti.__repr__()))

    def handle_alias(self, code: CodeLine = None, *args, **kwargs):
        r"""
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
        """

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
                self.info(Settings.gettext("msg_ignore_on"))
            else:
                self.info(Settings.gettext("msg_ignore_off"))
        elif cmd == "t+":
            if code.length <= 2:
                self.warning(Settings.gettext("msg_T_plus_incorrect"))
                return
            
            groupname = code.code[2]
            cnts = self.enableGroup(groupname)
            self.info(Settings.gettext("msg_group_enabled", groupname, *cnts))

        elif cmd == "t-":
            if code.length <= 2:
                self.warning(Settings.gettext("msg_T_minus_incorrect"))
                return
            
            groupname = code.code[2]
            cnts = self.enableGroup(groupname, False)
            self.info(Settings.gettext("msg_group_disabled", groupname, *cnts))

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
            self.info(Settings.gettext("msg_repeat_invalid"))

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

        title = Settings.gettext("msg_window_title", self.name)

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
        """
        清除会话有关任务项和事件标识，具体包括：
        
        - 复位所有可能包含异步操作的对象，包括定时器、触发器、别名、GMCP触发器、命令
        - 取消所有由本会话管理但仍未完成的任务
        - 清空会话管理的所有任务
        """
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
        """
        复位：清除所有异步项和等待对象，卸载所有模块，清除所有会话有关对象。
        """
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
        """
        模块加载函数。

        :param module_names: 要加载的模块清单。为元组/列表时，加载指定名称的系列模块，当名称为字符串时，加载单个模块。

        示例:
            - session.load_module('mymodule'):  加载名为mymodule.py文件对应的模块
            - session.load_modules(['mymod1', 'mymod2']): 依次加载mymod1.py与mymod2.py文件对应的模块
        """
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
                self._modules[module_name] = ModuleInfo(module_name, self)

            else:
                mod = self._modules[module_name]
                if isinstance(mod, ModuleInfo):
                    mod.reload()

        except Exception as e:
            import traceback
            self.error(Settings.gettext("msg_module_load_fail", module_name, e, type(e)))
            self.error(Settings.gettext("msg_exception_traceback", traceback.format_exc()))

    def unload_module(self, module_names):
        """
        模块卸载函数。卸载模块时，将自动调用模块中名称为Configuration类对象的unload方法。

        一般使用 #unload 命令来卸载模块，而不是在脚本中使用 unload_module 函数来卸载模块

        :param module_names: 要卸载的模块清单。为元组/列表时，卸载指定名称的系列模块，当名称为字符串时，卸载单个模块。
        """

        if isinstance(module_names, (list, tuple)):
            for mod in module_names:
                mod = mod.strip()
                self._unload_module(mod)

        elif isinstance(module_names, str):
            mod = module_names.strip()
            self._unload_module(mod)

    def _unload_module(self, module_name):
        "卸载指定名称模块。卸载支持需要模块的Configuration实现 __unload__ 或 unload 方法"
        if module_name in self._modules.keys():
            mod = self._modules.pop(module_name)
            if isinstance(mod, ModuleInfo):
                mod.unload()

        else:
            self.warning(Settings.gettext("msg_module_not_loaded", module_name))

    def reload_module(self, module_names = None):
        """
        模块重新加载函数。

        一般使用 #reload 命令来重新加载模块，而不是在脚本中使用 reload_module 函数来重新加载模块

        :param module_names: 要重新加载的模块清单。为元组/列表时，卸载指定名称的系列模块，当名称为字符串时，卸载单个模块。当不指定时，重新加载所有已加载模块。
        """
        if module_names is None:
            for name, module in self._modules.items():
                if isinstance(module, ModuleInfo):
                    module.reload()

            self.info(Settings.gettext("msg_all_module_reloaded"))

        elif isinstance(module_names, (list, tuple)):
            for mod in module_names:
                mod = mod.strip()
                if mod in self._modules.keys():
                    module = self._modules[mod]
                    if isinstance(module, ModuleInfo):
                        module.reload()
                else:
                    self.warning(Settings.gettext("msg_module_not_loaded", mod))

        elif isinstance(module_names, str):
            if module_names in self._modules.keys():
                module = self._modules[module_names]
                if isinstance(module, ModuleInfo):
                    module.reload()
            else:
                self.warning(Settings.gettext("msg_module_not_loaded", module_names))
        

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
                    self.info(Settings.gettext("msg_plugin_reloaded", mod))
                else:
                    self.warning(Settings.gettext("msg_name_not_found", mod))

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

        args = code.code[2:]
        
        if len(args) == 0:
            count = len(self._modules.keys())
            if count == 0:
                self.info(Settings.gettext("msg_no_module"), "MODULES")
            else:
                self.info(Settings.gettext("msg_module_list", count, list(self._modules.keys()).__repr__()))
    
        elif len(args) >= 1:
            modules = ",".join(args).split(",")
            for mod in modules:
                if mod in self._modules.keys():
                    module = self._modules[mod]
                    if isinstance(module, ModuleInfo):
                        if module.ismainmodule:
                            self.info(Settings.gettext("msg_module_configurations", module.name, ",".join(module.config.keys())))
                        else:
                            self.info(Settings.gettext("msg_submodule_no_config"))

                else:
                    self.info(Settings.gettext("msg_module_not_loaded", mod))

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
        嵌入命令 #save 的执行函数，保存当前会话变量（系统变量和临时变量除外）至文件。该命令不带参数。
        系统变量包括 %line, %copy 和 %raw 三个，临时变量是指变量名已下划线开头的变量
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
            keys = list(saved.keys())
            for key in keys:
                if key.startswith("_"):
                    saved.pop(key)
            saved.pop("%line", None)
            saved.pop("%raw", None)
            saved.pop("%copy", None)
            pickle.dump(saved, fp)
            self.info(Settings.gettext("msg_variables_saved", file))

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
        嵌入命令 #test / #show 的执行函数，触发器测试命令。类似于zmud的#show命令。
        该函数不应该在代码中直接调用。

        使用:
            - #test {some_text}: 测试服务器收到{some_text}时的触发器响应情况。此时，触发器不会真的响应。
            - #tt {some_test}: 与#test 的差异是，若存在匹配的触发器，无论其是否被使能，该触发器均会实际响应。

        示例:
            - ``#test 你深深吸了口气，站了起来。`` ： 模拟服务器收到“你深深吸了口气，站了起来。”时的情况进行触发测试（仅显示触发测试情况）
            - ``#test %copy``: 复制一句话，模拟服务器再次收到复制的这句内容时的情况进行触发器测试
            - ``#test 你深深吸了口气，站了起来。`` ： 模拟服务器收到“你深深吸了口气，站了起来。”时的情况进行触发测试（会实际导致触发器动作）

        注意:
            - #test命令测试触发器时，触发器不会真的响应。
            - #tt命令测试触发器时，触发器无论是否使能，均会真的响应。
        '''
        cmd = code.code[1].lower()
        docallback = False
        if cmd == "test":
            docallback = True

        new_cmd_text, new_code = code.expand(self, *args, **kwargs)
        line = new_cmd_text[6:]       # 取出#test 之后的所有内容

        if "\n" in line:
            lines = line.split("\n")
        else:
            lines = []
            lines.append(line)

        info_all = []
        info_enabled = []               # 组织好每一行显示的内容之后，统一输出，不逐行info
        info_disabled = []
        triggered = 0
        triggered_enabled = 0
        triggered_disabled = 0


        tris_enabled = [tri for tri in self._triggers.values() if isinstance(tri, Trigger) and tri.enabled]
        tris_enabled.sort(key = lambda tri: tri.priority)

        tris_disabled = [tri for tri in self._triggers.values() if isinstance(tri, Trigger) and not tri.enabled]
        tris_disabled.sort(key = lambda tri: tri.priority)
        
        for raw_line in lines:
            tri_line = self.getPlainText(raw_line)
            
            block = False
            for tri in tris_enabled:
                if tri.raw:
                    state = tri.match(raw_line, docallback = docallback)
                else:
                    state = tri.match(tri_line, docallback = docallback)

                if state.result == Trigger.SUCCESS:
                    triggered_enabled += 1
                    if not block: 
                        triggered += 1
                        info_enabled.append(Settings.gettext("msg_tri_triggered", tri.__detailed__()))
                        info_enabled.append(Settings.gettext("msg_tri_wildcards", state.wildcards))
                    
                        if not tri.keepEval:                # 非持续匹配的trigger，匹配成功后停止检测后续Trigger
                            info_enabled.append(Settings.gettext("msg_tri_prevent", Settings.WARN_STYLE, Settings.CLR_STYLE))
                            #info_enabled.append(f"      {Settings.WARN_STYLE}该触发器未开启keepEval, 会阻止后续触发器。{Settings.CLR_STYLE}")
                            block = True
                    else:
                        info_enabled.append(Settings.gettext("msg_tri_ignored", tri.__detailed__(), Settings.WARN_STYLE, Settings.CLR_STYLE))
                        # info_enabled.append(f"    {Settings.WARN_STYLE}{tri.__detailed__()} 可以触发，但由于优先级与keepEval设定，触发器不会触发。{Settings.CLR_STYLE}")
            
            
            for tri in tris_disabled:
                if tri.raw:
                    state = tri.match(raw_line, docallback = docallback)
                else:
                    state = tri.match(tri_line, docallback = docallback)

                if state.result == Trigger.SUCCESS:
                    triggered_disabled += 1
                    #info_disabled.append(f"    {tri.__detailed__()} 可以匹配触发。")
                    info_disabled.append(Settings.gettext("msg_tri_matched", tri.__detailed__()))

            if triggered_enabled + triggered_disabled == 0:
                info_all.append("")

        if triggered_enabled == 0:
            info_enabled.insert(0, Settings.gettext("msg_enabled_summary_0", Settings.INFO_STYLE))
            #info_enabled.insert(0, f"{Settings.INFO_STYLE}  使能的触发器中，没有可以触发的。")
        elif triggered < triggered_enabled:
            info_enabled.insert(0, Settings.gettext("msg_enabled_summary_1", Settings.INFO_STYLE, triggered_enabled, triggered, triggered_enabled - triggered))
            #info_enabled.insert(0, f"{Settings.INFO_STYLE}  使能的触发器中，共有 {triggered_enabled} 个可以触发，实际触发 {triggered} 个，另有 {triggered_enabled - triggered} 个由于 keepEval 原因实际不会触发。")
        else:
            info_enabled.insert(0, Settings.gettext("msg_enabled_summary_2", Settings.INFO_STYLE, triggered_enabled))
            #info_enabled.insert(0, f"{Settings.INFO_STYLE}  使能的触发器中，共有 {triggered_enabled} 个全部可以被正常触发。")

        if triggered_disabled > 0:
            info_disabled.insert(0, Settings.gettext("msg_disabled_summary_0", Settings.INFO_STYLE, triggered_disabled))
            #info_disabled.insert(0, f"{Settings.INFO_STYLE}  未使能的触发器中，共有 {triggered_disabled} 个可以匹配。")
        else:
            info_disabled.insert(0, Settings.gettext("msg_disabled_summary_1", Settings.INFO_STYLE))
            #info_disabled.insert(0, f"{Settings.INFO_STYLE}  未使能触发器，没有可以匹配的。")
        
        info_all.append("")
        if triggered_enabled + triggered_disabled == 0:
            #info_all.append(f"PYMUD 触发器测试: {'响应模式' if docallback else '测试模式'}")
            info_all.append(Settings.gettext("msg_test_summary_0", line))
            info_all.append(Settings.gettext("msg_test_summary_1"))
            #info_all.append(f"  测试内容: {line}")
            #info_all.append(f"  测试结果: 没有可以匹配的触发器。")
        else:
            #info_all.append(f"PYMUD 触发器测试: {'响应模式' if docallback else '测试模式'}")
            info_all.append(Settings.gettext("msg_test_summary_0", line))
            info_all.append(Settings.gettext("msg_test_summary_2", triggered, triggered_enabled + triggered_disabled))
            #info_all.append(f"  测试内容: {line}")
            #info_all.append(f"  测试结果: 有{triggered}个触发器可以被正常触发，一共有{triggered_enabled + triggered_disabled}个满足匹配触发要求。")
            info_all.extend(info_enabled)
            info_all.extend(info_disabled)
        
        title = Settings.gettext("msg_test_title", Settings.gettext("msg_triggered_mode") if docallback else Settings.gettext("msg_matched_mode"))
        #title = f"触发器测试 - {'响应模式' if docallback else '测试模式'}"
        self.info("\n".join(info_all), title)
        #self.info("PYMUD 触发器测试 完毕")

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
                self.info(Settings.gettext("msg_no_plugins"), "PLUGINS")
                #self.info("PYMUD当前并未加载任何插件。", "PLUGINS")
            else:
                self.info(Settings.gettext("msg_plugins_list", count), "PLUGINS")
                #self.info(f"PYMUD当前已加载 {count} 个插件，分别为：", "PLUGINS")
                for name, plugin in self.plugins.items():
                    self.info(Settings.gettext("msg_plugins_info", plugin.desc['DESCRIPTION'], plugin.desc['VERSION'], plugin.desc['AUTHOR'], plugin.desc['RELEASE_DATE']), f"PLUGIN {name}")
                    #self.info(f"{plugin.desc['DESCRIPTION']}, 版本 {plugin.desc['VERSION']} 作者 {plugin.desc['AUTHOR']} 发布日期 {plugin.desc['RELEASE_DATE']}", f"PLUGIN {name}")
        
        elif len(args) == 1:
            name = args[0]
            if name in self.plugins.keys():
                plugin = self.plugins[name]
                self.info(Settings.gettext("msg_plugins_info", plugin.desc['DESCRIPTION'], plugin.desc['VERSION'], plugin.desc['AUTHOR'], plugin.desc['RELEASE_DATE']), f"PLUGIN {name}")
                #self.info(f"{plugin.desc['DESCRIPTION']}, 版本 {plugin.desc['VERSION']} 作者 {plugin.desc['AUTHOR']} 发布日期 {plugin.desc['RELEASE_DATE']}", f"PLUGIN {name}")
                self.writetobuffer(plugin.help, True)

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
            self.error(Settings.gettext("msg_py_exception", e))

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
        self.warning(new_text[9:])

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
        self.error(new_text[7:])

    def info2(self, msg, title = None, style = Settings.INFO_STYLE):
        title = title or Settings.gettext("title_msg")
        msg = f"{msg}"

        self.writetobuffer("{}〔{}〕{}{}".format(style, title, msg, Settings.CLR_STYLE), newline = True)

    def info(self, msg, title = None, style = Settings.INFO_STYLE):
        """
        使用默认的INFO_STYLE（绿色）输出信息，并自动换行。信息格式类似 [title] msg
        
        :param msg: 要输出的信息
        :param title: 要显示在前面的标题，不指定时默认为 PYMUD INFO
        :param style: 要输出信息的格式(ANSI)， 默认为 INFO_STYLE, \x1b[32m
        """
        title = title or Settings.gettext("title_info")
        self.info2(msg, title, style)

    def warning(self, msg, title = None, style = Settings.WARN_STYLE):
        """
        使用默认的WARN_STYLE（黄色）输出信息，并自动换行。信息格式类似 [title] msg
        
        :param msg: 要输出的信息
        :param title: 要显示在前面的标题，不指定时默认为 PYMUD WARNING
        :param style: 要输出信息的格式(ANSI)， 默认为 WARN_STYLE, \x1b[33m
        """
        title = title or Settings.gettext("title_warning")
        self.info2(msg, title, style)

    def error(self, msg, title = None, style = Settings.ERR_STYLE):
        """
        使用默认的ERR_STYLE（红色）输出信息，并自动换行。信息格式类似 [title] msg
        
        :param msg: 要输出的信息
        :param title: 要显示在前面的标题，不指定时默认为 PYMUD ERROR
        :param style: 要输出信息的格式(ANSI)， 默认为 ERR_STYLE, \x1b[31m
        """
        title = title or Settings.gettext("title_error")
        self.info2(msg, title, style)

    def handle_log(self, code: CodeLine = None, *args, **kwargs):
        '''
        嵌入命令 #log 的执行函数，控制当前会话的记录状态。
        该函数不应该在代码中直接调用。

        使用:
            - #log : 显示所有记录器的状态情况
            - #log start [logger-name] [-a|-w|-n] [-r] : 启动一个记录器

                参数:
                    - :logger-name: 记录器名称。当不指定时，选择名称为会话名称的记录器（会话默认记录器）
                    - :-a|-w|-n: 记录器模式选择。 -a 为添加模式（未指定时默认值），在原记录文件后端添加； -w 为覆写模式，清空原记录文件并重新记录； -n 为新建模式，以名称和当前时间为参数，使用 name.now.log 形式创建新的记录文件
                    - :-r: 指定记录器是否使用 raw 模式

            - #log stop [logger-name] : 停止一个记录器
                
                参数:
                    - :logger-name: 记录器名称。当不指定时，选择名称为会话名称的记录器（会话默认记录器）

            - #log show [loggerFile]: 显示全部日志记录或指定记录文件

                参数:
                    - :loggerFile: 要显示的记录文件名称。当不指定时，弹出对话框列出当前目录下所有记录文件

        示例:
            - ``#log`` : 在当前会话窗口列出所有记录器状态
            - ``#log start`` : 启动本会话默认记录器（记录器名为会话名）。该记录器以纯文本模式，将后续所有屏幕输出、键盘键入、命令输入等记录到 log 目录下 name.log 文件的后端
            - ``#log start -r`` : 启动本会话默认记录器。该记录器以raw模式，将后续所有屏幕输出、键盘键入、命令输入等记录到 log 目录下 name.log 文件的后端
            - ``#log start chat`` : 启动名为 chat 的记录器。该记录器以纯文本模式，记录代码中调用过该记录器 .log 进行记录的信息
            - ``#log stop`` : 停止本会话默认记录器（记录器名为会话名）。

        注意:
            - 记录器文件模式（-a|-w|-n）在修改后，只有在下一次该记录器启动时才会生效
            - 记录器记录模式（-r）在修改后立即生效
        '''
        
        args = list()
        if isinstance(code, CodeLine):
            args = code.code[2:]

        if len(args) == 0:
            session_loggers = set(self._loggers.keys())
            app_loggers = set(self.application.loggers.keys()).difference(session_loggers)
            
            self.info(Settings.gettext("msg_log_title"))
            #self.info("本会话中的记录器情况:")
            for name in session_loggers:
                logger = self.application.loggers[name]
                self.info(f"{Settings.gettext('logger')} {logger.name}, {Settings.gettext('logger_status')}: {Settings.gettext('enabled') if logger.enabled else Settings.gettext('disabled')}, {Settings.gettext('file_mode')}: {logger.mode}, {Settings.gettext('logger_mode')}: {Settings.gettext('ANSI') if logger.raw else Settings.gettext('plain_text')}")
                #self.info(f"记录器 {logger.name}, 当前状态: {'开启' if logger.enabled else '关闭'}, 文件模式: {logger.mode}, 记录模式: {'ANSI' if logger.raw else '纯文本'}")

            if len(app_loggers) > 0:
                self.info(Settings.gettext("msg_log_title2"))
                #self.info("本应用其他会话中的记录器情况:")
                for name in app_loggers:
                    logger = self.application.loggers[name]
                    self.info(f"{Settings.gettext('logger')} {logger.name}, {Settings.gettext('logger_status')}: {Settings.gettext('enabled') if logger.enabled else Settings.gettext('disabled')}, {Settings.gettext('file_mode')}: {logger.mode}, {Settings.gettext('logger_mode')}: {Settings.gettext('ANSI') if logger.raw else Settings.gettext('plain_text')}")
                    #self.info(f"记录器 {logger.name}, 当前状态: {'开启' if logger.enabled else '关闭'}, 文件模式: {logger.mode}, 记录模式: {'ANSI' if logger.raw else '纯文本'}")

        else:
            name = self.name
            if len(args) > 1 and not args[1].startswith('-'):
                name = args[1]

            if (args[0] == "start"):
                if "-n" in args:
                    mode = "n"
                    #mode_name = '新建'
                    mode_name = Settings.gettext("filemode_new")
                elif "-w" in args:
                    mode = "w"
                    #mode_name = '覆写'
                    mode_name = Settings.gettext("filemode_overwrite")
                else:
                    mode = "a"
                    #mode_name = '追加'
                    mode_name = Settings.gettext("filemode_append")

                raw = True if "-r" in args else False
                #raw_name = '原始ANSI' if raw else '纯文本'
                raw_name = Settings.gettext("ANSI") if raw else Settings.gettext("plain_text")

                logger = self.getLogger(name = name, mode = mode, raw = raw)
                logger.enabled = True

                #self.info(f"{datetime.datetime.now()}: 记录器{name}以{mode_name}文件模式以及{raw_name}记录模式开启。")
                self.info(Settings.gettext("msg_logger_enabled", datetime.datetime.now(), name, mode_name, raw_name))

            elif (args[0] == "stop"):
                #self.info(f"{datetime.datetime.now()}: 记录器{name}记录已关闭。")
                self.info(Settings.gettext("msg_logger_disabled", datetime.datetime.now(), name))
                self.log.enabled = False

            elif (args[0] == "show"):
                if len(args) > 1 and not args[1].startswith('-'):
                    file = args[1]
                    if os.path.exists(file):
                        filepath = os.path.abspath(file)
                        #self.info(f'file {filepath} exists, will be shown.')
                        self.application.logFileShown = filepath
                        self.application.showLogInTab()
                    elif os.path.exists(os.path.join('./log', file)):
                        filepath = os.path.abspath(os.path.join('./log', file))
                        #self.info(f'file {filepath} exists, will be shown.')
                        self.application.logFileShown = filepath
                        self.application.showLogInTab()
                    else:
                        self.warning(Settings.gettext("msg_logfile_not_exists", file))
                    
                else:
                    self.application.show_logSelectDialog()

