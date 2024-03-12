import asyncio, functools, re, logging, math, json, os, webbrowser
import importlib.util
from prompt_toolkit.shortcuts import set_title
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit import HTML
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, Float, VSplit, HSplit, Window, WindowAlign
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Label, MenuItem, TextArea
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.key_binding import KeyPress, KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import (
    Condition,
    is_true,
    to_filter,
)
from prompt_toolkit.formatted_text import (
    Template,
)
from prompt_toolkit.layout.processors import (
    DisplayMultipleCursors,
    HighlightSearchProcessor,
    HighlightSelectionProcessor,
)
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from .objects import CodeBlock
from .extras import MudFormatProcessor, SessionBuffer, EasternMenuContainer, VSplitWindow, SessionBufferControl, DotDict, Plugin
from .session import Session
from .settings import Settings
from .dialogs import MessageDialog, WelcomeDialog, QueryDialog, NewSessionDialog

from enum import Enum

class STATUS_DISPLAY(Enum):
    NONE = 0
    HORIZON = 1
    VERTICAL = 2
    FLOAT = 3

class PyMudApp:
    """
    PYMUD程序管理主对象，对窗体、操作及所有会话进行管理。
    """
    def __init__(self, cfg_data = None) -> None:
        if cfg_data and isinstance(cfg_data, dict):
            for key in cfg_data.keys():
                if key == "sessions":
                    Settings.sessions = cfg_data[key]
                elif key == "client":
                    Settings.client.update(cfg_data[key])
                elif key == "text":
                    Settings.text.update(cfg_data[key])
                elif key == "server":
                    Settings.server.update(cfg_data[key])
                elif key == "styles":
                    Settings.styles.update(cfg_data[key])
                elif key == "keys":
                    Settings.keys.update(cfg_data[key])

        self._mouse_support = True
        self._plugins  = DotDict()              # 增加 插件 字典
        self._globals  = DotDict()              # 增加所有session使用的全局变量
        self.sessions = {}
        self.current_session = None
        self.status_display = STATUS_DISPLAY(Settings.client["status_display"])

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
        self.keybindings.add(Keys.F1, is_global=True)(lambda event: webbrowser.open(Settings.__website__))
        self.keybindings.add(Keys.F2, is_global=True)(self.toggle_mousesupport)

        used_keys = [Keys.PageUp, Keys.PageDown, Keys.ControlZ, Keys.ControlC, Keys.ControlR, Keys.Up, Keys.Down, Keys.Left, Keys.Right, Keys.ControlLeft, Keys.ControlRight, Keys.Backspace, Keys.Delete, Keys.F1, Keys.F2]

        for key, binding in Settings.keys.items():
            if (key not in used_keys) and binding and isinstance(binding, str):
                self.keybindings.add(key, is_global = True)(self.custom_key_press)

        self.initUI()

        # 对剪贴板进行处理，经测试，android下的termux中，pyperclip无法使用，因此要使用默认的InMemoryClipboard
        clipboard = None
        try:
            clipboard = PyperclipClipboard()
            clipboard.set_text("test pyperclip")
            clipboard.set_text("")
        except:
            clipboard = None

        self.app = Application(
            layout = Layout(self.root_container, focused_element=self.commandLine),
            enable_page_navigation_bindings=True,
            style=self.style,
            mouse_support=to_filter(self._mouse_support),
            full_screen=True,
            color_depth=ColorDepth.TRUE_COLOR,
            clipboard=clipboard,
            key_bindings=self.keybindings,
            cursor=CursorShape.BLINKING_UNDERLINE
        )

        set_title("{} {}".format(Settings.__appname__, Settings.__version__))
        self.set_status(Settings.text["welcome"])

        self.load_plugins()

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

        # 增加状态窗口显示
        self.statusView = FormattedTextControl(
            text = self.get_statuswindow_text,
            show_cursor=False
        )

        self.mudFormatProc = MudFormatProcessor()

        self.consoleView = SessionBufferControl(
            buffer = None,
            input_processors=[
                self.mudFormatProc,
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
            #right_margins=[ScrollbarMargin(True)],   
            style="class:text-area"
            )

        console_with_bottom_status = ConditionalContainer(
            content = HSplit(
                [
                    self.console,
                    Window(char = "—", height = 1),
                    Window(content = self.statusView, height = Settings.client["status_height"]),
                ]
            ),
            filter = to_filter(self.status_display == STATUS_DISPLAY.HORIZON)
        )


        console_with_right_status = ConditionalContainer(
            content = VSplit(
                [
                    self.console,
                    Window(char = "|", width = 1),
                    Window(content = self.statusView, width = Settings.client["status_width"]),
                ]
            ),
            filter = to_filter(self.status_display == STATUS_DISPLAY.VERTICAL)
        )

        console_without_status = ConditionalContainer(
            content = self.console,
            filter = to_filter(self.status_display == STATUS_DISPLAY.NONE)
        )

        body = HSplit(
            [
                console_without_status,
                console_with_right_status,
                console_with_bottom_status
            ]
        )

        fill = functools.partial(Window, style="class:frame.border")
        top_row_with_title = VSplit(
            [
                #fill(width=1, height=1, char=Border.TOP_LEFT),
                fill(char = "\u2500"),
                fill(width=1, height=1, char="|"),
                # Notice: we use `Template` here, because `self.title` can be an
                # `HTML` object for instance.
                Label(
                    lambda: Template(" {} ").format(self.get_frame_title),
                    style="class:frame.label",
                    dont_extend_width=True,
                ),
                fill(width=1, height=1, char="|"),
                fill(char = "\u2500"),
                #fill(width=1, height=1, char=Border.TOP_RIGHT),
            ],
            height=1,
        )

        new_body = HSplit([
            top_row_with_title,
            body,
            fill(height = 1, char = "\u2500"),
        ])

        #self.console_frame = Frame(body = body, title = self.get_frame_title)

        self.body = HSplit([
                new_body,
                #self.console_frame,
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
                        MenuItem(Settings.text["autoreconnect"], handler = self.act_autoreconnect),
                        MenuItem("-", disabled=True),
                        MenuItem(Settings.text["echoinput"], handler = self.act_echoinput),
                        MenuItem(Settings.text["nosplit"], handler = self.act_nosplit),
                        MenuItem(Settings.text["copy"], handler = self.act_copy),
                        MenuItem(Settings.text["copyraw"], handler = self.act_copyraw),
                        MenuItem(Settings.text["clearsession"], handler = self.act_clearsession),
                        MenuItem("-", disabled=True),
                        MenuItem(Settings.text["reloadconfig"], handler = self.act_reload),
                    ]
                ),

                # MenuItem(
                #     Settings.text["layout"],
                #     children = [
                #         MenuItem(Settings.text["hide"], handler = functools.partial(self.act_change_layout, False)),
                #         MenuItem(Settings.text["horizon"], handler = functools.partial(self.act_change_layout, True)),
                #         MenuItem(Settings.text["vertical"], handler = functools.partial(self.act_change_layout, True)),
                #     ]
                # ),

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

    def create_world_menus(self):
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
            scripts = list()
            default_script = site["default_script"]
            
            def_scripts = list()
            if isinstance(default_script, str):
                def_scripts.extend(default_script.split(","))
            elif isinstance(default_script, (list, tuple)):
                def_scripts.extend(default_script)

            menu = MenuItem(key)
            for name, info in site["chars"].items():
                after_connect = autologin.format(info[0], info[1])
                sess_scripts = list()
                sess_scripts.extend(def_scripts)
                
                if len(info) == 3:
                    session_script = info[2]
                    if session_script:
                        if isinstance(session_script, str):
                            sess_scripts.extend(session_script.split(","))
                        elif isinstance(session_script, (list, tuple)):
                            sess_scripts.extend(session_script)

                sub = MenuItem(name, handler = functools.partial(self.create_session, name, host, port, encoding, after_connect, sess_scripts, info[0]))
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
        #lines = (self.app.output.get_size().rows - 5) // 2 - 1
        lines = self.get_height() // 2 - 1
        self.scroll(-1 * lines)

    def page_down(self, event: KeyPressEvent) -> None:
        #lines = (self.app.output.get_size().rows - 5) // 2 - 1
        lines = self.get_height() // 2 - 1
        self.scroll(lines)

    def custom_key_press(self, event: KeyPressEvent):
        if (len(event.key_sequence) == 1) and (event.key_sequence[-1].key in Settings.keys.keys()):
            cmd = Settings.keys[event.key_sequence[-1].key]
            if self.current_session:
                self.current_session.exec_command(cmd)

    def hide_history(self, event: KeyPressEvent) -> None:
        """关闭历史行显示"""
        self.act_nosplit()

    def copy_selection(self, event: KeyPressEvent)-> None:
        if event.key_sequence[-1].key == Keys.ControlC:
            self.copy()
        elif event.key_sequence[-1].key == Keys.ControlR:
            self.copy(raw = True)

    def delete_selection(self, event: KeyPressEvent):
        event.key_sequence
        b = event.current_buffer
        if b.selection_state:
            event.key_processor.feed(KeyPress(Keys.Delete), first=True)
        else:
            b.delete_before_cursor(1)

    def complete_autosuggest(self, event: KeyPressEvent):
        """自动完成建议"""
        b = event.current_buffer
        if b.cursor_position == len(b.text):
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

    def toggle_mousesupport(self, event: KeyPressEvent):
        self._mouse_support = not self._mouse_support
        if self._mouse_support:
            self.app.renderer.output.enable_mouse_support()
        else:
            self.app.renderer.output.disable_mouse_support()

    def copy(self, raw = False):
        b = self.consoleView.buffer
        if b.selection_state:
            srow, scol = b.document.translate_index_to_position(b.selection_state.original_cursor_position)
            erow, ecol = b.document.translate_index_to_position(b.document.cursor_position)

            if not raw:
                # Control-C 复制纯文本
                if srow == erow:
                    # 单行情况
                    #line = b.document.current_line
                    line = self.mudFormatProc.line_correction(b.document.current_line)
                    start = max(0, scol)
                    end = min(ecol, len(line))
                    line_plain = re.sub("\x1b\\[[\d;]+[abcdmz]", "", line, flags = re.IGNORECASE).replace("\r", "").replace("\x00", "")
                    #line_plain = re.sub("\x1b\\[[^mz]+[mz]", "", line).replace("\r", "").replace("\x00", "")
                    selection = line_plain[start:end]
                    self.app.clipboard.set_text(selection)
                    self.set_status("已复制：{}".format(selection))

                    self.current_session.setVariable("%copy", selection)
                else:
                    # 多行只认行
                    lines = []
                    for row in range(srow, erow + 1):
                        line = b.document.lines[row]
                        line_plain = re.sub("\x1b\\[[\d;]+[abcdmz]", "", line, flags = re.IGNORECASE).replace("\r", "").replace("\x00", "")
                        lines.append(line_plain)

                    self.app.clipboard.set_text("\n".join(lines))
                    self.set_status("已复制：行数{}".format(1 + erow - srow))

                    self.current_session.setVariable("%copy", "\n".join(lines))
                    
            else:
                # Control-R 复制带有ANSI标记的原始内容（对应字符关系会不正确，因此RAW复制时自动整行复制）
                if srow == erow:
                    line = b.document.current_line
                    self.app.clipboard.set_text(line)
                    self.set_status("已复制：{}".format(line))

                    self.current_session.setVariable("%copy", line)

                else:
                    lines = b.document.lines[srow:erow+1]
                    copy_raw_text = "".join(lines)
                    self.app.clipboard.set_text(copy_raw_text)
                    self.set_status("已复制：行数{}".format(1 + erow - srow))
                    self.current_session.setVariable("%copy", copy_raw_text)

                # data = self.consoleView.buffer.copy_selection()
                # self.app.clipboard.set_data(data)
                # self.set_status("已复制：{}".format(data.text))

                # self.current_session.setVariable("%copy", data.text)
        else:
            self.set_status("未选中任何内容...")

    def create_session(self, name, host, port, encoding = None, after_connect = None, scripts = None, userid = None):
        result = False
        encoding = encoding or Settings.server["default_encoding"]

        if name not in self.sessions.keys():
            session = Session(self, name, host, port, encoding, after_connect, scripts = scripts)
            session.setVariable("id", userid)
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
            #self.set_status(Settings.text["session_changed"].format(session.name))
            self.app.invalidate()

    def close_session(self):
        "关闭当前会话"
        async def coroutine():
            if self.current_session:
                if self.current_session.connected:
                    dlgQuery = QueryDialog(HTML('<b fg="red">警告</b>'), HTML('<style fg="red">当前会话 {0} 还处于连接状态，确认要关闭？</style>'.format(self.current_session.name)))
                    result = await self.show_dialog_as_float(dlgQuery)
                    if result:
                        self.current_session.disconnect()
                    else:
                        return

                for plugin in self._plugins.values():
                    if isinstance(plugin, Plugin):
                        plugin.onSessionCreate(self.current_session)

                name = self.current_session.name
                self.current_session.clean()
                self.current_session = None
                self.consoleView.buffer = SessionBuffer()
                self.sessions.pop(name)
                #self.set_status(f"会话 {name} 已关闭")
                if len(self.sessions.keys()) > 0:
                    new_sess = list(self.sessions.keys())[0]
                    self.activate_session(new_sess)
                    #self.set_status(f"当前会话已切换为 {self.current_session.name}")

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

    def act_echoinput(self):
        val = not Settings.client["echo_input"]
        Settings.client["echo_input"] = val
        if self.current_session:
            self.current_session.info(f"回显输入命令被设置为：{'打开' if val else '关闭'}")

    def act_autoreconnect(self):
        val = not Settings.client["auto_reconnect"]
        Settings.client["auto_reconnect"] = val
        if self.current_session:
            self.current_session.info(f"自动重连被设置为：{'打开' if val else '关闭'}")

    def act_copy(self):
        "复制菜单"
        self.copy()

    def act_copyraw(self):
        "复制ANSI菜单"
        self.copy(raw = True)

    def act_clearsession(self):
        "清空当前会话缓存的文本内容"
        self.consoleView.buffer.text = ""

    def act_reload(self):
        "重新加载配置文件菜单"
        if self.current_session:
            self.current_session.handle_reload()

    def act_change_layout(self, layout):
        "更改状态窗口显示"
        #if isinstance(layout, STATUS_DISPLAY):
        self.status_display = layout
        #self.console_frame.body.reset()
        # if layout == STATUS_DISPLAY.HORIZON:
        #     self.console_frame.body = self.console_with_horizon_status
        # elif layout == STATUS_DISPLAY.VERTICAL:
        #     self.console_frame.body = self.console_with_vertical_status
        # elif layout == STATUS_DISPLAY.NONE:
        #     self.console_frame.body = self.console_without_status

        #self.show_message("布局调整", f"已将布局设置为{layout}")
        self.app.invalidate()

    def act_exit(self):
        "退出菜单"
        async def coroutine():
            for session in self.sessions.values():
                if session.connected:
                    dlgQuery = QueryDialog(HTML('<b fg="red">程序退出警告</b>'), HTML('<style fg="red">会话 {0} 还处于连接状态，确认要关闭？</style>'.format(session.name)))
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
        con_str, mouse_support, tri_status = "", "", ""
        if not self._mouse_support:
            mouse_support = "鼠标已禁用 "

        if self.current_session:
            if self.current_session._ignore:
                tri_status = "全局禁用 "

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

        return "{}{}{} {} {} ".format(mouse_support, tri_status, con_str, Settings.__appname__, Settings.__version__)

    def get_statuswindow_text(self):
        text = ""
        if self.current_session:
            text = self.current_session.get_status()

        return text

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
        "\x1b[1m相关\x1b[0m: help, exit\n"

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

    def enter_pressed(self, buffer: Buffer):
        cmd_line = buffer.text
        space_index = cmd_line.find(" ")
        
        if len(cmd_line) == 0:
            if self.current_session:
                self.current_session.writeline("")
        
        elif cmd_line[0] != Settings.client["appcmdflag"]:
            if self.current_session:
                self.current_session.last_command = cmd_line

        if cmd_line.startswith("#session"):
            cmd_tuple = cmd_line[1:].split()
            self.handle_session(*cmd_tuple[1:])

        else:
            if self.current_session:
                if len(cmd_line) == 0:
                    self.current_session.writeline("")
                else:
                    try:
                        cb = CodeBlock(cmd_line)
                        cb.execute(self.current_session)
                    except Exception as e:
                        self.current_session.warning(e)
                        self.current_session.exec_command(cmd_line)
            else:
                self.set_status("当前没有正在运行的session.")

        # 配置：命令行内容保留
        if Settings.client["remain_last_input"]:
            buffer.cursor_position = 0
            buffer.start_selection()
            buffer.cursor_right(len(cmd_line))
            return True
        
        else:
            return False

    @property
    def globals(self):
        return self._globals

    def get_globals(self, name, default = None):
        "获取PYMUD全局变量"
        if name in self._globals.keys():
            return self._globals[name]
        else:
            return default

    def set_globals(self, name, value):
        "设置PYMUD全局变量"
        self._globals[name] = value

    def del_globals(self, name):
        "移除一个PYMUD全局变量"
        if name in self._globals.keys():
            self._globals.pop(name)

    @property
    def plugins(self):
        return self._plugins

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
        size = self.app.output.get_size().columns - 4
        if Settings.client["status_display"] == 2:
            size = size - Settings.client["status_width"] - 1
        return size

    def get_height(self):
        "获取ConsoleView的实际高度，等于输出高度-5,（上下线条，菜单，命令栏，状态栏）"
        size = self.app.output.get_size().rows - 5

        if Settings.client["status_display"] == 1:
            size = size - Settings.client["status_height"] - 1
        return size

    #####################################
    # plugins 处理
    #####################################
    def load_plugins(self):
        # 首先加载系统目录下的插件
        current_dir = os.path.dirname(__file__)
        plugins_dir = os.path.join(current_dir, "plugins")
        if os.path.exists(plugins_dir):
            for file in os.listdir(plugins_dir):
                if file.endswith(".py"):
                    try:
                        file_path = os.path.join(plugins_dir, file)
                        file_name = file[:-3]
                        plugin = Plugin(file_name, file_path)
                        self._plugins[plugin.name] = plugin
                        plugin.onAppInit(self)
                    except Exception as e:
                        self.set_status(f"文件: {plugins_dir}\{file} 不是一个合法的插件文件，加载错误，信息为: {e}")
        
        # 然后加载当前目录下的插件
        current_dir = os.path.abspath(".")
        plugins_dir = os.path.join(current_dir, "plugins")
        if os.path.exists(plugins_dir):
            for file in os.listdir(plugins_dir):
                if file.endswith(".py"):
                    try:
                        file_path = os.path.join(plugins_dir, file)
                        file_name = file[:-3]
                        plugin = Plugin(file_name, file_path)
                        self._plugins[plugin.name] = plugin
                        plugin.onAppInit(self)
                    except Exception as e:
                        self.set_status(f"文件: {plugins_dir}\{file} 不是一个合法的插件文件. 加载错误，信息为: {e}")


    def reload_plugin(self, plugin: Plugin):
        "重新加载指定插件"
        for session in self.sessions.values():
            plugin.onSessionDestroy(session)

        plugin.reload()
        plugin.onAppInit(self)

        for session in self.sessions.values():
            plugin.onSessionCreate(session)
        

def main(cfg_data = None):
    logging.disable()
    app = PyMudApp(cfg_data)
    app.run()

if __name__ == "__main__":

    cfg = "pymud.cfg"
    import sys
    args = sys.argv
    if len(args) > 1:
        cfg = args[1]

    if os.path.exists(cfg):
        with open(cfg, "r", encoding="utf8", errors="ignore") as fp:
            cfg_data = json.load(fp)
            main(cfg_data)
    else:
        main()