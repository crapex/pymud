# External Libraries
from unicodedata import east_asian_width
from wcwidth import wcwidth
from dataclasses import dataclass
import time, re, logging

from typing import Iterable, NamedTuple, Optional, Union, Tuple
from prompt_toolkit import ANSI
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import to_formatted_text, fragment_list_to_text
from prompt_toolkit.formatted_text.base import OneStyleAndTextTuple
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout.controls import UIContent, FormattedTextControl
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.selection import SelectionType
from prompt_toolkit.buffer import Buffer, ValidationState
from prompt_toolkit.utils import Event

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
            
            #if isNotMargin:
            if isinstance(self.content, SessionBufferControl):
                b = self.content.buffer
                if not b:
                    return y
                    
                line_count = b.lineCount
                start_lineno = b.start_lineno
                if start_lineno < 0:
                    # no split window
                    if line_count < total:
                        # 内容行数小于屏幕行数
                        lineno = 0

                        while y < total and lineno < line_count:
                            # Take the next line and copy it in the real screen.
                            line = ui_content.get_line(lineno)
                            visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                            x = 0
                            x, y = copy_line(line, lineno, x, y, is_input=True)
                            lineno += 1
                            y += 1

                    else:
                        # 若内容行数大于屏幕行数，则倒序复制，确保即使有自动折行时，最后一行也保持在屏幕最底部

                        y = total
                        lineno = line_count

                        while y >= 0 and lineno >= 0:
                            lineno -= 1
                            # Take the next line and copy it in the real screen.
                            display_lines = ui_content.get_height_for_line(lineno, width, None)
                            y -= display_lines
                            line = ui_content.get_line(lineno)
                            visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                            copy_line(line, lineno, 0, y, is_input=True)

                    
                else:
                    # 有split window
                    


                    # 先复制下半部分，倒序复制，确保即使有自动折行时，最后一行也保持在屏幕最底部
                    y = total
                    lineno = line_count

                    while y > below and lineno >= 0:
                        lineno -= 1
                        # Take the next line and copy it in the real screen.
                        display_lines = ui_content.get_height_for_line(lineno, width, None)
                        y -= display_lines
                        if y <= below:
                            break
                        line = ui_content.get_line(lineno)
                        visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                        copy_line(line, lineno, 0, y, is_input=True)

                    # 复制上半部分，正序复制，确保即使有自动折行时，第一行也保持在屏幕最顶部
                    y = -vertical_scroll_2
                    lineno = start_lineno
                    while y <= below and lineno < line_count:
                        line = ui_content.get_line(lineno)
                        visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                        x = 0
                        x, y = copy_line(line, lineno, x, y, is_input=True)
                        lineno += 1
                        y += 1

                    # 最后复制分割线，若上下有由于折行额外占用的内容，都用分割线给覆盖掉
                    copy_line([("","-"*width)], -1, 0, upper + 1, is_input=False)
                    
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

    def _scroll_down(self) -> None:
        "向下滚屏，处理屏幕分隔"
        info = self.render_info

        if info is None:
            return

        if isinstance(self.content, SessionBufferControl):
            b = self.content.buffer
            if not b:
                return
            start_lineno = b.start_lineno
            if (start_lineno >= 0) and (start_lineno < b.lineCount - len(info.displayed_lines)):
                b.start_lineno = b.start_lineno + 1
            else:
                b.start_lineno = -1

    def _scroll_up(self) -> None:
        "向上滚屏，处理屏幕分隔"
        info = self.render_info

        if info is None:
            return

        if isinstance(self.content, SessionBufferControl):
            b = self.content.buffer
            if not b:
                return
            start_lineno = b.start_lineno
            if start_lineno > 0:
                b.start_lineno = b.start_lineno - 1
                
            elif start_lineno == 0:
                b.start_lineno = 0

            else:
                b.start_lineno = b.lineCount - len(info.displayed_lines) - 1


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

