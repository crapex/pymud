# External Libraries
import asyncio
import linecache
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple
from unicodedata import east_asian_width

from prompt_toolkit import ANSI
from prompt_toolkit.application import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
    to_formatted_text,
)
from prompt_toolkit.formatted_text.base import OneStyleAndTextTuple
from prompt_toolkit.formatted_text.utils import (
    fragment_list_width,
)
from prompt_toolkit.layout.containers import (
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import (
    FormattedTextControl,
    UIContent,
    UIControl,
)
from prompt_toolkit.layout.screen import _CHAR_CACHE, Screen, WritePosition
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import Button, MenuContainer, MenuItem
from prompt_toolkit.widgets.base import Border
from wcwidth import wcswidth, wcwidth

from .settings import Settings


class VSplitWindow(Window):
    "修改的分块窗口，向上翻页时，下半部保持最后数据不变"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 增加一个属性，记录分割偏移量
        self.split_offset = 0

    def move_split(self, offset: int):
        self.split_offset += offset

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
        get_line_prefix=None,
        isNotMargin=True,
    ):
        """
        Copy the UIContent into the output screen.
        Return (visible_line_to_row_col, rowcol_to_yx) tuple.

        :param get_line_prefix: None or a callable that takes a line number
            (int) and a wrap_count (int) and returns formatted text.
        """
        xpos = write_position.xpos + move_x
        ypos = write_position.ypos
        # line_count = ui_content.line_count
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

            # 防止没有 ratio 参数，或者被配置为不合适的值
            ratio = Settings.client.get("split_ratio", 0.5)
            if ratio < 0.15 or ratio > 0.85:
                ratio = 0.5

            upper = int(total * ratio) - 1
            # 上下各最少保留3行内容
            if self.split_offset < 2 - 1 * upper:
                self.split_offset = 2 - 1 * upper

            elif self.split_offset > total - upper - 5:
                self.split_offset = total - upper - 5

            upper = upper + self.split_offset

            if isinstance(self.content, PyMudBufferControl):
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
                            display_lines = ui_content.get_height_for_line(
                                lineno, width, None
                            )
                            y -= display_lines
                            line = ui_content.get_line(lineno)
                            visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                            copy_line(line, lineno, 0, y, is_input=True)

                else:
                    # 有split window

                    # 先复制下半部分，倒序复制，确保即使有自动折行时，最后一行也保持在屏幕最底部
                    y = total
                    lineno = line_count

                    while y > upper and lineno >= 0:
                        lineno -= 1
                        # Take the next line and copy it in the real screen.
                        display_lines = ui_content.get_height_for_line(
                            lineno, width, None
                        )
                        y -= display_lines
                        if y <= upper:
                            break
                        line = ui_content.get_line(lineno)
                        visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                        copy_line(line, lineno, 0, y, is_input=True)

                    # 复制上半部分，正序复制，确保即使有自动折行时，第一行也保持在屏幕最顶部
                    y = -vertical_scroll_2
                    lineno = start_lineno
                    while y <= upper and lineno < line_count:
                        line = ui_content.get_line(lineno)
                        visible_line_to_row_col[y] = (lineno, horizontal_scroll)
                        x = 0
                        x, y = copy_line(line, lineno, x, y, is_input=True)
                        lineno += 1
                        y += 1

                    # 最后复制分割线，若上下有由于折行额外占用的内容，都用分割线给覆盖掉
                    copy_line([("", "-" * width)], -1, 0, upper + 1, is_input=False)

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

        if isinstance(self.content, PyMudBufferControl):
            b = self.content.buffer
            if not b:
                return
            start_lineno = b.start_lineno
            if (start_lineno >= 0) and (
                start_lineno < b.lineCount - (info.window_height - 1) // 2
            ):
                b.start_lineno = b.start_lineno + 1
            else:
                b.start_lineno = -1

    def _scroll_up(self) -> None:
        "向上滚屏，处理屏幕分隔"
        info = self.render_info

        if info is None:
            return

        if isinstance(self.content, PyMudBufferControl):
            b = self.content.buffer
            if not b:
                return
            start_lineno = b.start_lineno
            if start_lineno > 0:
                b.start_lineno = b.start_lineno - 1

            elif start_lineno == 0:
                b.start_lineno = 0

            elif b.start_lineno < 0 and b.lineCount >= info.window_height:
                b.start_lineno = b.lineCount - (info.window_height - 1) // 2


