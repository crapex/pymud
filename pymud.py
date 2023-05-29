import sys, logging, asyncio, math
from collections.abc import Iterable
from terminal import ConsoleTerminal
from session import Session

_INFO_STYLE     = "\x1b[32m"     #"\x1b[38;2;0;128;255m"
_WARN_STYLE     = "\x1b[33m"
_ERR_STYLE      = "\x1b[31m"
_CLR_STYLE      = "\x1b[0m"

class PyMud:
    """
    PyMUD: a MUD Client in Python.
    以Python语言实现的MUD客户端
    此类为pymud模块的核心主要类型, 主入口
    """
    __appname__   = "PYMUD"
    __appdesc__   = "a MUD client written in Python"
    __version__   = "0.04b"
    __release__   = "2023-5-29"
    __author__    = "北侠玩家 本牛(newstart)"
    __email__     = "crapex@crapex.cc"

    MSG_NO_SESSION = "当前没有正在运行的session, 可以使用#session {name} {host} {port} {encoding}创建一个."

    _commands = (
        "alias",        # 别名
        "command",      # 命令
        "timer",        # 定时器
        "exit",         # 结束PyMud应用
        "help",         # 帮助
        "session",      # 开启一个新会话
        "variable",     # 变量
        "trigger",      # 触发器
        "load",         # 加载配置文件
        "reload",       # 重新加载配置文件
        "info",         # 输出蓝色info
        "warning",      # 输出黄色warning
        "error",        # 输出红色error
    )

    def __init__(self, terminal_factory = ConsoleTerminal, encoding = "utf-8", encoding_errors = "ignore", loop = None) -> None:
        self.log = logging.getLogger("pymud.PyMud")         # 此模块的logger
        self.server_encoding = encoding                     # 服务器端编码字符集为 UTF8
        self.local_encoding = "utf-8"                       # 本地编码字符集为 UTF-8
        self.encoding_errors = encoding_errors              # 字符集转换出错时，默认 ignore
        
        self.loop = loop if isinstance(loop, asyncio.AbstractEventLoop) else asyncio.get_event_loop()
        
        self.newline = "\n"
        
        # 默认绑定的终端
        self.terminal = terminal_factory(encoding = self.local_encoding, 
                                         encoding_errors = self.encoding_errors, 
                                         newline = self.newline, 
                                         loop = self.loop)                

        self._cmds_handler = dict()                         # 支持的命令的处理函数字典
        for cmd in PyMud._commands:
            handler = getattr(self, f"handle_{cmd}", None)
            self._cmds_handler[cmd] = handler

        self._tasks = []
        self._sessions = {}
        self.current_session = None

        self._localreader_end_future = self.loop.create_future()

        self._print_welcome_screen()

    def activate_session(self, session: Session):
        "激活指定session，并将该session设置为当前session"
        self.current_session = session.activate()
   
    def remove_session(self, session: Session):
        "移除会话, 若移除的为当前会话，则将清单中第一个会话设置为当前会话"
        if session.name in self._sessions.keys():
            self._sessions.pop(session.name)

        if len(self._sessions.keys()) > 0:
            if self.current_session == session:
                self.current_session = self._sessions.get(next(iter(self._sessions)))
        else:
            self.current_session = None

    def handle_session(self, *args):
        "\x1b[1m命令\x1b[0m: #session {名称} {宿主机} {端口} {编码}\n" \
        "      创建一个远程连接会话，使用指定编码格式连接到远程宿主机的指定端口并保存为 {名称} \n" \
        "      如， #session newstart mud.pkuxkx.net 8080 GBK \n" \
        "      当不指定编码格式时, 默认使用utf-8编码 \n" \
        "      如， #session newstart mud.pkuxkx.net 8081 \n" \
        "      当不指定参数时，列出所有可用的会话 \n" \
        "\x1b[1m相关\x1b[0m: help, exit"

        nothandle = True
        if len(args) == 0:
            # List all sessions.
            if len(self._sessions.keys()) == 0:
                self.terminal.writeline("当前没有正在运行的session.")
            else:
                self.terminal.writeline("当前运行session清单如下:")
                for name in self._sessions.keys():
                    if self.current_session.name == name:
                        self.terminal.writeline(f"  + {name} [活动的]")
                    else:
                        self.terminal.writeline(f"  + {name}")

            nothandle = False
        elif len(args) == 1:
            # TODO: change session
            if args[0] == "close":
                if self.current_session:
                    self.current_session.close()
                    self.current_session = None
                    self.terminal.writeline(f"当前会话已关闭")

        elif len(args) >= 3:
            session_name = args[0]
            session_host = args[1]
            session_port = int(args[2])
            if len(args) == 4:
                session_encoding = args[3]
            else:
                session_encoding = self.server_encoding

            if session_name not in self._sessions.keys():
                self.info("尝试建立连接到 %s:%d ..." % (session_host, session_port))
                session = Session(self, 
                                  session_name, 
                                  session_host, 
                                  session_port, 
                                  self.terminal,
                                  session_encoding, 
                                  self.encoding_errors, 
                                  self.terminal.getwidth(), 
                                  self.terminal.getheight()
                                  )
                self._sessions[session_name] = session
                nothandle = False
            else:
                self.terminal.writeline(f"已存在一个名为{session_name}的session，请更换名称再试.")
        
        if nothandle:
            self.terminal.writeline("错误的#session命令，请使用#help session查询用法")

    def handle_help(self, *args):
        "\x1b[1m命令\x1b[0m: #help {主题}\n" \
        "      当不带参数时, #help会列出所有可用的帮助主题\n" \
        "\x1b[1m相关\x1b[0m: session, exit"

        if len(args) == 0:      # 不带参数，打印所有支持的help主题
            self._print_all_help()
        elif len(args) >= 1:    # 大于1个参数，第1个为 topic， 其余参数丢弃
            topic = args[0]
            if topic in PyMud._commands:
                docstring = self._cmds_handler[topic].__doc__
            else:
                docstring = f"未找到主题{topic}, 请确认输入是否正确."
            
            self.terminal.writeline(docstring)
    
    def handle_exit(self, *args):
        "\x1b[1m命令\x1b[0m: #exit \n" \
        "      退出PYMUD程序\n" \
        "\x1b[1m相关\x1b[0m: session"
    
    def handle_variable(self, *args):
        "\x1b[1m命令\x1b[0m: #variable\n" \
        "      列出当前会话中所有的变量清单\n" \
        "\x1b[1m相关\x1b[0m: alias, trigger, command"

        if self.current_session:
            vars = self.current_session._variables
            vars_simple = {}
            vars_complex = {}
            for k, v in vars.items():
                if isinstance(v, Iterable) and not isinstance(v, str):
                    vars_complex[k] = v
                else:
                    vars_simple[k] = v


            width = self.terminal.getwidth()
            
            title = f"  VARIABLE LIST IN SESSION {self.current_session.name}  "
            left = (width - len(title)) // 2
            right = width - len(title) - left
            self.terminal.writeline("="*left + title + "="*right)
            
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
                self.terminal.write(" " * left_space)
                line_vars = var_keys[start:end]
                for var in line_vars:
                    self.terminal.write("{0:>18} = {1:<19}".format(var, vars_simple[var].__repr__()))

                self.terminal.writeline("")

            # print vars in complex, 每个变量占1行
            for k, v in vars_complex.items():
                self.terminal.write(" " * left_space)
                self.terminal.writeline("{0:>18} = {1}".format(k, v.__repr__()))

            self.terminal.writeline("="*width)
        else:
            self.info(self.MSG_NO_SESSION)

    def _handle_objs(self, name: str, objs: dict, *args):
        if len(args) == 0:
            width = self.terminal.getwidth()
            
            title = f"  {name.upper()} LIST IN SESSION {self.current_session.name}  "
            left = (width - len(title)) // 2
            right = width - len(title) - left
            self.terminal.writeline("="*left + title + "="*right)

            for id in sorted(objs.keys()):
                self.terminal.writeline("  %r" % objs[id])

            self.terminal.writeline("="*width)

        elif len(args) == 1:
            if args[0] in objs.keys():
                obj = objs[args[0]]
                self.info(obj.__detailed__())
            else:
                self.warning(f"当前session中不存在key为 {args[0]} 的 {name}, 请确认后重试.")

        elif len(args) == 2:
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
            else:
                self.warning(f"当前session中不存在key为 {args[0]} 的 {name}, 请确认后重试.")

    def handle_alias(self, *args):
        "\x1b[1m命令\x1b[0m: #alias\n" \
        "      不指定参数时, 列出当前会话中所有的别名清单\n" \
        "      为一个参数时, 该参数应为某个Alias的id, 可列出Alias的详细信息\n" \
        "      为一个参数时, 第一个参数应为Alias的id, 第二个应为on/off, 可修改Alias的使能状态\n" \
        "\x1b[1m相关\x1b[0m: variable, trigger, command, timer"

        if self.current_session:
            self._handle_objs("Alias", self.current_session._aliases, *args)
        else:
            self.info(self.MSG_NO_SESSION)

    def handle_timer(self, *args):
        "\x1b[1m命令\x1b[0m: #timer\n" \
        "      不指定参数时, 列出当前会话中所有的定时器清单\n" \
        "      为一个参数时, 该参数应为某个Timer的id, 可列出Timer的详细信息\n" \
        "      为一个参数时, 第一个参数应为Timer的id, 第二个应为on/off, 可修改Timer的使能状态\n" \
        "\x1b[1m相关\x1b[0m: variable, alias, trigger, command"

        if self.current_session:         
            self._handle_objs("Timer", self.current_session._timers, *args)
        else:
            self.warning(self.MSG_NO_SESSION)

    def handle_command(self, *args):
        "\x1b[1m命令\x1b[0m: #command\n" \
        "      不指定参数时, 列出当前会话中所有的命令清单\n" \
        "      为一个参数时, 该参数应为某个Command的id, 可列出Command的详细信息\n" \
        "      为一个参数时, 第一个参数应为Command的id, 第二个应为on/off, 可修改Command的使能状态\n" \
        "\x1b[1m相关\x1b[0m: alias, variable, trigger, timer"

        if self.current_session:
            self._handle_objs("Command", self.current_session._commands, *args)
        else:
            self.info(self.MSG_NO_SESSION)

    def handle_trigger(self, *args):
        "\x1b[1m命令\x1b[0m: #trigger\n" \
        "      不指定参数时, 列出当前会话中所有的触发器清单\n" \
        "      为一个参数时, 该参数应为某个Trigger的id, 可列出Trigger的详细信息\n" \
        "      为一个参数时, 第一个参数应为Trigger的id, 第二个应为on/off, 可修改Trigger的使能状态\n" \
        "\x1b[1m相关\x1b[0m: alias, variable, command, timer"
                
        if self.current_session:
            self._handle_objs("Trigger", self.current_session._triggers, *args)
        else:
            self.info(self.MSG_NO_SESSION)

    def handle_load(self, *args):
        "\x1b[1m命令\x1b[0m: #load {config}\n" \
        "      为当前session加载{config}指定的模块\n" \
        "\x1b[1m相关\x1b[0m: reload"

        if self.current_session:
            self.current_session.loadconfig(args[0])
        else:
            self.info(self.MSG_NO_SESSION)

    def handle_reload(self, *args):
        "\x1b[1m命令\x1b[0m: #reload\n" \
        "      为当前session重新加载配置模块（解决配置模块文件修改后的重启问题）\n" \
        "\x1b[1m相关\x1b[0m: load"

        if self.current_session:
            self.current_session.reload()
        else:
            self.info(self.MSG_NO_SESSION)

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

    def _print_welcome_screen(self):
        """打印欢迎屏幕"""
        width = self.terminal.getwidth()
        if width >= 80:
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#" * 80 + _CLR_STYLE)
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#" + " " * 78 + "#" + _CLR_STYLE)
            intro = f"{self.__appname__} - {self.__appdesc__}"
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#\x1b[0m" + f"{intro:^78}" + _INFO_STYLE + "#" + _CLR_STYLE)
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#" + " " * 78 + "#" + _CLR_STYLE)
            version = f"version: {self.__version__}   Release date: {self.__release__}"
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#\x1b[0m" + f"{version:^78}" + _INFO_STYLE + "#" + _CLR_STYLE)
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#" + " " * 78 + "#" + _CLR_STYLE)
            author = f"本程序由 {self.__author__} 开发, E-mail: {self.__email__}"
            align = 78 - (len(author.encode()) - len(author)) // 2 
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#\x1b[0m" + author.center(align, " ") + _INFO_STYLE + "#" + _CLR_STYLE)
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#" + " " * 78 + "#" + _CLR_STYLE)
            self.terminal.writeline(_INFO_STYLE + " " * 6 + "#" * 80 + _CLR_STYLE)
        else:
            self.terminal.writeline(f"program: {self.__appname__} - {self.__version__}")
            self.terminal.writeline(f"release: {self.__release__}")
            self.terminal.writeline(f" author: {self.__author__}")
            self.terminal.writeline(f"  email: {self.__email__}")

    def _print_all_help(self):
        """打印所有可用的help主题, 并根据终端尺寸进行排版"""
        width = self.terminal.getwidth()
        cmd_count = len(self._commands)
        left = (width - 9) // 2
        right = width - 9 - left
        self.terminal.writeline("#"*left + "  #HELP  " + "#"*right)
        cmd_per_line = (width - 2) // 20
        lines = math.ceil(cmd_count / cmd_per_line)
        left_space = (width - cmd_per_line * 20) // 2
        cmds = sorted(self._commands)
        for idx in range(0, lines):
            start = idx * cmd_per_line
            end   = (idx + 1) * cmd_per_line
            if end > cmd_count: end = cmd_count
            line_cmds = cmds[start:end]
            self.terminal.write(" " * left_space)
            for cmd in line_cmds:
                self.terminal.write(f"{cmd.upper():<20}")

            self.terminal.writeline("")

        self.terminal.writeline("#"*width)

    async def _local_reader_task(self):
        while True:
            cmd_line_raw = await self.terminal.readline()
            cmd_line = cmd_line_raw.lower().rstrip(self.newline)
            if cmd_line == "#exit":
                break
            elif len(cmd_line) > 0: 
                if cmd_line[0] == "#":
                    cmd_line = cmd_line[1:]
                    cmd_tuple = cmd_line.split()
                    handler = self._cmds_handler.get(cmd_tuple[0], None)
                    if handler and callable(handler):
                        handler(*cmd_tuple[1:])
                    else:
                        self.info("未识别的命令: %s" % cmd_line)
                else:
                    if self.current_session:
                        self.current_session.exec_command(cmd_line)
                        #    self.current_session.writeline(cmd_line)  
                    else:
                        self.info("当前没有正在运行的session, 请使用#session {name} {host} {port} {encoding}创建一个.")
            elif len(cmd_line) == 0: 
                if self.current_session:
                    self.current_session.writeline("")
        
        self._localreader_end_future.set_result(True)
    
    def info2(self, msg, title = "PYMUD INFO", style = _INFO_STYLE):
        self.terminal.writeline(style + "[{}] {}".format(title, msg) + _CLR_STYLE)

    def info(self, msg, title = "PYMUD INFO", style = _INFO_STYLE):
        "输出信息（蓝色），自动换行"
        #self.terminal.writeline(_INFO_STYLE + "[PYMUD INFO] {0}".format(msg) + _CLR_STYLE)
        self.info2(msg, title, style)

    def warning(self, msg, title = "PYMUD WARNING", style = _WARN_STYLE):
        "输出警告（黄色），自动换行"
        #self.terminal.writeline(_INFO_STYLE + "[PYMUD INFO] {0}".format(msg) + _CLR_STYLE)
        #self.terminal.writeline(_WARN_STYLE + "[PYMUD WARNING] {0}".format(msg) + _CLR_STYLE)
        self.info2(msg, title, style)

    def error(self, msg, title = "PYMUD ERROR", style = _ERR_STYLE):
        "输出错误（红色），自动换行"
        #self.terminal.writeline(_ERR_STYLE + "[PYMUD ERROR] {0}".format(msg) + _CLR_STYLE)
        self.info2(msg, title, style)
        
    def tell(self, msg):
        "输出信息，不换行"
        self.terminal.write(msg)
    
    def colorTell(self, fgColor, bgColor, msg):
        "带颜色输出信息，不换行，暂未实现"
        from reader import CSI, CSI_END, ANSI_COLOR
        s = f"{CSI}{str(fgColor)}{CSI_END}{CSI}{str(bgColor)}{CSI_END}{msg}{CSI}{str(ANSI_COLOR.Reset)}{CSI_END}"
        self.terminal.write(s)

    def finalize(self):
        """清理操作"""
        # 1. 清空所有弱引用的task
        self._tasks.clear()
        
        # 2. 关闭所有session
        for session in tuple(self._sessions.values()):
            session.close()

    def run_untile_exit(self):
        task = self.loop.create_task(self._local_reader_task(), name = "localread")
        self._tasks.append(task)
        # 以用户结束命令输入作为程序终止点
        self.loop.run_until_complete(self._localreader_end_future)
        self.finalize()
        self.info("感谢使用PYMUD, 期待下次再见 :)")
        self.loop.run_until_complete(self.terminal.drain())
        self.loop.close()

        return 0

if __name__ == "__main__":

    # 以此文件为入口时，main函数执行如下：
    # 所有级别log都存入文件
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename='myapp.log',
                        filemode='a')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    # 高于loglevel的在控制台打印
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    loop = asyncio.get_event_loop()
    pymud = PyMud(loop = loop)
    sys.exit(pymud.run_untile_exit())
