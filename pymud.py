import asyncio, functools, re 
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit import HTML
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Float, VSplit, HSplit, Window, WindowAlign
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension, D
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import  MenuItem, TextArea, SystemToolbar, Frame
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.key_binding import KeyPress, KeyPressEvent
from prompt_toolkit.keys import Keys

from prompt_toolkit.filters import (
    Condition,
    is_true,
)

from prompt_toolkit.layout.processors import (
    DisplayMultipleCursors,
    HighlightIncrementalSearchProcessor,
    HighlightSearchProcessor,
    HighlightSelectionProcessor,
    Processor,
    TransformationInput,
    merge_processors,
)
from prompt_toolkit.layout.margins import (
    ConditionalMargin,
    NumberedMargin,
    ScrollbarMargin,
)
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from objects import CodeBlock
from extras import MudFormatProcessor, SessionBuffer, EasternMenuContainer, VSplitWindow, SessionBufferControl
from session import Session
from settings import Settings
from dialogs import MessageDialog, WelcomeDialog, QueryDialog, NewSessionDialog

class PyMudApp:
    def __init__(self) -> None:
        self.sessions = {}
        self.current_session = None

        self.keybindings = KeyBindings()
        self.keybindings.add(Keys.PageUp, is_global = True)(self.page_up)
        self.keybindings.add(Keys.PageDown, is_global = True)(self.page_down)
        self.keybindings.add(Keys.ControlZ, is_global = True)(self.hide_history)
        self.keybindings.add(Keys.ControlC, is_global = True)(self.copy_selection)      # Control-C 复制文本
        self.keybindings.add(Keys.ControlR, is_global = True)(self.copy_selection)      # Control-R 复制带有ANSI标记的文本（适用于整行复制）
        self.keybindings.add(Keys.Right, is_global = True)(self.complete_autosuggest)   # 右箭头补完建议
        self.keybindings.add(Keys.Backspace)(self.delete_selection)
        self.keybindings.add(Keys.ControlLeft, is_global = True)(self.change_session)   # Control-左右箭头切换当前会话
        self.keybindings.add(Keys.ControlRight, is_global = True)(self.change_session)

        self.initUI()

        # 对剪贴板进行处理，经测试，android下的termux中，pyperclip无法使用，因此要使用默认的InMemoryClipboard
        clipboard = None
        try:
            clipboard = PyperclipClipboard()
            clipboard.set_text("test pyperclip")
        except:
            clipboard = None

        self.app = Application(
            layout = Layout(self.root_container, focused_element=self.commandLine),
            enable_page_navigation_bindings=True,
            style=self.style,
            mouse_support=True,
            full_screen=True,
            color_depth=ColorDepth.TRUE_COLOR,
            clipboard=clipboard,
            key_bindings=self.keybindings,
            cursor=CursorShape.BLINKING_UNDERLINE
        )

        self.set_status(Settings.text["welcome"])

    def initUI(self):
        self.style = Style.from_dict(Settings.styles)
        self.status_message = ""
        self.showHistory = False
        self.wrap_lines  = True

        self.commandLine = TextArea(
            prompt=self.get_input_prompt, 
            multiline = False, 
            accept_handler = self.enter_pressed, 
            height=D(min=1), 
            auto_suggest = AutoSuggestFromHistory(), 
            focus_on_click=True,
            name = "input",
            )

        self.status_bar = VSplit(
            [
                Window(FormattedTextControl(self.get_statusbar_text), style="class:status", align = WindowAlign.LEFT),
                Window(FormattedTextControl(self.get_statusbar_right_text), style="class:status.right", width = D(preferred=40), align = WindowAlign.RIGHT),
            ],
            height = 1,
            style ="class:status"
            )

        self.consoleView = SessionBufferControl(
            buffer = None,
            input_processors=[
                MudFormatProcessor(),
                HighlightSearchProcessor(),
                HighlightSelectionProcessor(),
                DisplayMultipleCursors(),
                ],
            focus_on_click = False,
            )
        

        self.console = VSplitWindow(
            content = self.consoleView,
            width = D(preferred = Settings.client["naws_width"]),
            height = D(preferred = Settings.client["naws_height"]),
            wrap_lines=Condition(lambda: is_true(self.wrap_lines)),
            right_margins=[ScrollbarMargin(True)],   
            style="class:text-area"
            )

        self.console_frame = Frame(body = self.console, title = self.get_frame_title)

        self.body = HSplit([
                self.console_frame,
                self.commandLine,
                self.status_bar
            ])

        self.root_container = EasternMenuContainer(
            body = self.body,
            menu_items=[
                MenuItem(
                    Settings.text["world"],
                    children=self.create_world_menus(),
                ),
                MenuItem(
                    Settings.text["session"],
                    children=[
                        MenuItem(Settings.text["connect"], handler = self.act_connect),
                        MenuItem(Settings.text["disconnect"], handler = self.act_discon),
                        MenuItem(Settings.text["closesession"], handler = self.act_close_session),
                        MenuItem("-", disabled=True),
                        MenuItem(Settings.text["nosplit"], handler = self.act_nosplit),
                        MenuItem(Settings.text["copy"], handler = self.act_copy),
                        MenuItem(Settings.text["copyraw"], handler = self.act_copyraw),
                        MenuItem("-", disabled=True),
                        MenuItem(Settings.text["reloadconfig"], handler = self.act_reload),
                    ]
                ),
                MenuItem(
                    Settings.text["help"],
                    children=[
                        MenuItem(Settings.text["about"], handler = self.act_about)
                    ]
                )
            ],
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1)
                )
            ],
        )

    def create_world_menus(self) -> list[MenuItem]:
        "创建世界子菜单"
        menus = []
        menus.append(MenuItem(Settings.text["new_session"], handler = self.act_new))
        menus.append(MenuItem("-", disabled=True))

        ss = Settings.sessions
        for key, site in ss.items():
            host = site["host"]
            port = site["port"]
            encoding = site["encoding"]
            autologin = site["autologin"]
            script = site["default_script"]
            menu = MenuItem(key)
            for name, info in site["chars"].items():
                after_connect = autologin.format(*info)
                sub = MenuItem(name, handler = functools.partial(self.create_session, name, host, port, encoding, after_connect, script))
                menu.children.append(sub)
            menus.append(menu)

        menus.append(MenuItem("-", disabled=True))
        menus.append(MenuItem(Settings.text["exit"], handler=self.act_exit))

        return menus

    def scroll(self, lines = 1):
        "内容滚动指定行数，小于0为向上滚动，大于0为向下滚动"
        if self.current_session:
            s = self.current_session
            b = s.buffer
            if lines < 0:
                b.cursor_up(-1 * lines)
            elif lines > 0:
                b.cursor_down(lines)

    def page_up(self, event: KeyPressEvent) -> None:
        lines = (self.app.output.get_size().rows - 5) // 2 - 1
        self.scroll(-1 * lines)

    def page_down(self, event: KeyPressEvent) -> None:
        lines = (self.app.output.get_size().rows - 5) // 2 - 1
        self.scroll(lines)

    def hide_history(self, event: KeyPressEvent) -> None:
        """关闭历史行显示"""
        self.act_nosplit()

    def copy_selection(self, event: KeyPressEvent)-> None:
        if event.key_sequence[-1].key == Keys.ControlC:
            self.copy()
        elif event.key_sequence[-1].key == Keys.ControlR:
            self.copy(raw = True)

    def delete_selection(self, event: KeyPressEvent):
        b = event.current_buffer
        if b.selection_state:
            event.key_processor.feed(KeyPress(Keys.Delete), first=True)
        else:
            b.delete_before_cursor(1)

    def complete_autosuggest(self, event: KeyPressEvent):
        """自动完成建议"""
        b = event.current_buffer
        s = b.auto_suggest.get_suggestion(b, b.document)
        if s:
            b.insert_text(s.text, fire_event=False)
        else:
            b.cursor_right()

    def change_session(self, event: KeyPressEvent):
        if self.current_session:
            current = self.current_session.name
            keys = list(self.sessions.keys())
            idx = keys.index(current)
            count = len(keys)

            if event.key_sequence[-1].key == Keys.ControlRight:
                if idx < count - 1:
                    new_key = keys[idx+1]
                    self.activate_session(new_key)

            elif event.key_sequence[-1].key == Keys.ControlLeft:
                if idx > 0:
                    new_key = keys[idx-1]
                    self.activate_session(new_key)

    def copy(self, raw = False):
        b = self.consoleView.buffer
        if b.selection_state:
            if not raw:
                # Control-C 复制纯文本
                line_start = b.document.translate_row_col_to_index(b.document.cursor_position_row, 0)
                line = b.document.current_line
                start = max(0, b.selection_state.original_cursor_position - line_start)
                end = min(b.cursor_position - line_start, len(line))
                line_plain = re.sub("\x1b\\[[^mz]+[mz]", "", line).replace("\r", "").replace("\x00", "")
                selection = line_plain[start:end]
                self.app.clipboard.set_text(selection)
                self.set_status("已复制：{}".format(selection))

            else:
                # Control-R 复制带有ANSI标记的原始内容（对应字符关系会不正确，因此需要整行复制-双击时才使用）
                data = self.consoleView.buffer.copy_selection()
                self.app.clipboard.set_data(data)
                self.set_status("已复制：{}".format(data.text))
        else:
            self.set_status("未选中任何内容...")

    def create_session(self, name, host, port, encoding = None, after_connect = None, script = None):
        result = False
        encoding = encoding or Settings.server["default_encoding"]

        if name not in self.sessions.keys():
            session = Session(self, name, host, port, encoding, after_connect, script = script)
            self.sessions[name] = session
            self.activate_session(name)

            result = True
        else:
            self.set_status(f"错误！已存在一个名为{name}的会话，请更换名称再试.")

        return result

    def activate_session(self, key):
        "激活指定名称的session，并将该session设置为当前session"
        session = self.sessions.get(key, None)

        if isinstance(session, Session):
            self.current_session = session
            self.consoleView.buffer = session.buffer
            self.set_status(Settings.text["session_changed"].format(session.name))
            self.app.invalidate()

    def close_session(self):
        "关闭当前会话"
        async def coroutine():
            if self.current_session:
                if self.current_session.connected:
                    dlgQuery = QueryDialog(HTML('<b fg="#aaaa00">警告</b>'), HTML('<style fg="#aaaa00">当前会话 {0} 还处于连接状态，确认要关闭？</style>'.format(self.current_session.name)))
                    result = await self.show_dialog_as_float(dlgQuery)
                    if result:
                        self.current_session.disconnect()
                    else:
                        return

                name = self.current_session.name
                self.current_session = None
                self.consoleView.buffer = SessionBuffer()
                self.sessions.pop(name)
                self.set_status(f"会话 {name} 已关闭")
                if len(self.sessions.keys()) > 0:
                    new_sess = list(self.sessions.keys())[0]
                    self.activate_session(new_sess)
                    self.set_status(f"当前会话已切换为 {self.current_session.name}")

        asyncio.ensure_future(coroutine())

    # 菜单选项操作 - 开始

    def act_new(self):
        async def coroutine():
            dlgNew = NewSessionDialog()
            result = await self.show_dialog_as_float(dlgNew)
            if result:
                self.create_session(*result)
            return result
        
        asyncio.ensure_future(coroutine())

    def act_connect(self):
        if self.current_session:
            self.current_session.handle_connect()

    def act_discon(self):
        if self.current_session:
            self.current_session.disconnect()

    def act_nosplit(self):
        if self.current_session:
            s = self.current_session
            b = s.buffer
            b.exit_selection()
            b.cursor_position = len(b.text)

    def act_close_session(self):
        self.close_session()

    def act_copy(self):
        "复制菜单"
        self.copy()

    def act_copyraw(self):
        "复制ANSI菜单"
        self.copy(raw = True)

    def act_reload(self):
        "重新加载配置文件菜单"
        if self.current_session:
            self.current_session.handle_reload()

    def act_exit(self):
        "退出菜单"
        async def coroutine():
            for session in self.sessions.values():
                if session.connected:
                    dlgQuery = QueryDialog(HTML('<b fg="yellow">程序退出警告</b>'), HTML('<style fg="yellow">会话 {0} 还处于连接状态，确认要关闭？</style>'.format(self.current_session.name)))
                    result = await self.show_dialog_as_float(dlgQuery)
                    if result:
                        session.disconnect()
                    else:
                        return
                
            self.app.exit()

        asyncio.ensure_future(coroutine())

    def act_about(self):
        "关于菜单"
        dialog_about = WelcomeDialog(True)
        self.show_dialog(dialog_about)

    # 菜单选项操作 - 完成

    def get_input_prompt(self):
        return HTML(Settings.text["input_prompt"])

    def btn_title_clicked(self, name, mouse_event: MouseEvent):
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.activate_session(name)

    def get_frame_title(self):
        if len(self.sessions.keys()) == 0:
            return Settings.__appname__ + " " + Settings.__version__
        
        title_formatted_list = []
        for key, session in self.sessions.items():
            if session == self.current_session:
                if session.connected:
                    style = Settings.styles["selected.connected"]
                else:
                    style = Settings.styles["selected"]

            else:
                if session.connected:
                    style = Settings.styles["normal.connected"]
                else:
                    style = Settings.styles["normal"]

            title_formatted_list.append((style, key, functools.partial(self.btn_title_clicked, key)))
            title_formatted_list.append(("", " | "))

        return title_formatted_list[:-1]

    def get_statusbar_text(self):
        return [
            ("class:status", " "),
            ("class:status", self.status_message),
        ]
    
    def get_statusbar_right_text(self):
        con_str = ""
        if self.current_session:
            if not self.current_session.connected:
                con_str = "未连接"
            else:
                dura = self.current_session.duration
                DAY, HOUR, MINUTE = 86400, 3600, 60
                days, hours, mins, secs = 0,0,0,0
                days = dura // DAY
                dura = dura - days * DAY
                hours = dura // HOUR
                dura = dura - hours * HOUR
                mins = dura // MINUTE
                sec = dura - mins * MINUTE

                if days > 0:
                    con_str = "已连接：{:.0f}天{:.0f}小时{:.0f}分{:.0f}秒".format(days, hours, mins, sec)
                elif hours > 0:
                    con_str = "已连接：{:.0f}小时{:.0f}分{:.0f}秒".format(hours, mins, sec)
                elif mins > 0:
                    con_str = "已连接：{:.0f}分{:.0f}秒".format(mins, sec)
                else:
                    con_str = "已连接：{:.0f}秒".format(sec)

        return "{} {} {} ".format(con_str, Settings.__appname__, Settings.__version__)

    def set_status(self, msg):
        self.status_message = msg
        self.app.invalidate()

    def handle_session(self, *args):
        "\x1b[1m命令\x1b[0m: #session {名称} {宿主机} {端口} {编码}\n" \
        "      创建一个远程连接会话，使用指定编码格式连接到远程宿主机的指定端口并保存为 {名称} \n" \
        "      如， #session newstart mud.pkuxkx.net 8080 GBK \n" \
        "      当不指定编码格式时, 默认使用utf-8编码 \n" \
        "      如， #session newstart mud.pkuxkx.net 8081 \n" \
        "      可以直接使用#{名称}将指定会话切换为当前会话，如#newstart \n" \
        "\x1b[1m相关\x1b[0m: help, exit"

        nothandle = True

        if len(args) >= 3:
            session_name = args[0]
            session_host = args[1]
            session_port = int(args[2])
            if len(args) == 4:
                session_encoding = args[3]
            else:
                session_encoding = Settings.server["default_encoding"]

            self.create_session(session_name, session_host, session_port, session_encoding)
            nothandle = False
        
        if nothandle:
            self.set_status("错误的#session命令")

    def handle_help(self, *args):
        "\x1b[1m命令\x1b[0m: #help {主题}\n" \
        "      当不带参数时, #help会列出所有可用的帮助主题\n" \
        "\x1b[1m相关\x1b[0m: session, exit"

        # if len(args) == 0:      # 不带参数，打印所有支持的help主题
        #     self._print_all_help()
        # elif len(args) >= 1:    # 大于1个参数，第1个为 topic， 其余参数丢弃
        #     topic = args[0]
        #     if topic in PyMud._commands_alias.keys():
        #         command = PyMud._commands_alias[topic]
        #         docstring = self._cmds_handler[command].__doc__
        #     elif topic in PyMud._commands:
        #         docstring = self._cmds_handler[topic].__doc__
        #     else:
        #         docstring = f"未找到主题{topic}, 请确认输入是否正确."
            
        #     self.terminal.writeline(docstring)
    
    def handle_exit(self, *args):
        "\x1b[1m命令\x1b[0m: #exit \n" \
        "      退出PYMUD程序\n" \
        "\x1b[1m相关\x1b[0m: session"
    
    def enter_pressed(self, buffer: Buffer):
        cmd_line = buffer.text
        
        if len(cmd_line) == 0:
            if self.current_session:
                self.current_session.writeline("")

        if cmd_line == "#exit":
            self.act_exit()

        elif cmd_line == "#close":
            self.close_session()

        elif cmd_line.startswith("#session"):
            cmd_tuple = cmd_line[1:].split()
            self.handle_session(*cmd_tuple[1:])

        elif cmd_line == "#help":
            self.act_about()

        elif cmd_line[1:] in self.sessions.keys():
            self.activate_session(cmd_line[1:])

        else:
            if self.current_session:
                if len(cmd_line) == 0:
                    self.current_session.writeline("")
                else:
                    cb = CodeBlock(self.current_session, cmd_line)
                    cb.execute()
            else:
                self.set_status("当前没有正在运行的session.")

        # if len(cmd_line) == 0:
        #     # 直接回车时，向当前session发送空字节（仅回车键）
        #     if self.current_session:
        #         self.current_session.writeline("")

        # elif (cmd_line[0] == "#") and (len(cmd_line) > 1):
        #     # 当命令由#开头时，exit, session, help三个命令，以及活动session切换由APP处理，其余发送到session进行处理
        #     cmd_tuple = cmd_line[1:].split()
        #     cmd = cmd_tuple[0]

        #     if cmd == "exit":
        #         # TODO 增加活动session判断
        #         self.act_exit()
            
        #     elif cmd in self.sessions.keys():
        #         self.activate_session(cmd)

        #     elif cmd == "session":
        #         self.handle_session(*cmd_tuple[1:])

        #     elif cmd == "close":
        #         self.close_session()


        #     elif cmd == "help":
        #         self.handle_help(*cmd_tuple[1:])

        #     else:
        #         # #xxx 发送到session进行处理
        #         if self.current_session:
        #             self.current_session.handle_input(*cmd_tuple)
        #         else:
        #             self.set_status("当前没有正在运行的session, 请使用#session {name} {host} {port} {encoding}创建一个.")

        # else:
        #     # #xxx 发送到session进行处理
        #     if self.current_session:
        #         self.current_session.exec_command(cmd_line)
        #     else:
        #         self.set_status("当前没有正在运行的session, 请使用#session {name} {host} {port} {encoding}创建一个.")

        # 配置：命令行内容保留
        if Settings.client["remain_last_input"]:
            buffer.cursor_position = 0
            buffer.start_selection()
            buffer.cursor_right(len(cmd_line))
            return True
        
        else:
            return False

    def show_message(self, title, text, modal = True):
        "显示一个消息对话框"
        async def coroutine():
            dialog = MessageDialog(title, text, modal)
            await self.show_dialog_as_float(dialog)

        asyncio.ensure_future(coroutine())

    def show_dialog(self, dialog):
        "显示一个给定的对话框"
        async def coroutine():
            await self.show_dialog_as_float(dialog)

        asyncio.ensure_future(coroutine())

    async def show_dialog_as_float(self, dialog):
        "显示弹出式窗口."
        float_ = Float(content=dialog)
        self.root_container.floats.insert(0, float_)

        self.app.layout.focus(dialog)
        result = await dialog.future
        self.app.layout.focus(self.commandLine)

        if float_ in self.root_container.floats:
            self.root_container.floats.remove(float_)

        return result

    async def run_async(self):
        await self.app.run_async()

    def run(self):
        self.app.run()
        #asyncio.run(self.run_async())

    def get_width(self):
        "获取ConsoleView的实际宽度，等于输出宽度-4,（左右线条宽度, 滚动条宽度，右边让出的1列）"
        return self.app.output.get_size().columns - 4

    def get_height(self):
        "获取ConsoleView的实际高度，等于输出高度-5,（上下线条，菜单，命令栏，状态栏）"
        #return self.console.height
        return self.app.output.get_size().rows - 5

if __name__ == "__main__":
    app = PyMudApp()
    app.run()