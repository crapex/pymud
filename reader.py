import logging
from asyncio import StreamReader, events, exceptions

# TELNET中的颜色定义
# 在TELNET协议中，颜色特殊定义都使用标志 CSI 开头， 以字母 m 结尾
# 颜色定义包括ANSI颜色、256颜色、24位色三种。
# CSI n m,      ANSI 颜色标志，以CSI开头，m结尾。中间的n为序号查表的ANSI颜色
# CSI 38;5;n m  256色前景颜色, 8bit
# CSI 48;5;n m  256色背景颜色
# CSI 38;2;r;g;b m 24位rgb颜色前景颜色
# CSI 48;2;r;g;b m 24位rgb颜色背景颜色

ESC = 0x1b
CSI = b"\x1b["          # TELNET COLORS CSI, Control Sequence Indicator
CSI_END = b"m"

class ANSI_COLOR:
    Reset = 0
    Bold  = 1
    Faint = 2
    Italic = 3
    Underline = 4
    SlowBlink = 5
    FastBlink = 6
    ReverseVideo = 7
    Erase = 8
    Strikethrough = 9
    DoubleUnderline = 21
    Bold_off = 22
    Italic_off = 23
    Underline_off = 24
    SlowBlink_off = 25
    FastBlink_off = 26
    ReverseVideo_off = 27
    Erase_off = 28
    Strikethrough_off = 29
    Black = 30
    Red = 31
    Green = 32
    Yellow = 33
    Blue = 34
    Magenta = 35
    Cyan = 36
    White = 37
    fgReset = 39
    bgBlack = 40
    bgRed = 41
    bgGreen = 42
    bgYellow = 43
    bgBlue = 44
    bgMagenta = 45
    bgCyan = 46
    bgWhite = 47
    bgReset = 49

color_name = {
    ANSI_COLOR.Black    : "black",
    ANSI_COLOR.Red      : "red",
    ANSI_COLOR.Green    : "green",
    ANSI_COLOR.Yellow   : "yellow",
    ANSI_COLOR.Blue     : "blue",
    ANSI_COLOR.Magenta  : "magenta",
    ANSI_COLOR.Cyan     : "cyan",
    ANSI_COLOR.White    : "white"
    }