@dataclass
class SessionSelectionState:
    start_row: int = -1
    end_row: int = -1
    start_col: int = -1
    end_col: int = -1
    def is_valid(self):
        if self.start_row >= 0 and self.end_row >= 0 and self.start_col >= 0 and self.end_col >= 0:
            if (self.start_row == self.end_row) and (self.start_col == self.end_col):
                return False
            elif self.start_row > self.end_row:
                srow, scol = self.end_row, self.end_col
                erow, ecol = self.start_row, self.start_col
                self.start_row, self.end_row = srow, erow
                self.start_col, self.end_col = scol, ecol
            elif self.start_row == self.end_row and self.start_col > self.end_col:
                scol, ecol = self.end_col, self.start_col
                self.start_col, self.end_col = scol, ecol

            return True

        return False

    @property
    def rows(self):
        if self.is_valid():
            return self.end_row - self.start_row + 1
        else:
            return 0
    

class SessionBuffer:
    def __init__(
        self, 
        name, 
        newline = "\n",
        max_buffered_lines = 10000,
        ) -> None:

        self.name = name
        self.lines = []
        self.newline = newline
        self.isnewline = True
        self.max_buffered_lines = max_buffered_lines
        self.selection = SessionSelectionState(-1, -1, -1, -1)
        self.start_lineno = -1

    def append(self, line: str):
        """
        追加文本到缓冲区。
        当文本以换行符结尾时，会自动添加到缓冲区。
        当文本不以换行符结尾时，会自动添加到上一行。
        """
        newline_after_append = False
        if line.endswith(self.newline):
            line = line.rstrip(self.newline)
            newline_after_append = True
        if not self.newline in line:
            if self.isnewline:
                self.lines.append(line)
            else:
                self.lines[-1] += line

        else:
            lines = line.split(self.newline)
            if self.isnewline:
                self.lines.extend(lines)
            else:
                self.lines[-1] += lines[0]
                self.lines.extend(lines[1:])

        self.isnewline = newline_after_append

        ## limit buffered lines
        if len(self.lines) > self.max_buffered_lines:
            diff = self.max_buffered_lines - len(self.lines)
            del self.lines[:diff]
            ## adjust selection
            if self.selection.start_row >= 0:
                self.selection.start_row -= diff
                self.selection.end_row -= diff

        get_app().invalidate()

    def clear(self):
        self.lines.clear()
        self.selection = SessionSelectionState(-1, -1, -1, -1)

        get_app().invalidate()

    def loadfile(self, filename, encoding = 'utf-8', errors = 'ignore'):
        with open(filename, 'r', encoding = encoding, errors = errors) as fp:
            lines = fp.readlines()
            self.clear()
            self.lines.extend(lines)

            get_app().invalidate()

    @property
    def lineCount(self):
        return len(self.lines)
        
    def getLine(self, lineno):
        if lineno < 0 or lineno >= len(self.lines):
            return ""
        return self.lines[lineno]

    # 获取指定某行到某行的内容。当start未设置时，从首行开始。当end未设置时，到最后一行结束。
    # 注意判断首位顺序逻辑，以及给定参数是否越界
    def getLines(self, start = None, end = None):
        if start is None:
            start = 0
        if end is None:
            end = len(self.lines) - 1
        if start < 0:
            start = 0
        if end >= len(self.lines):
            end = len(self.lines) - 1
        if start > end:
            return []
        return self.lines[start:end+1]

    def selection_range_at_line(self, lineno):
        if self.selection.is_valid():
            if self.selection.rows > 1:
                if lineno == self.selection.start_row:
                    return (self.selection.start_col, len(self.lines[lineno]) - 1)
                elif lineno == self.selection.end_row:
                    return (0, self.selection.end_col)
                elif lineno > self.selection.start_row and lineno < self.selection.end_row:
                    return (0, len(self.lines[lineno]) - 1)

            elif self.selection.rows == 1:
                if lineno == self.selection.start_row:
                    return (self.selection.start_col, self.selection.end_col)

        return None

    def exit_selection(self):
        self.selection = SessionSelectionState(-1, -1, -1, -1)

    def nosplit(self):
        self.start_lineno = -1
        get_app().invalidate()