class EasternButton(Button):
    "解决增加中文等东亚全宽字符后不对齐问题"

    def _get_text_fragments(self) -> StyleAndTextTuples:
        # 主要改动在这里
        width = (
            self.width
            - (get_cwidth(self.left_symbol) + get_cwidth(self.right_symbol))
            - (get_cwidth(self.text) - len(self.text))
        )

        text = (f"{{:^{width}}}").format(self.text)

        def handler(mouse_event: MouseEvent) -> None:
            if (
                self.handler is not None
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                self.handler()

        return [
            ("class:button.arrow", self.left_symbol, handler),
            # ("[SetCursorPosition]", ""),
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
                            # adj_width = menu.width + 3 - (get_cwidth(item.text) - len(item.text))
                            yield (
                                style,
                                DStr(f" {item.text}").ljust(menu.width + 3),
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
        return (
            (self.start_row >= 0)
            and (self.start_col >= 0)
            and (self.end_row >= 0)
            and (self.end_col >= 0)
            and abs(self.start_row - self.end_row) + abs(self.start_col - self.end_col)
            > 0
        )

    @property
    def rows(self):
        if self.is_valid():
            return abs(self.end_row - self.start_row) + 1
        else:
            return 0

    @property
    def actual_start_row(self):
        if self.is_valid():
            if self.start_row <= self.end_row:
                return self.start_row
            else:
                return self.end_row

        return -1

    @property
    def actual_start_col(self):
        if self.is_valid():
            if self.start_row <= self.end_row:
                return self.start_col
            else:
                return self.end_col

        return -1

    @property
    def actual_end_row(self):
        if self.is_valid():
            if self.start_row <= self.end_row:
                return self.end_row
            else:
                return self.start_row

        return -1

    @property
    def actual_end_col(self):
        if self.is_valid():
            if self.start_row <= self.end_row:
                return self.end_col
            else:
                return self.start_col

        return -1


class BufferBase:
    def __init__(self, name, newline="\n", max_buffered_lines=10000) -> None:
        self.name = name
        self.newline = newline
        self.max_buffered_lines = max_buffered_lines
        self._start_lineno = -1
        self.selection = SessionSelectionState(-1, -1, -1, -1)

        self.mouse_point = Point(-1, -1)

    def clear(self):
        pass

    @property
    def start_lineno(self):
        return self._start_lineno

    @start_lineno.setter
    def start_lineno(self, value: int):
        self._start_lineno = value

    @property
    def lineCount(self) -> int:
        return 0

    def getLine(self, lineno: int) -> str:
        return ""

    # 获取指定某行到某行的内容。当start未设置时，从首行开始。当end未设置时，到最后一行结束。
    # 注意判断首位顺序逻辑，以及给定参数是否越界
    def selection_range_at_line(self, lineno: int) -> Optional[Tuple[int, int]]:
        if self.selection.is_valid():
            if self.selection.rows > 1:
                if lineno == self.selection.actual_start_row:
                    return (self.selection.actual_start_col, len(self.getLine(lineno)))
                elif lineno == self.selection.actual_end_row:
                    return (0, self.selection.actual_end_col)
                elif (
                    lineno > self.selection.actual_start_row
                    and lineno < self.selection.actual_end_row
                ):
                    return (0, len(self.getLine(lineno)))

            elif self.selection.rows == 1:
                if lineno == self.selection.start_row:
                    return (self.selection.start_col, self.selection.end_col)

        return None

    def exit_selection(self):
        self.selection = SessionSelectionState(-1, -1, -1, -1)

    def nosplit(self):
        self.start_lineno = -1
        get_app().invalidate()


class SessionBuffer(BufferBase):
    BUF_A = 0
    BUF_B = 1
    BUF_C = 2

    def __init__(
        self,
        name,
        newline="\n",
        max_buffered_lines=2000,
    ) -> None:
        super().__init__(name, newline, max_buffered_lines)
        self.BUFFER_SIZE = max_buffered_lines
        self._buf = [""] * self.BUFFER_SIZE
        self.CACHE_BUFFER_SIZE = max_buffered_lines // 2
        if self.CACHE_BUFFER_SIZE < 500:
            self.CACHE_BUFFER_SIZE = 500
        elif self.CACHE_BUFFER_SIZE > 1000:
            self.CACHE_BUFFER_SIZE = 1000
        self._bufC = [""] * self.CACHE_BUFFER_SIZE

        self.clear()

    def clear(self):
        self._c_count = 0
        self._count = 0
        self._startIndex = 0
        self._cursorIndex = 0
        self._endInCache = False
        self._endIndex = 0

        self._hold = False
        self._isnewline = True

        if len(self._bufC) > self.CACHE_BUFFER_SIZE:
            del self._bufC[self.CACHE_BUFFER_SIZE :]

    @BufferBase.start_lineno.setter
    def start_lineno(self, value: int):
        self._start_lineno = value
        if (value < 0) and self._hold:
            self.hold = False
        elif (value >= 0) and not self._hold:
            self.hold = True

    @property
    def hold(self) -> bool:
        return self._hold or (self._start_lineno >= 0)

    @hold.setter
    def hold(self, value: bool):
        if self._hold != value:
            if not value and self._c_count > 0:
                if self._c_count < self.BUFFER_SIZE:
                    copystart = 0
                    copyend = self._c_count
                else:
                    copystart = self._c_count - self.BUFFER_SIZE
                    copyend = self._c_count
                savedNewline = self._isnewline
                self._isnewline = True
                self._endInCache = False
                self._endIndex = self._startIndex
                self._cursorIndex = self._startIndex
                self._count = self.BUFFER_SIZE
                for lineno in range(copystart, copyend):
                    self._appendLineNormal(self._bufC[lineno], True)
                self._isnewline = savedNewline
                self._c_count = 0
                if len(self._bufC) > self.CACHE_BUFFER_SIZE:
                    del self._bufC[self.CACHE_BUFFER_SIZE :]

            self._hold = value

    def _appendLineNormal(self, line: str, newline: bool = True):
        if not self._isnewline:
            if self._endInCache:
                self._bufC[self._endIndex] += line
            else:
                self._buf[self._endIndex] += line
        else:
            self._buf[self._cursorIndex] = line
            self._endInCache = False
            self._endIndex = self._cursorIndex
            self._cursorIndex = (self._cursorIndex + 1) % self.BUFFER_SIZE
            if self._count == self.BUFFER_SIZE:
                self._startIndex = (self._startIndex + 1) % self.BUFFER_SIZE
            elif self._count < self.BUFFER_SIZE:
                self._count += 1
            else:
                raise Exception("count out of range.")
        self._isnewline = newline

    def _appendLineHold(self, line: str, newline: bool = True):
        if not self._isnewline:
            if self._endInCache:
                self._bufC[self._endIndex] += line
            else:
                self._buf[self._endIndex] += line
        else:
            if self._count < self.BUFFER_SIZE:
                self._appendLineNormal(line, newline)
            elif self._count >= self.BUFFER_SIZE:
                if self._c_count < self.CACHE_BUFFER_SIZE:
                    self._bufC[self._c_count] = line
                else:
                    self._bufC.append(line)
                self._c_count += 1
                self._count += 1
                self._endInCache = True
                self._endIndex = self._c_count - 1
        self._isnewline = newline

    def _appendLine(self, line: str, newline: bool = True):
        if self._hold:
            self._appendLineHold(line, newline)
        else:
            self._appendLineNormal(line, newline)

    def append(self, line: str):
        newline_after_append = False
        if line.endswith(self.newline):
            line = line.rstrip(self.newline)
            newline_after_append = True

        if self.newline not in line:
            self._appendLine(line, newline_after_append)

        else:
            lines = line.split(self.newline)
            for line in lines[:-1]:
                self._appendLine(line, True)

            self._appendLine(lines[-1], newline_after_append)
        get_app().invalidate()

    @property
    def lineCount(self) -> int:
        return self._count

    def getLine(self, lineno: int) -> str:
        if self._count == 0:
            return ""

        if lineno < 0 or lineno >= self._count:
            lineno = lineno % self._count

        if lineno < self.BUFFER_SIZE:
            idx = (self._startIndex + lineno) % self.BUFFER_SIZE
            line = self._buf[idx]
        else:
            line = self._bufC[lineno - self.BUFFER_SIZE]

        return line

    def forceNewline(self):
        self._isnewline = True


class LogFileBuffer(BufferBase):
    def __init__(
        self,
        name,
        filepath: Optional[str] = None,
    ) -> None:
        super().__init__(name)
        self._lines: Dict[int, str] = {}
        self.loadfile(filepath)

    def loadfile(self, filepath: Optional[str] = None):
        if filepath and os.path.exists(filepath):
            self.filepath = filepath
        else:
            self.filepath = None

    def clear(self):
        self.filepath = None

    @property
    def lineCount(self):
        if not self.filepath or not os.path.exists(self.filepath):
            return 0

        with open(self.filepath, "r", encoding="utf-8", errors="ignore") as fp:
            return sum(1 for _ in fp)

    def getLine(self, lineno: int):
        if not self.filepath or not os.path.exists(self.filepath):
            return ""

        return linecache.getline(self.filepath, lineno).rstrip(self.newline)

    def __del__(self):
        self._lines.clear()


class PyMudBufferControl(UIControl):
    def __init__(self, buffer: Optional[BufferBase]) -> None:
        self.buffer = buffer

        # 为MUD显示进行校正的处理，包括对齐校正，换行颜色校正等
        self.FULL_BLOCKS = set("▂▃▅▆▇▄█")
        self.TABLE_LINES = set("┃││║┃")
        self.SINGLE_LINES = set("┠┌└├┬┼┴╭╰─")
        self.SINGLE_LINES_LEFT = set("┨┘┐┤╮╯")
        self.DOUBLE_LINES = set("╔╚╠╦╪╩═")
        self.DOUBLE_LINES_LEFT = set("╗╝╣")
        self.THICK_LINES = set("┏┗━")
        self.THICK_LINES_LEFT = set("┓┛ ")
        self.ALL_COLOR_REGX = re.compile(r"(?:\[[\d;]+m)+")
        self.AVAI_COLOR_REGX = re.compile(r"(?:\[[\d;]+m)+(?!$)")
        self._color_start = ""
        self._color_correction = False
        self._color_line_index = 0

        self._last_click_timestamp = 0

    def reset(self) -> None:
        # Default reset. (Doesn't have to be implemented.)
        pass

    def preferred_width(self, max_available_width: int) -> Optional[int]:
        return None

    def is_focusable(self) -> bool:
        """
        Tell whether this user control is focusable.
        """
        return False

    def width_correction(self, line: str) -> str:
        new_str = []
        for idx, ch in enumerate(line):
            if (east_asian_width(ch) in "FWA") and (wcwidth(ch) == 1):
                if ch in self.FULL_BLOCKS:
                    new_str.append(ch)
                    new_str.append(ch)
                elif ch in self.SINGLE_LINES:
                    new_str.append(ch)
                    new_str.append("─")
                elif ch in self.DOUBLE_LINES:
                    new_str.append(ch)
                    new_str.append("═")
                elif ch in self.THICK_LINES:
                    new_str.append(ch)
                    new_str.append("━")
                else:
                    new_str.append(ch)
                    new_str.append(" ")

                # 恢复为统一右侧添加补充显示字符，以下为往左添加字符的代码，暂保留注释
                # else:
                #     right = str.rstrip(line[idx+1:])
                #     right_len = fragment_list_width(to_formatted_text(ANSI(right)))
                #     if (idx == len(line) - 1) or (right_len == 0):
                #         if ch in self.SINGLE_LINES_LEFT:
                #             new_str.append("─")
                #             new_str.append(ch)
                #         elif ch in self.DOUBLE_LINES_LEFT:
                #             new_str.append("═")
                #             new_str.append(ch)
                #         elif ch in self.THICK_LINES_LEFT:
                #             new_str.append("━")
                #             new_str.append(ch)
                #         elif ch in self.TABLE_LINES:
                #             new_str.append(" ")
                #             new_str.append(ch)
                #         else:
                #             new_str.append(ch)
                #             new_str.append(' ')
                #     else:
                #         new_str.append(ch)
                #         new_str.append(' ')
            else:
                new_str.append(ch)

        return "".join(new_str)

    def return_correction(self, line: str):
        return line.replace("\r", "").replace("\x00", "")

    def tab_correction(self, line: str):
        from .session import Session

        while "\t" in line:
            tab_index = line.find("\t")
            left, right = line[:tab_index], line[tab_index + 1 :]
            left_width = get_cwidth(Session.PLAIN_TEXT_REGX.sub("", left))
            tab_width = Settings.client["tabstop"] - (
                left_width % Settings.client["tabstop"]
            )
            line = left + " " * tab_width + right

        return line

    def line_correction(self, line: str):
        # 处理\r符号（^M）
        line = self.return_correction(line)

        # 美化（解决中文英文在Console中不对齐的问题）
        if Settings.client["beautify"]:
            line = self.width_correction(line)

        # 处理Tab(\r)符号（^I）对齐
        line = self.tab_correction(line)

        line += " "  # 最后添加一个空格，用于允许选择行时选到最后一个字符

        return line

    def create_content(self, width: int, height: int) -> UIContent:
        """
        Generate the content for this user control.

        Returns a :class:`.UIContent` instance.
        """
        buffer = self.buffer
        if not buffer:
            return UIContent(get_line=lambda i: [], line_count=0, cursor_position=None)

        def get_line(i: int) -> StyleAndTextTuples:
            line = buffer.getLine(i)
            # 颜色校正
            SEARCH_LINES = 50
            thislinecolors = len(self.AVAI_COLOR_REGX.findall(line))
            if thislinecolors == 0:
                lineno = i - 1
                search = 0
                while lineno >= 0 and search < SEARCH_LINES:
                    search += 1

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
            # line = self.return_correction(line)

            # 处理ANSI标记（生成FormmatedText）
            fragments = to_formatted_text(ANSI(line))
            # fragments = explode_text_fragments(fragments)

            # if Settings.client["beautify"]:
            #     fragments = self.fragment_correction(fragments)

            # 选择内容标识
            selected_fragment = " class:selected "

            # In case of selection, highlight all matches.
            selection_at_line = buffer.selection_range_at_line(i)

            if selection_at_line:
                from_, to = selection_at_line
                total_display = fragment_list_width(fragments)
                if to == len(buffer.getLine(i)):
                    to = total_display

                fragments = explode_text_fragments(fragments)

                if from_ == 0 and to == 0 and len(fragments) == 0:
                    # When this is an empty line, insert a space in order to
                    # visualize the selection.
                    return [(selected_fragment, " ")]
                else:
                    for i in range(from_, min(to, total_display + 1)):
                        if i < len(fragments):
                            old_fragment, old_text, *_ = fragments[i]
                            fragments[i] = (old_fragment + selected_fragment, old_text)
                        # elif i == len(fragments):
                        #     fragments.append((selected_fragment, " "))

            return fragments

        content = UIContent(
            get_line=get_line, line_count=buffer.lineCount, cursor_position=None
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
                buffer.mouse_point = position
                if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                    buffer.exit_selection()
                    buffer.selection.start_row = position.y
                    buffer.selection.start_col = position.x

                elif (
                    mouse_event.event_type == MouseEventType.MOUSE_MOVE
                    and mouse_event.button == MouseButton.LEFT
                ):
                    # Click and drag to highlight a selection
                    if buffer.selection.start_row >= 0 and not (
                        position.y == 0 and position.x == 0
                    ):
                        buffer.selection.end_row = position.y
                        buffer.selection.end_col = position.x

                elif mouse_event.event_type == MouseEventType.MOUSE_UP:
                    # When the cursor was moved to another place, select the text.
                    # (The >1 is actually a small but acceptable workaround for
                    # selecting text in Vi navigation mode. In navigation mode,
                    # the cursor can never be after the text, so the cursor
                    # will be repositioned automatically.)

                    if buffer.selection.start_row >= 0 and position.y >= 0:
                        buffer.selection.end_row = position.y
                        buffer.selection.end_col = position.x

                    if not buffer.selection.is_valid():
                        buffer.exit_selection()

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
        if (__key not in self.__dict__) and (not __key.startswith("__")):
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


# 构建一个DStr类型，替代str类型进行显示对齐操作。该类型在str的基础上，len方法返回其显示宽度，ljust/rjust/center均以显示宽度返回对齐的字符串。


class DStr(str):
    """增强的字符串类型，使用显示宽度进行对齐操作"""

    def __len__(self):
        """返回字符串的显示宽度，而不是字符数量"""
        return wcswidth(self.__str__())

    def ljust(self, width, fillchar=" "):
        """左对齐字符串，使用显示宽度进行计算"""
        display_len = len(self)  # 使用重写的len方法获取显示宽度
        if display_len >= width:
            return self
        return self + fillchar * (width - display_len)

    def rjust(self, width, fillchar=" "):
        """右对齐字符串，使用显示宽度进行计算"""
        display_len = len(self)  # 使用重写的len方法获取显示宽度
        if display_len >= width:
            return self
        return fillchar * (width - display_len) + self

    def center(self, width, fillchar=" "):
        """居中对齐字符串，使用显示宽度进行计算"""
        display_len = len(self)  # 使用重写的len方法获取显示宽度
        if display_len >= width:
            return self
        spaces = width - display_len
        left = spaces // 2
        right = spaces - left
        return fillchar * left + self + fillchar * right


# 创建一个awaitable对象，既支持像asyncio.Event那样可以set/clear重复使用，也支持像asyncio.Future那样可以带返回值。
class ValuedEvent:
    """
    一个可等待对象，结合了asyncio.Event和asyncio.Future的特性。
    支持set/clear重复使用，也可以设置返回值。
    """

    def __init__(self, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._future = asyncio.Future(loop=self._loop)
        self._value = None
        self._set = False

    def __await__(self):
        return self._future.__await__()

    def set(self, value=None):
        """设置事件为已触发状态，并可选地设置返回值。"""
        self._value = value
        self._set = True
        if not self._future.done():
            self._future.set_result(value)

    def clear(self):
        """重置事件为未触发状态，以便再次使用。"""
        if self._future.done():
            self._future = asyncio.Future(loop=self._loop)
        self._set = False
        self._value = None

    def is_set(self):
        """检查事件是否已被触发。"""
        return self._set

    def result(self):
        """获取设置的结果值。如果尚未设置，则抛出异常。"""
        return self._future.result()

    def exception(self):
        """获取异常（如果有）。"""
        return self._future.exception()

    def set_exception(self, exc):
        """设置异常。"""
        if not self._future.done():
            self._future.set_exception(exc)
        self._set = True

    def cancel(self):
        """取消等待。"""
        return self._future.cancel()

    def cancelled(self):
        """检查是否已取消。"""
        return self._future.cancelled()

    async def wait(self):
        """
        等待事件被设置，类似于asyncio.Event.wait方法。
        如果事件已设置，立即返回结果值；否则等待直到事件被设置。

        返回值：
            设置的结果值，如果事件已被取消则抛出CancelledError。
        """
        if self.is_set() and not self._future.done():
            # 如果事件已设置但future尚未完成，手动完成它
            self._future.set_result(self._value)
        return await self._future
