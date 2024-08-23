import asyncio, webbrowser

from prompt_toolkit.layout import AnyContainer, ConditionalContainer, Float, VSplit, HSplit, Window, WindowAlign, ScrollablePane, ScrollOffsets
from prompt_toolkit.widgets import Button, Dialog, Label, MenuContainer, MenuItem, TextArea, SystemToolbar, Frame, RadioList 
from prompt_toolkit.layout.dimension import Dimension, D
from prompt_toolkit import ANSI, HTML
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.application.current import get_app
from .extras import EasternButton

from .settings import Settings

class BasicDialog:
    def __init__(self, title = "", modal = True):
        self.future = asyncio.Future()
        self.dialog = Dialog(
            body = self.create_body(),
            title = title,
            buttons = self.create_buttons(),
            modal = modal,
            width = D(preferred=80),
        )

    def set_done(self, result = True):
        self.future.set_result(result)

    def create_body(self) -> AnyContainer:
        return HSplit([Label(text="basic dialog")])

    def create_buttons(self):
        ok_button = EasternButton(text="确定", handler=(lambda: self.set_done()))
        return [ok_button]

    def set_exception(self, exc):
        self.future.set_exception(exc)

    def __pt_container__(self):
        return self.dialog

class MessageDialog(BasicDialog):
    def __init__(self, title="", message = "", modal=True):
        self.message = message
        super().__init__(title, modal)

    def create_body(self) -> AnyContainer:
        return HSplit([Label(text=self.message)])
    
class QueryDialog(BasicDialog):
    def __init__(self, title="", message = "", modal=True):
        self.message = message
        super().__init__(title, modal)

    def create_body(self) -> AnyContainer:
        return HSplit([Label(text=self.message)])
    
    def create_buttons(self):
        ok_button = EasternButton(text="确定", handler=(lambda: self.set_done(True)))
        cancel_button = EasternButton(text="取消", handler=(lambda: self.set_done(False)))
        return [ok_button, cancel_button]

class WelcomeDialog(BasicDialog):
    def __init__(self, modal=True):
        self.website = FormattedText(
            [('', '访问 '),
             #('class:b', 'GitHub:'), 
             ('', 'https://pymud.readthedocs.org/', self.open_url),
             ('', ' 以查看最新帮助文档')]
             )
        super().__init__("PYMUD", modal)
        
    def open_url(self, event: MouseEvent):
        if event.event_type == MouseEventType.MOUSE_UP:
            webbrowser.open(Settings.__website__)

    def create_body(self) -> AnyContainer:
        import platform, sys
        body = HSplit([
            Window(height=1),
            Label(HTML('<b fg="red">PYMUD {0}</b> - a MUD Client Written in Python'.format(Settings.__version__, Settings.__release__)), align=WindowAlign.CENTER),
            Label(HTML('作者: <b>{0}</b> <b>E-mail</b>: <u>{1}</u>'.format(Settings.__author__, Settings.__email__)), align=WindowAlign.CENTER),
            Label(self.website, align=WindowAlign.CENTER),
            Label('系统:{} {}   Python版本:{}'.format(platform.system(), platform.version(), platform.python_version()), align = WindowAlign.CENTER),

            Window(height=1),
        ])
        
        return body

class NewSessionDialog(BasicDialog):
    def __init__(self):
        super().__init__("创建新会话", True)
    
    def create_body(self) -> AnyContainer:
        body = HSplit([
            VSplit([
                HSplit([
                    Label(" 会话名称:"),
                    Frame(body=TextArea(name = "session", text="session", multiline=False, wrap_lines=False, height = 1, dont_extend_height=True, width = D(preferred=10), focus_on_click=True, read_only=False),)
                ]),
                HSplit([
                    Label(" 服务器地址:"),
                    Frame(body=TextArea(name = "host", text="mud.pkuxkx.net", multiline=False, wrap_lines=False, height = 1, dont_extend_height=True, width = D(preferred=20), focus_on_click=True, read_only=False),)
                ]),
                HSplit([
                    Label(" 端口:"),
                    Frame(body=TextArea(name = "port", text="8081", multiline=False, wrap_lines=False, height = 1, dont_extend_height=True, width = D(max=8), focus_on_click=True, read_only=False),)
                ]),
                HSplit([
                    Label(" 编码:"),
                    Frame(body=TextArea(name = "encoding", text="utf8", multiline=False, wrap_lines=False, height = 1, dont_extend_height=True, width = D(max=8), focus_on_click=True, read_only=False),)
                ]),
            ])
        ])

        return body

    def create_buttons(self):
        ok_button = EasternButton(text="确定", handler=self.btn_ok_clicked)
        cancel_button = EasternButton(text="取消", handler=(lambda: self.set_done(False)))
        return [ok_button, cancel_button]
    
    def btn_ok_clicked(self):
        name = get_app().layout.get_buffer_by_name("session").text
        host = get_app().layout.get_buffer_by_name("host").text
        port = int(get_app().layout.get_buffer_by_name("port").text)
        encoding = get_app().layout.get_buffer_by_name("encoding").text
        result = (name, host, port, encoding)
        self.set_done(result)


class LogSelectionDialog(BasicDialog):
    def __init__(self, text, values, modal=True):
        self._header_text = text
        self._selection_values = values
        self._itemsCount = len(values)
        if len(values) > 0:
            self._radio_list = RadioList(values = self._selection_values)
        else:
            self._radio_list = Label('无记录'.center(13))
        super().__init__('选择查看的记录', modal)

    def create_body(self) -> AnyContainer:
        body=HSplit([
            Label(text = self._header_text, dont_extend_height=True), 
            self._radio_list
            ])
        return body
    
    def create_buttons(self):
        ok_button = EasternButton(text="确定", handler=self.btn_ok_clicked)
        cancel_button = EasternButton(text="取消", handler=(lambda: self.set_done(False)))
        return [ok_button, cancel_button]
    
    def btn_ok_clicked(self):
        if self._itemsCount:
            result = self._radio_list.current_value
            self.set_done(result)
        else:
            self.set_done(False)
    