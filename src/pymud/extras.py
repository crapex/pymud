# External Libraries
from unicodedata import east_asian_width
from wcwidth import wcwidth
import time, re, logging

from typing import Iterable
from prompt_toolkit import ANSI
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import to_formatted_text, fragment_list_to_text
from prompt_toolkit.formatted_text.base import OneStyleAndTextTuple
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout.controls import UIContent
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.selection import SelectionType
from prompt_toolkit.buffer import Buffer, ValidationState

from prompt_toolkit.filters import (
    FilterOrBool,
)
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
    to_formatted_text,
)
from prompt_toolkit.formatted_text.utils import fragment_list_to_text
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding.key_bindings import KeyBindingsBase
from prompt_toolkit.layout.containers import (
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import (
    BufferControl,
    FormattedTextControl,
)
from prompt_toolkit.layout.processors import (
    Processor,
    TransformationInput,
    Transformation
)
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import Button, MenuContainer, MenuItem
from prompt_toolkit.widgets.base import Border

from prompt_toolkit.layout.screen import _CHAR_CACHE, Screen, WritePosition
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
)

from .settings import Settings

class MudFormatProcessor(Processor):
    "在BufferControl中显示ANSI格式的处理器"

    def __init__(self) -> None:
        super().__init__()
        self.FULL_BLOCKS = set("▂▃▅▆▇▄█")
        self.SINGLE_LINES = set("┌└├┬┼┴╭╰─")
        self.DOUBLE_LINES = set("╔╚╠╦╪╩═")
        self.ALL_COLOR_REGX  = re.compile(r"(?:\[[\d;]+m)+")
        self.AVAI_COLOR_REGX = re.compile(r"(?:\[[\d;]+m)+(?!$)")
        self._color_start = ""
        self._color_correction = False
        self._color_line_index = 0

    def width_correction(self, line: str) -> str:
        new_str = []
        for ch in line:
            new_str.append(ch)
            if (east_asian_width(ch) in "FWA") and (wcwidth(ch) == 1):
                if ch in self.FULL_BLOCKS:
                    new_str.append(ch)
                elif ch in self.SINGLE_LINES:
                    new_str.append("─")
                elif ch in self.DOUBLE_LINES:
                    new_str.append("═")
                else:
                    new_str.append(' ')

        return "".join(new_str)
    
    def return_correction(self, line: str):
        return line.replace("\r", "").replace("\x00", "")
    
    def tab_correction(self, line: str):
        return line.replace("\t", " " * Settings.client["tabstop"])

    def line_correction(self, line: str):
        # 处理\r符号（^M）
        line = self.return_correction(line)
        # 处理Tab(\r)符号（^I）
        line = self.tab_correction(line)
        
        # 美化（解决中文英文在Console中不对齐的问题）
        if Settings.client["beautify"]:
            line = self.width_correction(line)

        return line

    def apply_transformation(self, transformation_input: TransformationInput):
        # 准备（先还原为str）
        line = fragment_list_to_text(transformation_input.fragments)

        # 颜色校正
        thislinecolors = len(self.AVAI_COLOR_REGX.findall(line))
        if thislinecolors == 0:
            lineno = transformation_input.lineno - 1
            while lineno > 0:
                lastline = transformation_input.document.lines[lineno]
                allcolors = self.ALL_COLOR_REGX.findall(lastline)
                
                if len(allcolors) == 0:
                    lineno = lineno - 1

                elif len(allcolors) == 1:
                    colors = self.AVAI_COLOR_REGX.findall(lastline)
                    
                    if len(colors) == 1:
                        line = f"{colors[0]}{line}"
                        break

                    else:
                        break

                else:
                    break

        # 其他校正
        line = self.line_correction(line)

        # 处理ANSI标记（生成FormmatedText）
        fragments = to_formatted_text(ANSI(line))

        return Transformation(fragments)

