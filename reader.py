import logging
from asyncio import StreamReader, Event, exceptions


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
        self._gmcp = {}
        self._gmcp_events = {}

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

    def feed_gmcp(self, key, value):
        self._gmcp[key] = value
        if not key in self._gmcp_events.keys():
            self._gmcp_events[key] = Event()
        self._gmcp_events[key].set()

    async def read_gmcp(self, key):
        if key in self._gmcp.keys() and key in self._gmcp_events.keys():
            event = self._gmcp_events[key]
            if isinstance(event, Event):
                await event.wait()
                event.clear()
                return self._gmcp[key]
            
        return None
    
    def list_gmcp(self):
        return self._gmcp