class MudStreamReader(StreamReader):
    '''
    MUD 客户端的读取流，主要处理MUD中的转义字符
    '''
    def __init__(
            self, 
            limit: int = 65536, 
            loop = None,
            encoding: str = "utf-8",
            encoding_errors: str = "ignore",
            *args,
            **kwargs
            ) -> None:
        super().__init__(limit, loop)
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self.log = logging.getLogger("pymud.MudStreamReader")

        self._go_ahead = False

    async def readline(self):
        """
        返回从服务器中读取的一行信息，特征：
        1. 已解码为UTF--8格式
        2. 包含换行符(可能为\r\n->windows,\r->mac,\n->unix/linux)本身
        """
        # TODO 此处有点BUG，在某些时候，服务器端发送的内容不包含换行符，但在等待用户输入，此时readline不会返回，因而await会持续等待
        # if not "\n" in self._buffer:
        #     line = await super().read()
        # else:
        line = await super().readline()
        raw_line = line.decode(self.encoding, self.encoding_errors)
        return raw_line
        # 修改：使用console来处理，暂时不使用qt与html转换
        #return raw_line, *self.translateline(line)
    
    def goahead(self):
        self._go_ahead = True

    async def readuntil(self, separator=b'\n'):
        """
        更新 StreamReader的 readuntil语句，以使其可以人工中止
        """
        seplen = len(separator)
        if seplen == 0:
            raise ValueError('Separator should be at least one-byte string')

        if self._exception is not None:
            raise self._exception

        offset = 0

        # Loop until we find `separator` in the buffer, exceed the buffer size,
        # or an EOF has happened.
        while True:
            buflen = len(self._buffer)

            # Check if we now have enough data in the buffer for `separator` to
            # fit.
            if buflen - offset >= seplen:
                
                # 如果收到了GA， 此时如果还有分隔，则按分隔返回；若无，则返回全部
                if self._go_ahead:
                    self._go_ahead = False

                    isep = self._buffer.find(separator, offset)

                    if isep != -1:
                        # `separator` is in the buffer. `isep` will be used later
                        # to retrieve the data.
                        break

                    else:
                        # 返回全部，即默认认为分隔在缓冲尾端
                        chunk = self._buffer[:]
                        del self._buffer[:]

                        return bytes(chunk)

                else:

                    isep = self._buffer.find(separator, offset)

                    if isep != -1:
                        # `separator` is in the buffer. `isep` will be used later
                        # to retrieve the data.
                        break
                
                
                # see upper comment for explanation.
                offset = buflen + 1 - seplen
                if offset > self._limit:
                    raise exceptions.LimitOverrunError(
                        'Separator is not found, and chunk exceed the limit',
                        offset)

            # Complete message (with full separator) may be present in buffer
            # even when EOF flag is set. This may happen when the last chunk
            # adds data which makes separator be found. That's why we check for
            # EOF *ater* inspecting the buffer.
            if self._eof:
                chunk = bytes(self._buffer)
                self._buffer.clear()
                raise exceptions.IncompleteReadError(chunk, None)

            # _wait_for_data() will resume reading if stream was paused.
            await self._wait_for_data('readuntil')

        if isep > self._limit:
            raise exceptions.LimitOverrunError(
                'Separator is found, but chunk is longer than limit', isep)

        chunk = self._buffer[:isep + seplen]
        del self._buffer[:isep + seplen]

        self._maybe_resume_transport()
        return bytes(chunk)

    def translateline(self, data):
        # TODO 转换为HTML后，还要考虑原字符串中的转义问题
        formatted_line = bytearray()      # 带html格式的行结果
        plaintext_line = bytearray()      # plain文本的行结果
        format_queue = list()             # 储存格式列表，目的是为了在清楚时，逐个关闭
        content = b""                     # 过程数据保存在content中
        state = "normal"
        
        formatted_line.extend(b"<div>")

        for byte in data:
            #byte = bytes([byte,])

            if state == "normal":
                if byte == ESC:                 
                    state = "waitleftbracket"       # 下一个字节为[ 已知 COLOR和MXP均为 ^ESC[开头，color为m结尾，MXP为z结尾
                elif not byte in (10, 13) :         # 如果遇到 \r \n 不添加
                    if byte == 32:
                        formatted_line.extend(b"&nbsp;")
                    elif byte == 60:
                        formatted_line.extend(b"&lt;")
                    elif byte == 62:
                        formatted_line.extend(b"&gt;")
                    else:
                        formatted_line.append(byte)
                    plaintext_line.append(byte)
            elif state == "waitleftbracket":
                if byte == 91:                  # 字符'['
                    state = "waitdata"          # 下面字节为数据
                    content = b""               # 数据保存在content中
                else:
                    # TODO 当前设计为 如果转义字符之后紧跟着不是[，当做正常字符处理
                    state = "normal"
                    formatted_line.extend(byte)
                    plaintext_line.extend(byte)
            elif state == "waitdata":
                if byte == 109:                 # 如果是字符m，表示颜色结束
                    #if len(content) == 1:       # 1个字节，表示ANSI颜色
                    if not 59 in content:       # 如果数据内容中没有分号，则表示ANSI颜色
                        style = int(content)
                        #style = content[0]
                        if style == ANSI_COLOR.Bold:
                            formatted_line.extend(rb"<b>")
                            format_queue.insert(0, rb"</b>")
                        elif style == ANSI_COLOR.Italic:
                            formatted_line.extend(rb"<i>")
                            format_queue.insert(0, rb"</i>")
                        elif style == ANSI_COLOR.Underline:
                            formatted_line.extend(rb"<u>")
                            format_queue.insert(0, rb"</u>")
                        elif (style >= ANSI_COLOR.Black) and (style <= ANSI_COLOR.White):
                            fmt = f'<font color="{color_name[style]}">'
                            formatted_line.extend(fmt.encode(self.encoding))
                        elif (style >= ANSI_COLOR.bgBlack) and (style <= ANSI_COLOR.bgReset):
                            self.log.warning(f"暂不支持设置背景颜色模式: {content}")
                        elif style == ANSI_COLOR.Italic_off:
                            formatted_line.extend(rb"</i>")
                            if len(format_queue) > 0: format_queue.pop()
                        elif style == ANSI_COLOR.Bold_off:
                            formatted_line.extend(rb"</b>")
                            if len(format_queue) > 0: format_queue.pop()
                        elif style == ANSI_COLOR.Underline_off:
                            formatted_line.extend(rb"</u>")
                            if len(format_queue) > 0: format_queue.pop()
                        elif style == ANSI_COLOR.fgReset:
                            formatted_line.extend(rb"</font>")
                            if len(format_queue) > 0: format_queue.pop()
                        elif style == ANSI_COLOR.Reset:             # 重置时，关闭所有格式标记
                            while len(format_queue) > 0:
                                fmt = format_queue.pop()
                                formatted_line.extend(fmt)
                        else:             
                            self.log.debug(f"暂不支持的ANSI颜色: {content}")
                    elif len(content) == 3:       # 3个字节，表示256颜色，暂不支持
                        self.log.debug(f"暂不支持256色模式: {content}")
                    elif len(content) == 5:       # 5个字节，表示rgb颜色，暂不支持
                        self.log.debug(f"暂不支持24bit颜色模式: {content}")

                    state = "normal"
                elif byte == 122:               # 如果是z，表示MXP结束
                    self.log.warning(f'暂不支持MXP，收到未处理的MXP命令:{content}')
                    state = "normal"
                #elif byte == 59                 # 如果是有分号';'，才是更高的颜色
                else:                           # 否则为正常数据
                    content += bytes([byte,])

        formatted_line.extend(b"</div>")
        return formatted_line.decode(self.encoding), plaintext_line.decode(self.encoding)