class SessionBuffer(Buffer):
    "继承自Buffer，为Session内容所修改，主要修改为只能在最后新增内容，并且支持分屏显示适配"

    def __init__(
        self,
    ):
        super().__init__()

        # 修改内容
        self.__text = ""
        self.__split = False
        
    def _set_text(self, value: str) -> bool:
        """set text at current working_index. Return whether it changed."""
        original_value = self.__text
        self.__text = value

        # Return True when this text has been changed.
        if len(value) != len(original_value):
            return True
        elif value != original_value:
            return True
        return False

    @property
    def text(self) -> str:
        return self.__text

    @text.setter
    def text(self, value: str) -> None:
        # SessionBuffer is only appendable

        if self.cursor_position > len(value):
            self.cursor_position = len(value)

        changed = self._set_text(value)

        if changed:
            self._text_changed()
            self.history_search_text = None

    @property
    def working_index(self) -> int:
        return 0

    @working_index.setter
    def working_index(self, value: int) -> None:
        pass

    def _text_changed(self) -> None:
        # Remove any validation errors and complete state.
        self.validation_error = None
        self.validation_state = ValidationState.UNKNOWN
        self.complete_state = None
        self.yank_nth_arg_state = None
        self.document_before_paste = None
        
        # 添加内容时，不取消选择
        #self.selection_state = None

        self.suggestion = None
        self.preferred_column = None

        # fire 'on_text_changed' event.
        self.on_text_changed.fire()

    def set_document(self, value: Document, bypass_readonly: bool = False) -> None:
        pass

    @property
    def split(self) -> bool:
        return self.__split
    
    @split.setter
    def split(self, value: bool) -> None:
        self.__split = value

    @property
    def is_returnable(self) -> bool:
        return False

    # End of <getters/setters>

    def save_to_undo_stack(self, clear_redo_stack: bool = True) -> None:
        pass

    def delete(self, count: int = 1) -> str:
        pass

    def insert_text(
        self,
        data: str,
        overwrite: bool = False,
        move_cursor: bool = True,
        fire_event: bool = True,
    ) -> None:
        # 始终在最后增加内容
        self.text += data
        
        # 分隔情况下，光标保持原位置不变，否则光标始终位于最后
        if not self.__split:
            # 若存在选择状态，则视情保留选择
            if self.selection_state:
                start = self.selection_state.original_cursor_position
                end = self.cursor_position
                row, col = self.document.translate_index_to_position(start)
                lastrow, col = self.document.translate_index_to_position(len(self.text))
                self.exit_selection()
                # 还没翻过半页的话，就重新选择上
                if lastrow - row < get_app().output.get_size().rows // 2 - 1:
                    self.cursor_position = len(self.text)
                    self.cursor_position = start
                    self.start_selection
                    self.cursor_position = end
                else:
                    self.cursor_position = len(self.text)
            else:
                self.cursor_position = len(self.text)
        else:
            pass
        

    def clear_half(self):
        "将Buffer前半段内容清除，并清除缓存"
        remain_lines = len(self.document.lines) // 2
        start = self.document.translate_row_col_to_index(remain_lines, 0)
        new_text = self.text[start:]

        del self.history
        self.history = InMemoryHistory()
        
        self.text = ""
        self._set_text(new_text)

        self._document_cache.clear()
        new_doc  = Document(text = new_text, cursor_position = len(new_text))
        self.reset(new_doc, False)
        self.__split = False

        return new_doc.line_count

    def undo(self) -> None:
        pass

    def redo(self) -> None:
        pass


