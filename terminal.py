"""
提供支持MUD协议的输入/输出终端的标准接口类——终端、基于控制台的终端、基于pySide的终端
标准终端应支持VT100所有特性，考虑支持XTERM特性，支持ANSI颜色、256颜色
"""

import os, aioconsole, asyncio

class MudTerminal:
    """
    基础的MUD终端(接口基础类，除必要特性外，并无实现)
    本终端类型使用了asyncio的异步特性，因此主宿主必须包含正在运行的消息循环，或指定消息循环
    """
    def __init__(
        self, 
        encoding = "utf-8", 
        encoding_errors = "ignore",
        newline = "\n",
        loop : asyncio.AbstractEventLoop = None
        ):
        
        self.clear_style = "\x1b[0m"
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        self.newline = newline

        self._features = {
                "ANSI"      : True,
                "VT100"     : False,
                "UTF-8"     : False,
                "COLORS256" : False,
                "MOUSETRACKING"     : False,
                "OSC_COLOR_PALETTE" : False,
                "SCREEN_READER"     : False,
                "PROXY"     : False,
                "TRUECOLOR" : False,
                "MNES"      : False,
                "MSLP"      : False,
                "SSL"       : False,
                }

        if not loop:
            raise Exception("终端只能运行在事件循环中！")
        self.loop = loop

    def get_feature(self, name):
        val = getattr(self._features, name, False)
        return val

    def get_features(self):
        return self._features

    def get_feature_value(self):
        idx, value = 0, 0
        for k, v in self._features.items():
            if v:
                value += (1 << idx)
            idx += 1

        return value

    def getwidth(self):
        return 150
    
    def getheight(self):
        return 50

    def writebytes(self, data_in_bytes):
        """向终端中写入字节流，需子类自行实现"""
        pass

    def write(self, data_in_str: str):
        """向终端中写入字符串，会使用编码调用字符串的encode，并自动调用writebytes写入方法"""
        data_in_bytes = data_in_str.encode(self.encoding, self.encoding_errors)
        self.writebytes(data_in_bytes)

    def writeline(self, line: str):
        """向终端中写入一行。与write的区别为，在line数据写入完毕后，会自动加入换行符。换行符由实例化类时的newline参数指定"""
        self.write(line)
        self.write(self.clear_style)
        self.write(self.newline)

    def writelines(self, lines, newline_in_lines = False):
        """向终端中写入多行。多行内容由lines指定。newline_in_lines指定在lines的每一行结尾是否带有换行符"""
        if newline_in_lines:
            for line in lines:
                self.write(line)
        else:
            for line in lines:
                self.writeline(line)

    async def drain(self):
        pass

    async def wait_closed(self):
        await self.drain()

    async def readline(self):
        """从输入流中读取一行"""
        pass

    async def readuntil(self, seperator=b"\n"):
        """从输入流中读取字节流，直至遇到seperator分隔符"""
        pass

    async def read(self, n=-1):
        """
        从输入流中读取字节流, 至多n个字节
        当n为-1时，读取缓冲区中所有字节
        当n为0时，直接返回空结果
        当n为正数时，至多读取n个字节，不受流的Limit限制
        """
        pass

    async def readexactly(self, n):
        """
        从输入流中读取字节流, 精确/确切的n个字节
        
        Raise an IncompleteReadError if EOF is reached before `n` bytes can be
        read. The IncompleteReadError.partial attribute of the exception will
        contain the partial read bytes.

        if n is zero, return empty bytes object.

        Returned value is not limited with limit, configured at stream
        creation.

        If stream was paused, this function will automatically resume it if
        needed.
        """
        pass


class ConsoleTerminal(MudTerminal):
    """
    基于控制台(命令行)的MUD终端实现
    """
    def __init__(self, encoding="utf-8", encoding_errors="ignore", newline="\n", loop=None):
        super().__init__(encoding, encoding_errors, newline, loop)
        
        super().get_features().update({
                "VT100"     : True,
                "UTF-8"     : True,
                "COLORS256" : True,
                # "MOUSETRACKING"     : True,
                # "SCREEN_READER"     : True,
                # "TRUECOLOR" : True,
                # "MNES"      : True,
                })

        # 阻塞主线程，并等待返回aio的标准输入输出流
        if self.loop:
            self._stream_ok = loop.create_future()
            reader, writer = self.loop.run_until_complete(aioconsole.get_standard_streams())

            self.reader = reader
            self.writer = writer
            self.loop.run_until_complete(self.drain())
        else:
            raise Exception("没有可用的事件循环!")
        
    def getwidth(self):
        try:
            width = os.get_terminal_size().columns
        except:
            width = super().getwidth()
        
        return width
    
    def getheight(self):
        try:
            height = os.get_terminal_size().lines
        except:
            height = super().getheight()
        return height


    def writebytes(self, data_in_bytes):
        if self.writer:
            self.writer.write(data_in_bytes)
        else:
            raise Exception("writer流有错误, 无法写入!")

    def write(self, data_in_str: str):
        if self.writer:
            data_in_bytes = data_in_str.encode(self.encoding, self.encoding_errors)
            self.writebytes(data_in_bytes)
        else:
            raise Exception("writer流有错误, 无法写入!")

    async def drain(self):
        if self.writer:
            await self.writer.drain()

    async def read(self, n=-1):
        return await self.reader.read(n)
    
    async def readline(self):
        line = await self.reader.readline()
        if isinstance(line, bytes) or isinstance(line, bytearray):
            line_str = line.decode(self.encoding, self.encoding_errors)
        elif isinstance(line, str):
            line_str = line
        return line_str.rstrip(self.newline)
    
    async def readuntil(self, seperator=b"\n"):
        return await super().readuntil(seperator)
    
    async def readexactly(self, n):
        return await super().readexactly(n)


__all__ = [MudTerminal, ConsoleTerminal]


async def main():
    term = ConsoleTerminal()
    term.writer.write("Hello, asyncio ok.")
    await term.writer.drain()
 
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    term = ConsoleTerminal(loop=loop)
    term.writeline("this is \x1b[1m\x1b[31moutside\x1b[0m class")
    loop.run_until_complete(term.drain())
    loop.close()
    print("console size:", term.getwidth(), term.getheight())
    print("feature_value: ", term.get_feature_value())
    print("program exit.")