class SessionBufferControl(UIControl):
    def __init__(self, buffer: Optional[SessionBuffer]) -> None:
        self.buffer = buffer

        # 为MUD显示进行校正的处理，包括对齐校正，换行颜色校正等
        self.FULL_BLOCKS = set("▂▃▅▆▇▄█")
        self.SINGLE_LINES = set("┌└├┬┼┴╭╰─")
        self.DOUBLE_LINES = set("╔╚╠╦╪╩═")
        self.ALL_COLOR_REGX  = re.compile(r"(?:\[[\d;]+m)+")
        self.AVAI_COLOR_REGX = re.compile(r"(?:\[[\d;]+m)+(?!$)")
        self._color_start = ""
        self._color_correction = False
        self._color_line_index = 0

        self._last_click_timestamp = 0

    def reset(self) -> None:
        # Default reset. (Doesn't have to be implemented.)
        pass

    def preferred_width(self, max_available_width: int) -> int | None:
        return None

    def is_focusable(self) -> bool:
        """
        Tell whether this user control is focusable.
        """
        return False


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

    def create_content(self, width: int, height: int) -> UIContent:
        """
        Generate the content for this user control.

        Returns a :class:`.UIContent` instance.
        """
        buffer = self.buffer
        if not buffer:
            return UIContent(
                get_line = lambda i: [],
                line_count = 0,
                cursor_position = None
            )

        def get_line(i: int) -> StyleAndTextTuples:
            line = buffer.getLine(i)
            # 颜色校正
            thislinecolors = len(self.AVAI_COLOR_REGX.findall(line))
            if thislinecolors == 0:
                lineno = i - 1
                while lineno >= 0:
                    lastline = buffer.getLine(lineno)
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

            # 选择内容标识
            selected_fragment = " class:selected "

            # In case of selection, highlight all matches.
            selection_at_line = buffer.selection_range_at_line(i)

            if selection_at_line:
                from_, to = selection_at_line
                # from_ = source_to_display(from_)
                # to = source_to_display(to)

                fragments = explode_text_fragments(fragments)

                if from_ == 0 and to == 0 and len(fragments) == 0:
                    # When this is an empty line, insert a space in order to
                    # visualize the selection.
                    return [(selected_fragment, " ")]
                else:
                    for i in range(from_, to):
                        if i < len(fragments):
                            old_fragment, old_text, *_ = fragments[i]
                            fragments[i] = (old_fragment + selected_fragment, old_text)
                        elif i == len(fragments):
                            fragments.append((selected_fragment, " "))

            return fragments

        content = UIContent(
            get_line = get_line,
            line_count = buffer.lineCount,
            cursor_position = None
        )

        return content

    def mouse_handler(self, mouse_event: MouseEvent):
        """
        Handle mouse events.

        When `NotImplemented` is returned, it means that the given event is not
        handled by the `UIControl` itself. The `Window` or key bindings can
        decide to handle this event as scrolling or changing focus.

        :param mouse_event: `MouseEvent` instance.
        """
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
        # 这里是修改的内容
        if (cur_control == self) or (cur_buffer and cur_buffer.name == "input"):

            if buffer:
                # Set the selection position.
                if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                    buffer.exit_selection()
                    buffer.selection.start_row = position.y
                    buffer.selection.start_col = position.x

                elif (
                    mouse_event.event_type == MouseEventType.MOUSE_MOVE
                    and mouse_event.button == MouseButton.LEFT
                ):
                    # Click and drag to highlight a selection
                    if buffer.selection.start_row >= 0:
                        buffer.selection.end_row = position.y
                        buffer.selection.end_col = position.x

                elif mouse_event.event_type == MouseEventType.MOUSE_UP:
                    # When the cursor was moved to another place, select the text.
                    # (The >1 is actually a small but acceptable workaround for
                    # selecting text in Vi navigation mode. In navigation mode,
                    # the cursor can never be after the text, so the cursor
                    # will be repositioned automatically.)
                    
                    if buffer.selection.start_row >= 0:
                        buffer.selection.end_row = position.y
                        buffer.selection.end_col = position.x

                        if buffer.selection.start_row == buffer.selection.end_row and buffer.selection.start_col == buffer.selection.end_col:
                            buffer.selection = SessionSelectionState(-1, -1, -1, -1)


                    # Select word around cursor on double click.
                    # Two MOUSE_UP events in a short timespan are considered a double click.
                    double_click = (
                        self._last_click_timestamp
                        and time.time() - self._last_click_timestamp < 0.3
                    )
                    self._last_click_timestamp = time.time()

                    if double_click:
                        buffer.selection.start_row = position.y
                        buffer.selection.start_col = 0
                        buffer.selection.end_row = position.y
                        buffer.selection.end_col = len(buffer.getLine(position.y))

                    get_app().layout.focus("input")

                else:
                    # Don't handle scroll events here.
                    return NotImplemented

        # Not focused, but focusing on click events.
        else:
                return NotImplemented

        return None

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


        