class SessionBufferControl(BufferControl):
    def __init__(self, buffer: SessionBuffer = None, input_processors = None, include_default_input_processors: bool = True, lexer: Lexer = None, preview_search: FilterOrBool = False, focusable: FilterOrBool = True, search_buffer_control = None, menu_position = None, focus_on_click: FilterOrBool = False, key_bindings: KeyBindingsBase = None):
        # 将所属Buffer类型更改为SessionBuffer
        buffer = buffer or SessionBuffer()
        super().__init__(buffer, input_processors, include_default_input_processors, lexer, preview_search, focusable, search_buffer_control, menu_position, focus_on_click, key_bindings)
        self.buffer = buffer


    def mouse_handler(self, mouse_event: MouseEvent):
        """
        鼠标处理，修改内容包括：
        1. 在CommandLine获得焦点的时候，鼠标对本Control也可以操作
        2. 鼠标双击为选中行
        """
        buffer = self.buffer
        position = mouse_event.position

        # Focus buffer when clicked.
        cur_control = get_app().layout.current_control
        cur_buffer = get_app().layout.current_buffer
        # 这里时修改的内容
        if (cur_control == self) or (cur_buffer and cur_buffer.name == "input"):
            if self._last_get_processed_line:
                processed_line = self._last_get_processed_line(position.y)

                # Translate coordinates back to the cursor position of the
                # original input.
                xpos = processed_line.display_to_source(position.x)
                index = buffer.document.translate_row_col_to_index(position.y, xpos)

                # Set the cursor position.
                if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                    buffer.exit_selection()
                    buffer.cursor_position = index

                elif (
                    mouse_event.event_type == MouseEventType.MOUSE_MOVE
                    and mouse_event.button != MouseButton.NONE
                ):
                    # Click and drag to highlight a selection
                    if (
                        buffer.selection_state is None
                        and abs(buffer.cursor_position - index) > 0
                    ):
                        buffer.start_selection(selection_type=SelectionType.CHARACTERS)
                    buffer.cursor_position = index

                elif mouse_event.event_type == MouseEventType.MOUSE_UP:
                    # When the cursor was moved to another place, select the text.
                    # (The >1 is actually a small but acceptable workaround for
                    # selecting text in Vi navigation mode. In navigation mode,
                    # the cursor can never be after the text, so the cursor
                    # will be repositioned automatically.)
                    
                    if abs(buffer.cursor_position - index) > 1:
                        if buffer.selection_state is None:
                            buffer.start_selection(
                                selection_type=SelectionType.CHARACTERS
                            )
                        buffer.cursor_position = index

                    # Select word around cursor on double click.
                    # Two MOUSE_UP events in a short timespan are considered a double click.
                    double_click = (
                        self._last_click_timestamp
                        and time.time() - self._last_click_timestamp < 0.3
                    )
                    self._last_click_timestamp = time.time()

                    if double_click:
                        start = buffer.document.translate_row_col_to_index(position.y, 0)
                        end = buffer.document.translate_row_col_to_index(position.y + 1, 0) - 1
                        buffer.cursor_position = start
                        buffer.start_selection(selection_type=SelectionType.LINES)
                        buffer.cursor_position = end

                else:
                    # Don't handle scroll events here.
                    return NotImplemented

        # Not focused, but focusing on click events.
        else:
            if (
                self.focus_on_click()
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                # Focus happens on mouseup. (If we did this on mousedown, the
                # up event will be received at the point where this widget is
                # focused and be handled anyway.)
                get_app().layout.current_control = self
            else:
                return NotImplemented

        return None

    def move_cursor_down(self) -> None:
        b = self.buffer
        b.cursor_position += b.document.get_cursor_down_position()

    def move_cursor_up(self) -> None:
        b = self.buffer
        b.cursor_position += b.document.get_cursor_up_position()

    def move_cursor_right(self, count = 1) -> None:
        b = self.buffer
        b.cursor_position += count

    def move_cursor_left(self, count = 1) -> None:
        b = self.buffer
        b.cursor_position -= count


class VSplitWindow(Window):
    "修改的分块窗口，向上翻页时，下半部保持最后数据不变"
 
    def _copy_body(
        self,
        ui_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
        vertical_scroll: int = 0,
        horizontal_scroll: int = 0,
        wrap_lines: bool = False,
        highlight_lines: bool = False,
        vertical_scroll_2: int = 0,
        always_hide_cursor: bool = False,
        has_focus: bool = False,
        align: WindowAlign = WindowAlign.LEFT,
        get_line_prefix = None,
        isNotMargin = True,
    ):
        """
        Copy the UIContent into the output screen.
        Return (visible_line_to_row_col, rowcol_to_yx) tuple.

        :param get_line_prefix: None or a callable that takes a line number
            (int) and a wrap_count (int) and returns formatted text.
        """
        xpos = write_position.xpos + move_x
        ypos = write_position.ypos
        line_count = ui_content.line_count
        new_buffer = new_screen.data_buffer
        empty_char = _CHAR_CACHE["", ""]

        # Map visible line number to (row, col) of input.
        # 'col' will always be zero if line wrapping is off.
        visible_line_to_row_col: dict[int, tuple[int, int]] = {}

        # Maps (row, col) from the input to (y, x) screen coordinates.
        rowcol_to_yx: dict[tuple[int, int], tuple[int, int]] = {}

        def copy_line(
            line: StyleAndTextTuples,
            lineno: int,
            x: int,
            y: int,
            is_input: bool = False,
        ):
            """
            Copy over a single line to the output screen. This can wrap over
            multiple lines in the output. It will call the prefix (prompt)
            function before every line.
            """
            if is_input:
                current_rowcol_to_yx = rowcol_to_yx
            else:
                current_rowcol_to_yx = {}  # Throwaway dictionary.

            # Draw line prefix.
            if is_input and get_line_prefix:
                prompt = to_formatted_text(get_line_prefix(lineno, 0))
                x, y = copy_line(prompt, lineno, x, y, is_input=False)

            # Scroll horizontally.
            skipped = 0  # Characters skipped because of horizontal scrolling.
            if horizontal_scroll and is_input:
                h_scroll = horizontal_scroll
                line = explode_text_fragments(line)
                while h_scroll > 0 and line:
                    h_scroll -= get_cwidth(line[0][1])
                    skipped += 1
                    del line[:1]  # Remove first character.

                x -= h_scroll  # When scrolling over double width character,
                # this can end up being negative.

            # Align this line. (Note that this doesn't work well when we use
            # get_line_prefix and that function returns variable width prefixes.)
            if align == WindowAlign.CENTER:
                line_width = fragment_list_width(line)
                if line_width < width:
                    x += (width - line_width) // 2
            elif align == WindowAlign.RIGHT:
                line_width = fragment_list_width(line)
                if line_width < width:
                    x += width - line_width

            col = 0
            wrap_count = 0
            for style, text, *_ in line:
                new_buffer_row = new_buffer[y + ypos]

                # Remember raw VT escape sequences. (E.g. FinalTerm's
                # escape sequences.)
                if "[ZeroWidthEscape]" in style:
                    new_screen.zero_width_escapes[y + ypos][x + xpos] += text
                    continue

                for c in text:
                    char = _CHAR_CACHE[c, style]
                    char_width = char.width

                    # Wrap when the line width is exceeded.
                    if wrap_lines and x + char_width > width:
                        visible_line_to_row_col[y + 1] = (
                            lineno,
                            visible_line_to_row_col[y][1] + x,
                        )
                        y += 1
                        wrap_count += 1
                        x = 0

                        # Insert line prefix (continuation prompt).
                        if is_input and get_line_prefix:
                            prompt = to_formatted_text(
                                get_line_prefix(lineno, wrap_count)
                            )
                            x, y = copy_line(prompt, lineno, x, y, is_input=False)

                        new_buffer_row = new_buffer[y + ypos]

                        if y >= write_position.height:
                            return x, y  # Break out of all for loops.

                    # Set character in screen and shift 'x'.
                    if x >= 0 and y >= 0 and x < width:
                        new_buffer_row[x + xpos] = char

                        # When we print a multi width character, make sure
                        # to erase the neighbours positions in the screen.
                        # (The empty string if different from everything,
                        # so next redraw this cell will repaint anyway.)
                        if char_width > 1:
                            for i in range(1, char_width):
                                new_buffer_row[x + xpos + i] = empty_char

                        # If this is a zero width characters, then it's
                        # probably part of a decomposed unicode character.
                        # See: https://en.wikipedia.org/wiki/Unicode_equivalence
                        # Merge it in the previous cell.
                        elif char_width == 0:
                            # Handle all character widths. If the previous
                            # character is a multiwidth character, then
                            # merge it two positions back.
                            for pw in [2, 1]:  # Previous character width.
                                if (
                                    x - pw >= 0
                                    and new_buffer_row[x + xpos - pw].width == pw
                                ):
                                    prev_char = new_buffer_row[x + xpos - pw]
                                    char2 = _CHAR_CACHE[
                                        prev_char.char + c, prev_char.style
                                    ]
                                    new_buffer_row[x + xpos - pw] = char2

                        # Keep track of write position for each character.
                        current_rowcol_to_yx[lineno, col + skipped] = (
                            y + ypos,
                            x + xpos,
                        )

                    col += 1
                    x += char_width
            return x, y

        # Copy content.
        def copy() -> int:
            y = -vertical_scroll_2        
            lineno = vertical_scroll
            
            total = write_position.height
            upper = (total - 1) // 2
            below = total - upper - 1
            
            if lineno + total < line_count:
                if isinstance(self.content, SessionBufferControl):
                    b = self.content.buffer
                    b.split = True

                while y < upper and lineno < line_count:
                    line = ui_content.get_line(lineno)
                    visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                    x = 0
                    x, y = copy_line(line, lineno, x, y, is_input=True)
                    lineno += 1
                    y += 1

                x = 0
                x, y = copy_line([("","-"*width)], lineno, x, y, is_input=False)
                y += 1

                lineno = line_count - below
                while y < total and lineno < line_count:
                    line = ui_content.get_line(lineno)
                    visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                    x = 0
                    x, y = copy_line(line, lineno, x, y, is_input=True)
                    lineno += 1
                    y += 1

                return y
                
            else:
                if isNotMargin and isinstance(self.content, SessionBufferControl):
                    b = self.content.buffer
                    b.split = False

                while y < write_position.height and lineno < line_count:
                    # Take the next line and copy it in the real screen.
                    line = ui_content.get_line(lineno)

                    visible_line_to_row_col[y] = (lineno, horizontal_scroll)

                    # Copy margin and actual line.
                    x = 0
                    x, y = copy_line(line, lineno, x, y, is_input=True)

                    lineno += 1
                    y += 1
                return y
        
            

        copy()

        def cursor_pos_to_screen_pos(row: int, col: int) -> Point:
            "Translate row/col from UIContent to real Screen coordinates."
            try:
                y, x = rowcol_to_yx[row, col]
            except KeyError:
                # Normally this should never happen. (It is a bug, if it happens.)
                # But to be sure, return (0, 0)
                return Point(x=0, y=0)

                # raise ValueError(
                #     'Invalid position. row=%r col=%r, vertical_scroll=%r, '
                #     'horizontal_scroll=%r, height=%r' %
                #     (row, col, vertical_scroll, horizontal_scroll, write_position.height))
            else:
                return Point(x=x, y=y)

        # Set cursor and menu positions.
        if ui_content.cursor_position:
            screen_cursor_position = cursor_pos_to_screen_pos(
                ui_content.cursor_position.y, ui_content.cursor_position.x
            )

            if has_focus:
                new_screen.set_cursor_position(self, screen_cursor_position)

                if always_hide_cursor:
                    new_screen.show_cursor = False
                else:
                    new_screen.show_cursor = ui_content.show_cursor

                self._highlight_digraph(new_screen)

            if highlight_lines:
                self._highlight_cursorlines(
                    new_screen,
                    screen_cursor_position,
                    xpos,
                    ypos,
                    width,
                    write_position.height,
                )

        # Draw input characters from the input processor queue.
        if has_focus and ui_content.cursor_position:
            self._show_key_processor_key_buffer(new_screen)

        # Set menu position.
        if ui_content.menu_position:
            new_screen.set_menu_position(
                self,
                cursor_pos_to_screen_pos(
                    ui_content.menu_position.y, ui_content.menu_position.x
                ),
            )

        # Update output screen height.
        new_screen.height = max(new_screen.height, ypos + write_position.height)

        return visible_line_to_row_col, rowcol_to_yx

    def _copy_margin(
        self,
        margin_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
    ) -> None:
        """
        Copy characters from the margin screen to the real screen.
        """
        xpos = write_position.xpos + move_x
        ypos = write_position.ypos

        margin_write_position = WritePosition(xpos, ypos, width, write_position.height)
        self._copy_body(margin_content, new_screen, margin_write_position, 0, width, isNotMargin=False)

    def _scroll_down(self) -> None:
        "向下滚屏，处理屏幕分隔"
        info = self.render_info

        if info is None:
            return

        if isinstance(self.content, SessionBufferControl):
            b = self.content.buffer
            d = b.document

            b.exit_selection()
            cur_line = d.cursor_position_row
            
            # # 向下滚动时，如果存在自动折行情况，要判断本行被折成了几行，在行内时要逐行移动（此处未调试好）
            # cur_col  = d.cursor_position_col
            # line = d.current_line
            # line_width = len(line)
            # line_start = d.translate_row_col_to_index(cur_line, 0)
            # screen_width = info.window_width

            # offset_y = cur_col // screen_width
            # wraplines = math.ceil(1.0 * line_width / screen_width)

            if cur_line < info.content_height:
                
                # if offset_y < wraplines:                                    # add
                #     self.content.move_cursor_right(screen_width)            # add
                # else:                                                       # add

                self.content.move_cursor_down()
                self.vertical_scroll = cur_line + 1

            firstline = d.line_count - len(info.displayed_lines)
            if cur_line >= firstline:
                b.cursor_position = len(b.text)

    def _scroll_up(self) -> None:
        "向上滚屏，处理屏幕分隔"
        info = self.render_info

        if info is None:
            return

        #if info.cursor_position.y >= 1:
        if isinstance(self.content, SessionBufferControl):
            b = self.content.buffer
            d = b.document

            b.exit_selection()
            cur_line = d.cursor_position_row
            if cur_line > d.line_count - len(info.displayed_lines):
                firstline = d.line_count - len(info.displayed_lines)
                newpos = d.translate_row_col_to_index(firstline, 0)
                b.cursor_position = newpos
                cur_line = d.cursor_position_row
                self.vertical_scroll = cur_line

            elif cur_line > 0:
                self.content.move_cursor_up()
                self.vertical_scroll = cur_line - 1


class EasternButton(Button):
    "解决增加中文等东亚全宽字符后不对齐问题"

    def _get_text_fragments(self) -> StyleAndTextTuples:
        # 主要改动在这里
        width = self.width - (
            get_cwidth(self.left_symbol) + get_cwidth(self.right_symbol)
        ) - (get_cwidth(self.text) - len(self.text))


        text = (f"{{:^{width}}}").format(self.text)

        def handler(mouse_event: MouseEvent) -> None:
            if (
                self.handler is not None
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                self.handler()

        return [
            ("class:button.arrow", self.left_symbol, handler),
            #("[SetCursorPosition]", ""),
            ("class:button.text", text, handler),
            ("class:button.arrow", self.right_symbol, handler),
        ]

class EasternMenuContainer(MenuContainer):
    "解决增加中文等东亚全宽字符后不对齐问题"

    def _submenu(self, level: int = 0) -> Window:
        def get_text_fragments() -> StyleAndTextTuples:
            result: StyleAndTextTuples = []
            if level < len(self.selected_menu):
                menu = self._get_menu(level)
                if menu.children:
                    result.append(("class:menu", Border.TOP_LEFT))
                    result.append(("class:menu", Border.HORIZONTAL * (menu.width + 4)))
                    result.append(("class:menu", Border.TOP_RIGHT))
                    result.append(("", "\n"))
                    try:
                        selected_item = self.selected_menu[level + 1]
                    except IndexError:
                        selected_item = -1

                    def one_item(
                        i: int, item: MenuItem
                    ) -> Iterable[OneStyleAndTextTuple]:
                        def mouse_handler(mouse_event: MouseEvent) -> None:
                            if item.disabled:
                                # The arrow keys can't interact with menu items that are disabled.
                                # The mouse shouldn't be able to either.
                                return
                            hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
                            if (
                                mouse_event.event_type == MouseEventType.MOUSE_UP
                                or hover
                            ):
                                app = get_app()
                                if not hover and item.handler:
                                    app.layout.focus_last()
                                    item.handler()
                                else:
                                    self.selected_menu = self.selected_menu[
                                        : level + 1
                                    ] + [i]

                        if i == selected_item:
                            yield ("[SetCursorPosition]", "")
                            style = "class:menu-bar.selected-item"
                        else:
                            style = ""

                        yield ("class:menu", Border.VERTICAL)
                        if item.text == "-":
                            yield (
                                style + "class:menu-border",
                                f"{Border.HORIZONTAL * (menu.width + 3)}",
                                mouse_handler,
                            )
                        else:
                            # 主要改动在这里，其他地方都未更改.
                            adj_width = menu.width + 3 - (get_cwidth(item.text) - len(item.text))
                            yield (
                                style,
                                f" {item.text}".ljust(adj_width),
                                mouse_handler,
                            )

                        if item.children:
                            yield (style, ">", mouse_handler)
                        else:
                            yield (style, " ", mouse_handler)

                        if i == selected_item:
                            yield ("[SetMenuPosition]", "")
                        yield ("class:menu", Border.VERTICAL)

                        yield ("", "\n")

                    for i, item in enumerate(menu.children):
                        result.extend(one_item(i, item))

                    result.append(("class:menu", Border.BOTTOM_LEFT))
                    result.append(("class:menu", Border.HORIZONTAL * (menu.width + 4)))
                    result.append(("class:menu", Border.BOTTOM_RIGHT))
            return result

        return Window(FormattedTextControl(get_text_fragments), style="class:menu")



class MenuItem:
    def __init__(
        self,
        text: str = "",
        handler = None,
        children = None,
        shortcut = None,
        disabled: bool = False,
    ) -> None:
        self.text = text
        self.handler = handler
        self.children = children or []
        self.shortcut = shortcut
        self.disabled = disabled
        self.selected_item = 0

    @property
    def width(self) -> int:
        if self.children:
            return max(get_cwidth(c.text) for c in self.children)
        else:
            return 0


class DotDict(dict):
    """
    可以通过点.访问内部key-value对的字典。此类型继承自dict。

    - 由于继承关系，此类型可以使用所有dict可以使用的方法
    - 额外增加的点.访问方法使用示例如下

    示例:
        .. code:: Python

            mydict = DotDict()
            
            # 以下写内容访问等价
            mydict["key1"] = "value1"
            mydict.key1 = "value1"

            # 以下读访问等价
            val = mydict["key1"]
            val = mydict.key1
    """

    def __getattr__(self, __key):
        if (not __key in self.__dict__) and (not __key.startswith("__")):
            return self.__getitem__(__key)

    def __setattr__(self, __name: str, __value):
        if __name in self.__dict__:
            object.__setattr__(self, __name, __value)
        else:
            self.__setitem__(__name, __value)

    def __getstate__(self):
        return self
    
    def __setstate__(self, state):
        self.update(state)


        