import asyncio, functools, re, os, webbrowser, threading
from datetime import datetime
from pathlib import Path
from prompt_toolkit.shortcuts import set_title, radiolist_dialog
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit import HTML
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, Float, VSplit, HSplit, Window, WindowAlign, ScrollbarMargin, NumberedMargin
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
from wcwidth import wcwidth, wcswidth

from .objects import CodeBlock
from .extras import MudFormatProcessor, SessionBuffer, EasternMenuContainer, VSplitWindow, SessionBufferControl, DotDict
from .modules import Plugin
from .session import Session
from .settings import Settings
from .dialogs import MessageDialog, WelcomeDialog, QueryDialog, NewSessionDialog, LogSelectionDialog

from enum import Enum

class STATUS_DISPLAY(Enum):
    NONE = 0
    HORIZON = 1
    VERTICAL = 2
    FLOAT = 3

class PyMudApp:
    """
    PYMUD程序管理主对象，对窗体、操作及所有会话进行管理。

    PyMudApp对象不需要手动创建，在命令行中执行 ``python -m pymud`` 时会自动创建对象实例。

    参数： 
        - ``cfg_data``: 替代配置数据，由本地pymud.cfg文件读取，用于覆盖settings.py中的默认Settings数据

    可替代字典: 含义请查阅 `应用配置及本地化 <settings.html>`_
        - sessions: 用于创建菜单栏会话的字典
        - client: 用于配置客户端属性的字典
        - text: 用于各默认显示文字内容的字典
        - server: 用于服务器选项的配置字典
        - styles: 用于显示样式的定义字典
        - keys: 用于快捷键定义的字典

    *替代配置按不同的dict使用dict.update进行更新覆盖，因此可以仅指定需替代的部分。*
    """

    def __init__(self, cfg_data = None) -> None:
        """
        构造PyMudApp对象实例，并加载替代配置。
        """

        from .i18n import i18n_LoadLanguage, i18n_ListAvailableLanguages
        # 加载默认chs语言内容，以防翻译不完整时，默认使用中文替代
        i18n_LoadLanguage("chs")

        if cfg_data and isinstance(cfg_data, dict):
            # load language from 
            language = Settings.language
            if "language" in cfg_data.keys():
                if cfg_data["language"] in i18n_ListAvailableLanguages() and cfg_data["language"] != "chs":
                    language = cfg_data["language"]
                    i18n_LoadLanguage(language)
            
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
                elif key == "language":
                    Settings.language = cfg_data[key]

        self._mouse_support = True
        self._plugins  = DotDict()              # 增加 插件 字典
        self._globals  = DotDict()              # 增加所有session使用的全局变量
        self._onTimerCallbacks = dict()
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
        self.keybindings.add(Keys.ShiftLeft, is_global = True)(self.change_session)    # Shift-左右箭头切换当前会话
        self.keybindings.add(Keys.ShiftRight, is_global = True)(self.change_session)   # 适配 MacOS系统
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

        self.loggers = dict()           # 所有记录字典
        self.showLog = False            # 是否显示记录页
        self.logFileShown = ''          # 记录页显示的记录文件名
        self.logSessionBuffer = SessionBuffer()
        self.logSessionBuffer.name = "LOGBUFFER"

        self.load_plugins()

    async def onSystemTimerTick(self):
        while True:
            await asyncio.sleep(1)
            self.app.invalidate()
            for callback in self._onTimerCallbacks.values():
                if callable(callback):
                    callback()

    def addTimerTickCallback(self, name, func):
        '注册一个系统定时器回调，每1s触发一次。指定name为回调函数关键字，func为回调函数。'
        if callable(func) and (not name in self._onTimerCallbacks.keys()):
            self._onTimerCallbacks[name] = func

    def removeTimerTickCallback(self, name):
        '从系统定时器回调中移除一个回调函数。指定name为回调函数关键字。'
        if name in self._onTimerCallbacks.keys():
            self._onTimerCallbacks.pop(name)

    def initUI(self):
        """初始化UI界面"""
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
            #left_margins=[NumberedMargin()],
            #right_margins=[ScrollbarMargin(True)],   
            style="class:text-area"
            )

        console_with_bottom_status = ConditionalContainer(
            content = HSplit(
                [
                    self.console,
                    ConditionalContainer(content = Window(char = "—", height = 1), filter = Settings.client["status_divider"]),
                    #Window(char = "—", height = 1),
                    Window(content = self.statusView, height = Settings.client["status_height"]),
                ]
            ),
            filter = to_filter(self.status_display == STATUS_DISPLAY.HORIZON)
        )


        console_with_right_status = ConditionalContainer(
            content = VSplit(
                [
                    self.console,
                    ConditionalContainer(content = Window(char = "|", width = 1), filter = Settings.client["status_divider"]),
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
                    Settings.gettext("world"),
                    children=self.create_world_menus(),
                ),
                MenuItem(
                    Settings.gettext("session"),
                    children=[
                        MenuItem(Settings.gettext("disconnect"), handler = self.act_discon),
                        MenuItem(Settings.gettext("connect"), handler = self.act_connect),
                        MenuItem(Settings.gettext("closesession"), handler = self.act_close_session),
                        MenuItem(Settings.gettext("autoreconnect"), handler = self.act_autoreconnect),
                        MenuItem("-", disabled=True),
                        MenuItem(Settings.gettext("nosplit"), handler = self.act_nosplit),
                        MenuItem(Settings.gettext("echoinput"), handler = self.act_echoinput),
                        MenuItem(Settings.gettext("beautify"), handler = self.act_beautify),
                        MenuItem(Settings.gettext("copy"), handler = self.act_copy),
                        MenuItem(Settings.gettext("copyraw"), handler = self.act_copyraw),
                        MenuItem(Settings.gettext("clearsession"), handler = self.act_clearsession),
                        MenuItem("-", disabled=True),
                        
                        MenuItem(Settings.gettext("reloadconfig"), handler = self.act_reload),
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
                    Settings.gettext("help"),
                    children=[
                        MenuItem(Settings.gettext("about"), handler = self.act_about)
                    ]
                ),

                MenuItem(
                    "",    # 增加一个空名称MenuItem，单机后焦点移动至命令行输入处，阻止右侧空白栏点击响应
                    handler = lambda : self.app.layout.focus(self.commandLine)
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
        "创建世界子菜单，其中根据本地pymud.cfg中的有关配置创建会话有关子菜单"
        menus = []
        menus.append(MenuItem(f'{Settings.gettext("new_session")}...', handler = self.act_new))
        menus.append(MenuItem("-", disabled=True))

        ss = Settings.sessions

        for key, site in ss.items():
            menu = MenuItem(key)
            for name in site["chars"].keys():
                sub = MenuItem(name, handler = functools.partial(self._quickHandleSession, key, name))
                menu.children.append(sub)
            menus.append(menu)

        menus.append(MenuItem("-", disabled=True))
        menus.append(MenuItem(Settings.gettext("show_log"), handler = self.show_logSelectDialog))
        menus.append(MenuItem("-", disabled=True))
        menus.append(MenuItem(Settings.gettext("exit"), handler=self.act_exit))

        return menus

    def invalidate(self):
        "刷新显示界面"
        self.app.invalidate()

    def scroll(self, lines = 1):
        "内容滚动指定行数，小于0为向上滚动，大于0为向下滚动"
        if self.current_session:
            s = self.current_session
            b = s.buffer
        elif self.showLog:
            b = self.logSessionBuffer
            
        if isinstance(b, Buffer):
            if lines < 0:
                b.cursor_up(-1 * lines)
            elif lines > 0:
                b.cursor_down(lines)

    def page_up(self, event: KeyPressEvent) -> None:
        "快捷键PageUp: 用于向上翻页。翻页页数为显示窗口行数的一半减去一行。"
        #lines = (self.app.output.get_size().rows - 5) // 2 - 1
        lines = self.get_height() // 2 - 1
        self.scroll(-1 * lines)

    def page_down(self, event: KeyPressEvent) -> None:
        "快捷键PageDown: 用于向下翻页。翻页页数为显示窗口行数的一半减去一行。"
        #lines = (self.app.output.get_size().rows - 5) // 2 - 1
        lines = self.get_height() // 2 - 1
        self.scroll(lines)

    def custom_key_press(self, event: KeyPressEvent):
        "自定义快捷键功能实现，根据keys字典配置在当前会话执行指定指令"
        if (len(event.key_sequence) == 1) and (event.key_sequence[-1].key in Settings.keys.keys()):
            cmd = Settings.keys[event.key_sequence[-1].key]
            if self.current_session:
                self.current_session.exec_command(cmd)

    def hide_history(self, event: KeyPressEvent) -> None:
        """快捷键Ctrl+Z: 关闭历史行显示"""
        self.act_nosplit()

    def copy_selection(self, event: KeyPressEvent)-> None:
        """快捷键Ctrl+C/Ctrl+R: 复制选择内容。根据按键不同选择文本复制方式和RAW复制方式"""
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
        """快捷键右箭头→: 自动完成建议"""
        b = event.current_buffer
        if b.cursor_position == len(b.text):
            s = b.auto_suggest.get_suggestion(b, b.document)
            if s:
                b.insert_text(s.text, fire_event=False)
        else:
            b.cursor_right()

    def change_session(self, event: KeyPressEvent):
        """快捷键Ctrl/Shift+左右箭头: 切换会话"""
        if self.current_session:
            current = self.current_session.name
            keys = list(self.sessions.keys())
            idx = keys.index(current)
            count = len(keys)

            if (event.key_sequence[-1].key == Keys.ControlRight) or (event.key_sequence[-1].key == Keys.ShiftRight):
                if idx < count - 1:
                    new_key = keys[idx+1]
                    self.activate_session(new_key)

                elif (idx == count -1) and self.showLog:
                    self.showLogInTab()

            elif (event.key_sequence[-1].key == Keys.ControlLeft) or (event.key_sequence[-1].key == Keys.ShiftLeft):
                if idx > 0:
                    new_key = keys[idx-1]
                    self.activate_session(new_key)

        else:
            if self.showLog:
                if (event.key_sequence[-1].key == Keys.ControlRight) or (event.key_sequence[-1].key == Keys.ShiftRight):
                    keys = list(self.sessions.keys())
                    if len(keys) > 0:
                        new_key = keys[-1]
                        self.activate_session(new_key)

    def toggle_mousesupport(self, event: KeyPressEvent):
        """快捷键F2: 切换鼠标支持状态。用于远程连接时本地复制命令执行操作"""
        self._mouse_support = not self._mouse_support
        if self._mouse_support:
            self.app.renderer.output.enable_mouse_support()
        else:
            self.app.renderer.output.disable_mouse_support()

    def copy(self, raw = False):
        """
        复制会话中的选中内容

        :param raw: 指定采取文本模式还是ANSI格式模式

        ``注意: 复制的内容仅存在于运行环境的剪贴板中。若使用ssh远程，该复制命令不能访问本地剪贴板。``
        """
        
        b = self.consoleView.buffer
        if b.selection_state:
            cur1, cur2 = b.selection_state.original_cursor_position, b.document.cursor_position
            start, end = min(cur1, cur2), max(cur1, cur2)
            srow, scol = b.document.translate_index_to_position(start)
            erow, ecol = b.document.translate_index_to_position(end)
            # srow, scol = b.document.translate_index_to_position(b.selection_state.original_cursor_position)
            # erow, ecol = b.document.translate_index_to_position(b.document.cursor_position)

            if not raw:
                # Control-C 复制纯文本
                if srow == erow:
                    # 单行情况
                    #line = b.document.current_line
                    line = self.mudFormatProc.line_correction(b.document.current_line)
                    start = max(0, scol)
                    end = min(ecol, len(line))
                    line_plain = Session.PLAIN_TEXT_REGX.sub("", line).replace("\r", "").replace("\x00", "")
                    selection = line_plain[start:end]
                    self.app.clipboard.set_text(selection)
                    self.set_status(Settings.gettext("msg_copy", selection))
                    if self.current_session:
                        self.current_session.setVariable("%copy", selection)
                else:
                    # 多行只认行
                    lines = []
                    for row in range(srow, erow + 1):
                        line = b.document.lines[row]
                        line_plain = Session.PLAIN_TEXT_REGX.sub("", line).replace("\r", "").replace("\x00", "")
                        lines.append(line_plain)

                    self.app.clipboard.set_text("\n".join(lines))
                    self.set_status(Settings.gettext("msg_copylines", 1 + erow - srow))
                    
                    if self.current_session:
                        self.current_session.setVariable("%copy", "\n".join(lines))
                    
            else:
                # Control-R 复制带有ANSI标记的原始内容（对应字符关系会不正确，因此RAW复制时自动整行复制）
                if srow == erow:
                    line = b.document.current_line
                    self.app.clipboard.set_text(line)
                    self.set_status(Settings.gettext("msg_copy", line))
                    
                    if self.current_session:
                        self.current_session.setVariable("%copy", line)

                else:
                    lines = b.document.lines[srow:erow+1]
                    copy_raw_text = "".join(lines)
                    self.app.clipboard.set_text(copy_raw_text)
                    self.set_status(Settings.gettext("msg_copylines", 1 + erow - srow))

                    if self.current_session:
                        self.current_session.setVariable("%copy", copy_raw_text)

        else:
            self.set_status(Settings.gettext("msg_no_selection"))

    def create_session(self, name, host, port, encoding = None, after_connect = None, scripts = None, userid = None):
        """
        创建一个会话。菜单或者#session命令均调用本函数执行创建会话。

        :param name: 会话名称
        :param host: 服务器域名或IP地址
        :param port: 端口号
        :param encoding: 服务器编码
        :param after_connect: 连接后要向服务器发送的内容，用来实现自动登录功能
        :param scripts: 要加载的脚本清单
        :param userid: 自动登录的ID(获取自cfg文件中的定义，绑定到菜单)，将以该值在该会话中创建一个名为id的变量
        """
        result = False
        encoding = encoding or Settings.server["default_encoding"]

        if name not in self.sessions.keys():
            session = Session(self, name, host, port, encoding, after_connect, scripts = scripts)
            session.setVariable("id", userid)
            self.sessions[name] = session
            self.activate_session(name)

            for plugin in self._plugins.values():
                if isinstance(plugin, Plugin):
                    plugin.onSessionCreate(session)

            result = True
        else:
            self.set_status(Settings.gettext("msg_session_exists", name))

        return result

    def show_logSelectDialog(self):
        def correction_align_width(text, width):
            "修正文本对齐宽度，防止ljust和rjust方法产生的中文宽度不对齐问题"
            return width - wcswidth(text) + len(text)
        async def coroutine():
            title_filename = Settings.gettext("logfile_name").ljust(correction_align_width(Settings.gettext("logfile_name"), 20))
            title_filesize = Settings.gettext("logfile_size").rjust(correction_align_width(Settings.gettext("logfile_size"), 20))
            title_modified = Settings.gettext("logfile_modified").center(correction_align_width(Settings.gettext("logfile_modified"), 23))
            head_line = "   {}{}{}".format(title_filename, title_filesize, title_modified)
            
            log_list = list()
            files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.log')]
            for file in files:
                file = os.path.abspath(file)
                filename = os.path.basename(file).ljust(20)
                filesize = f"{os.path.getsize(file):,} Bytes".rjust(20)
                # ctime   = datetime.fromtimestamp(os.path.getctime(file)).strftime('%Y-%m-%d %H:%M:%S').rjust(23)
                mtime   = datetime.fromtimestamp(os.path.getmtime(file)).strftime('%Y-%m-%d %H:%M:%S').rjust(23)
                
                file_display_line = "{}{}{}".format(filename, filesize, mtime)
                log_list.append((file, file_display_line))

            logDir = os.path.abspath(os.path.join(os.curdir, 'log'))
            if os.path.exists(logDir):
                files = [f for f in os.listdir(logDir) if f.endswith('.log')]
                for file in files:
                    file = os.path.join(logDir, file)
                    filename = ('log/' + os.path.basename(file)).ljust(20)
                    filesize = f"{os.path.getsize(file):,} Bytes".rjust(20)
                    # ctime   = datetime.fromtimestamp(os.path.getctime(file)).strftime('%Y-%m-%d %H:%M:%S').rjust(23)
                    mtime   = datetime.fromtimestamp(os.path.getmtime(file)).strftime('%Y-%m-%d %H:%M:%S').rjust(23)
                    
                    file_display_line = "{}{}{}".format(filename, filesize, mtime)
                    log_list.append((file, file_display_line))
            
            dialog = LogSelectionDialog(
                text = head_line,
                values = log_list
            )

            result = await self.show_dialog_as_float(dialog)

            if result:
                self.logFileShown = result
                self.showLogInTab()

        asyncio.ensure_future(coroutine())

    def showLogInTab(self):
        "在记录也显示LOG记录"
        self.current_session = None
        self.showLog = True

        if self.logFileShown:
            filename = os.path.abspath(self.logFileShown)
            if os.path.exists(filename):
                lock = threading.RLock()
                lock.acquire()
                with open(filename, 'r', encoding = 'utf-8', errors = 'ignore') as file:
                    self.logSessionBuffer._set_text(file.read())
                lock.release()

            self.logSessionBuffer.cursor_position = len(self.logSessionBuffer.text)
            self.consoleView.buffer = self.logSessionBuffer
            self.app.invalidate()

    def activate_session(self, key):
        "激活指定名称的session，并将该session设置为当前session"
        session = self.sessions.get(key, None)

        if isinstance(session, Session):
            self.current_session = session
            self.consoleView.buffer = session.buffer
            #self.set_status(Settings.text["session_changed"].format(session.name))
            self.app.invalidate()

    def close_session(self):
        "关闭当前会话。若当前会话处于连接状态，将弹出对话框以确认。"
        async def coroutine():
            if self.current_session:
                if self.current_session.connected:
                    dlgQuery = QueryDialog(HTML(f'<b fg="red">{Settings.gettext("warning")}</b>'), HTML(f'<style fg="red">{Settings.gettext("session_close_prompt", self.current_session.name)}</style>'))
                    result = await self.show_dialog_as_float(dlgQuery)
                    if result:
                        self.current_session.disconnect()

                        # 增加延时等待确保会话关闭
                        wait_time = 0
                        while self.current_session.connected:
                            await asyncio.sleep(0.1)
                            wait_time += 1
                            if wait_time > 100:
                                self.current_session.onDisconnected(None)
                                break
                            
                    else:
                        return

                for plugin in self._plugins.values():
                    if isinstance(plugin, Plugin):
                        plugin.onSessionDestroy(self.current_session)

                name = self.current_session.name
                self.current_session.closeLoggers()
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
        "菜单: 创建新会话"
        async def coroutine():
            dlgNew = NewSessionDialog()
            result = await self.show_dialog_as_float(dlgNew)
            if result:
                self.create_session(*result)
            return result
        
        asyncio.ensure_future(coroutine())

    def act_connect(self):
        "菜单: 连接/重新连接"
        if self.current_session:
            self.current_session.handle_connect()

    def act_discon(self):
        "菜单: 断开连接"
        if self.current_session:
            self.current_session.disconnect()

    def act_nosplit(self):
        "菜单: 取消分屏"
        if self.current_session:
            s = self.current_session
            b = s.buffer
            b.exit_selection()
            b.cursor_position = len(b.text)

        elif self.showLog:
            b = self.logSessionBuffer
            b.exit_selection()
            b.cursor_position = len(b.text)

    def act_close_session(self):
        "菜单: 关闭当前会话"
        if self.current_session:
            self.close_session()

        elif self.showLog:
            self.showLog = False
            self.logSessionBuffer.text = ""
            if len(self.sessions.keys()) > 0:
                new_sess = list(self.sessions.keys())[0]
                self.activate_session(new_sess)

    def act_beautify(self):
        "菜单: 打开/关闭美化显示"
        val = not Settings.client["beautify"]
        Settings.client["beautify"] = val
        if self.current_session:
            self.current_session.info(f'{Settings.gettext("msg_beautify")}{Settings.gettext("open") if val else Settings.gettext("close")}!')

    def act_echoinput(self):
        "菜单: 显示/隐藏输入指令"
        val = not Settings.client["echo_input"]
        Settings.client["echo_input"] = val
        if self.current_session:
            self.current_session.info(f'{Settings.gettext("msg_echoinput")}{Settings.gettext("open") if val else Settings.gettext("close")}!')

    def act_autoreconnect(self):
        "菜单: 打开/关闭自动重连"
        val = not Settings.client["auto_reconnect"]
        Settings.client["auto_reconnect"] = val
        if self.current_session:
            self.current_session.info(f'{Settings.gettext("msg_autoreconnect")}{Settings.gettext("open") if val else Settings.gettext("close")}')

    def act_copy(self):
        "菜单: 复制纯文本"
        self.copy()

    def act_copyraw(self):
        "菜单: 复制(ANSI)"
        self.copy(raw = True)

    def act_clearsession(self):
        "菜单: 清空会话内容"
        self.consoleView.buffer.text = ""

    def act_reload(self):
        "菜单: 重新加载脚本配置"
        if self.current_session:
            self.current_session.handle_reload()

    # 暂未实现该功能
    def act_change_layout(self, layout):
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
        """菜单: 退出"""
        async def coroutine():
            con_sessions = list()
            for session in self.sessions.values():
                if session.connected:
                    con_sessions.append(session.name)

            if len(con_sessions) > 0:
                dlgQuery = QueryDialog(HTML(f'<b fg="red">{Settings.gettext('warning_exit')}</b>'), HTML(f'<style fg="red">{Settings.gettext("app_exit_prompt", len(con_sessions), ", ".join(con_sessions))}</style>'))
                result = await self.show_dialog_as_float(dlgQuery)
                if result:
                    for ss_name in con_sessions:
                        ss = self.sessions[ss_name]
                        ss.disconnect()

                        # 增加延时等待确保会话关闭
                        wait_time = 0
                        while ss.connected:
                            await asyncio.sleep(0.1)
                            wait_time += 1
                            if wait_time > 100:
                                ss.onDisconnected(None)
                                break

                        for plugin in self._plugins.values():
                            if isinstance(plugin, Plugin):
                                plugin.onSessionDestroy(ss)

                else:
                    return
                
            self.app.exit()

        asyncio.ensure_future(coroutine())

    def act_about(self):
        "菜单: 关于"
        dialog_about = WelcomeDialog(True)
        self.show_dialog(dialog_about)

    # 菜单选项操作 - 完成

    def get_input_prompt(self):
        "命令输入行提示符"
        return HTML(Settings.gettext("input_prompt"))

    def btn_title_clicked(self, name, mouse_event: MouseEvent):
        "顶部会话标签点击切换鼠标事件"
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            if name == '[LOG]':
                self.showLogInTab()
            else:
                self.activate_session(name)

    def get_frame_title(self):
        "顶部会话标题选项卡"
        if len(self.sessions.keys()) == 0:
            if not self.showLog:
                return Settings.__appname__ + " " + Settings.__version__
            else:
                if self.logFileShown:
                    return f'[LOG] {self.logFileShown}'
                else:
                    return f'[LOG]'
        
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

        if self.showLog:
            if self.current_session is None:
                style = style = Settings.styles["selected"]
            else:
                style = Settings.styles["normal"]

            title = f'[LOG] {self.logFileShown}' if self.logFileShown else f'[LOG]'

            title_formatted_list.append((style, title, functools.partial(self.btn_title_clicked, '[LOG]')))
            title_formatted_list.append(("", " | "))

        return title_formatted_list[:-1]

    def get_statusbar_text(self):
        "状态栏内容"
        return [
            ("class:status", " "),
            ("class:status", self.status_message),
        ]
    
    def get_statusbar_right_text(self):
        "状态栏右侧内容"
        con_str, mouse_support, tri_status, beautify = "", "", "", ""
        if not Settings.client["beautify"]:
            beautify = Settings.gettext("status_nobeautify") + " "

        if not self._mouse_support:
            mouse_support = Settings.gettext("status_mouseinh") + " "

        if self.current_session:
            if self.current_session._ignore:
                tri_status = Settings.gettext("status_ignore") + " "

            if not self.current_session.connected:
                con_str = Settings.gettext("status_notconnect")
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
                    con_str = Settings.gettext("status_connected") + ": {0:.0f}{4}{1:.0f}{5}{2:.0f}{6}{3:.0f}{7}".format(days, hours, mins, sec, Settings.gettext("Day"), Settings.gettext("Hour"), Settings.gettext("Minute"), Settings.gettext("Second"))
                elif hours > 0:
                    con_str = Settings.gettext("status_connected") + ": {0:.0f}{3}{1:.0f}{4}{2:.0f}{5}".format(hours, mins, sec, Settings.gettext("Hour"), Settings.gettext("Minute"), Settings.gettext("Second"))
                elif mins > 0:
                    con_str = Settings.gettext("status_connected") + ": {0:.0f}{2}{1:.0f}{3}".format(mins, sec, Settings.gettext("Minute"), Settings.gettext("Second"))
                else:
                    con_str = Settings.gettext("status_connected") + ": {:.0f}{}".format(sec, Settings.gettext("Second"))

        return "{}{}{}{} {} {} ".format(beautify, mouse_support, tri_status, con_str, Settings.__appname__, Settings.__version__)

    def get_statuswindow_text(self):
        "状态窗口: status_maker 的内容"
        text = ""

        try:
            if self.current_session:
                text = self.current_session.get_status()
        except Exception as e:
            text = f"{e}"

        return text

    def set_status(self, msg):
        """
        在状态栏中上显示消息。可在代码中调用
        
        :param msg: 要显示的消息
        """
        self.status_message = msg
        self.app.invalidate()

    def _quickHandleSession(self, group, name):
        '''
        根据指定的组名和会话角色名，从Settings内容，创建一个会话
        '''
        handled = False
        if name in self.sessions.keys():
           self.activate_session(name)
           handled = True

        else:
            site = Settings.sessions[group]
            if name in site["chars"].keys():
                host = site["host"]
                port = site["port"]
                encoding = site["encoding"]
                autologin = site["autologin"]
                default_script = site["default_script"]
                
                def_scripts = list()
                if isinstance(default_script, str):
                    def_scripts.extend(default_script.split(","))
                elif isinstance(default_script, (list, tuple)):
                    def_scripts.extend(default_script)

                charinfo = site["chars"][name]

                after_connect = autologin.format(charinfo[0], charinfo[1])
                sess_scripts = list()
                sess_scripts.extend(def_scripts)
                    
                if len(charinfo) == 3:
                    session_script = charinfo[2]
                    if session_script:
                        if isinstance(session_script, str):
                            sess_scripts.extend(session_script.split(","))
                        elif isinstance(session_script, (list, tuple)):
                            sess_scripts.extend(session_script)

                self.create_session(name, host, port, encoding, after_connect, sess_scripts, charinfo[0])
                handled = True
        
        return handled


    def handle_session(self, *args):
        '''
        嵌入命令 #session 的执行函数，创建一个远程连接会话。
        该函数不应该在代码中直接调用。

        使用:
            - #session {name} {host} {port} {encoding}
            - 当不指定 Encoding: 时, 默认使用utf-8编码
            - 可以直接使用 #{名称} 切换会话和操作会话命令

            - #session {group}.{name}
            - 相当于直接点击菜单{group}下的{name}菜单来创建会话. 当该会话已存在时，切换到该会话

        参数:
            :name: 会话名称
            :host: 服务器域名或IP地址
            :port: 端口号
            :encoding: 编码格式，不指定时默认为 utf8
    
            :group: 组名, 即配置文件中, sessions 字段下的某个关键字
            :name: 会话快捷名称, 上述 group 关键字下的 chars 字段中的某个关键字

        示例:
            ``#session {名称} {宿主机} {端口} {编码}`` 
                创建一个远程连接会话，使用指定编码格式连接到远程宿主机的指定端口并保存为 {名称} 。其中，编码可以省略，此时使用Settings.server["default_encoding"]的值，默认为utf8
            ``#session newstart mud.pkuxkx.net 8080 GBK`` 
                使用GBK编码连接到mud.pkuxkx.net的8080端口，并将该会话命名为newstart
            ``#session newstart mud.pkuxkx.net 8081`` 
                使用UTF8编码连接到mud.pkuxkx.net的8081端口，并将该会话命名为newstart
            ``#newstart`` 
                将名称为newstart的会话切换为当前会话
            ``#newstart give miui gold`` 
                使名称为newstart的会话执行give miui gold指令，但不切换到该会话

            ``#session pkuxkx.newstart``
                通过指定快捷配置创建会话，相当于点击 世界->pkuxkx->newstart 菜单创建会话。若该会话存在，则切换到该会话

        相关命令:
            - #close
            - #exit

        '''

        nothandle = True
        errmsg = "错误的#session命令"
        if len(args) == 1:
            host_session = args[0]
            if '.' in host_session:
                group, name = host_session.split('.')
                nothandle = not self._quickHandleSession(group, name)

            else:
                errmsg = Settings.gettext("msg_cmd_session_error")

        elif len(args) >= 3:
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
            self.set_status(errmsg)

    def enter_pressed(self, buffer: Buffer):
        "命令行回车按键处理"
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
                        self.current_session.log.log(f"{Settings.gettext('msg_cmdline_input')} {cmd_line}\n")

                        cb = CodeBlock(cmd_line)
                        cb.execute(self.current_session)
                    except Exception as e:
                        self.current_session.warning(e)
                        self.current_session.exec_command(cmd_line)
            else:
                if cmd_line == "#exit":
                    self.act_exit()
                elif (cmd_line == "#close") and self.showLog:
                    self.act_close_session()
                else:
                    self.set_status(Settings.gettext("msg_no_session"))

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
        """
        全局变量，快捷点访问器
        用于替代get_globals与set_globals函数的调用
        """
        return self._globals

    def get_globals(self, name, default = None):
        """
        获取PYMUD全局变量
        
        :param name: 全局变量名称
        :param default: 当全局变量不存在时的返回值
        """
        if name in self._globals.keys():
            return self._globals[name]
        else:
            return default

    def set_globals(self, name, value):
        """
        设置PYMUD全局变量

        :param name: 全局变量名称
        :param value: 全局变量值。值可以为任何类型。
        """
        self._globals[name] = value

    def del_globals(self, name):
        """
        移除一个PYMUD全局变量
        移除全局变量是从字典中删除该变量，而不是将其设置为None

        :param name: 全局变量名称
        """
        if name in self._globals.keys():
            self._globals.pop(name)

    @property
    def plugins(self):
        "所有已加载的插件列表，快捷点访问器"
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
        "以异步方式运行本程序"
        # 运行插件启动应用，放在此处，确保插件初始化在event_loop创建完成之后运行
        for plugin in self._plugins.values():
            if isinstance(plugin, Plugin):
                plugin.onAppInit(self)
                
        asyncio.create_task(self.onSystemTimerTick())
        await self.app.run_async(set_exception_handler = False)

        # 当应用退出时，运行插件销毁应用
        for plugin in self._plugins.values():
            if isinstance(plugin, Plugin):
                plugin.onAppDestroy(self)

    def run(self):
        "运行本程序"
        #self.app.run(set_exception_handler = False)
        asyncio.run(self.run_async())

    def get_width(self):
        "获取ConsoleView的实际宽度，等于输出宽度,（已经没有左右线条和滚动条了）"
        size = self.app.output.get_size().columns
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
        "加载插件。将加载pymud包的plugins目录下插件，以及当前目录的plugins目录下插件"
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
                        # plugin.onAppInit(self)
                    except Exception as e:
                        self.set_status(Settings.gettext("msg_plugin_load_error", file, e))
        
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
                        self.set_status(Settings.gettext("msg_plugin_load_error", file, e))

    def reload_plugin(self, plugin: Plugin):
        "重新加载指定插件"
        for session in self.sessions.values():
            plugin.onSessionDestroy(session)

        plugin.reload()
        plugin.onAppInit(self)

        for session in self.sessions.values():
            plugin.onSessionCreate(session)
        

def startApp(cfg_data = None):
    app = PyMudApp(cfg_data)
    app.run()
