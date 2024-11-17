import os, re, datetime, threading, pathlib
from queue import SimpleQueue, Empty
from pathlib import Path

class Logger:
    """
    PyMUD 的记录器类型，可用于会话中向文件记录数据。记录文件保存在当前目录下的 log 子目录中
    
    :param name: 记录器名称，各记录器名称应保持唯一。记录器名称会作为记录文件名称的主要参数
    :param mode: 记录模式。可选模式包括 a, w, n 三种。
       - a为添加模式，当新开始记录时，会添加在原有记录文件（name.log）之后。
       - w为覆写模式，当新开始记录时，会覆写原记录文件（name.log）。
       - n为新建模式，当新开始记录时，会以name和当前时间为参数新建一个文件（name.now.log）用于记录。
    :param encoding: 记录文件的编码格式，默认为 "utf-8"
    :param errors: 当编码模式失败时的处理方式，默认为 "ignore"
    :param raw: 记录带ANSI标记的原始内容，还是记录纯文本内容，默认为True，即记录带ANSI标记的原始内容。
    """

    # _esc_regx = re.compile(r"\x1b\[[\d;]+[abcdmz]", flags = re.IGNORECASE)

    def __init__(self, name, mode = 'a', encoding = "utf-8", errors = "ignore", raw = False):
        self._name = name
        self._enabled = False
        self._raw = raw
        self.mode = mode
        self._encoding = encoding
        self._errors = errors
        self._lock = threading.RLock()
        self._stream = None
        
        self._queue = SimpleQueue()

    @property
    def name(self):
        "记录器名称，仅在创建时设置，过程中只读"
        return self._name

    @property
    def enabled(self):
        """
        使能属性。
        从false切换到true时，会打开文件，创建后台线程进行记录。
        从true切换到false时，会终止后台记录线程，并关闭记录文件。
        """
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        if self._enabled != enabled:
            if enabled:
                mode = "a"

                if self._mode in ("a", "w"):
                    filename = f"{self.name}.log"
                    mode = self._mode
                elif self._mode == "n":
                    now = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                    filename = f"{self.name}.{now}.log"

                logdir = Path.cwd().joinpath('log')
                if not logdir.exists() or not logdir.is_dir():
                    logdir.mkdir()

                filename = logdir.joinpath(filename)
                #filename = os.path.abspath(filename)
                self._stream = open(filename, mode = mode, encoding = self._encoding, errors = self._errors)
                self._thread = t = threading.Thread(target=self._monitor)
                t.daemon = True
                t.start()

            else:
                self._queue.put_nowait(None)
                self._thread.join()
                self._thread = None
                self._closeFile()

            self._enabled = enabled

    @property
    def raw(self):
        "属性，设置和获取是否记录带有ANSI标记的原始记录"
        return self._raw
    
    @raw.setter
    def raw(self, val: bool):
        self._raw = val

    @property
    def mode(self):
        "属性，记录器模式，可为 a, w, n"
        return self._mode
    
    @mode.setter
    def mode(self, value):
        if value in ("a", "w", "n"):
            self._mode = value

    def _closeFile(self):
        """
        Closes the stream.
        """
        self._lock.acquire()
        try:
            if self._stream:
                try:
                    self._stream.flush()
                finally:
                    stream = self._stream
                    self._stream = None
                    stream.close()
        finally:
            self._lock.release()

    def log(self, msg):
        """
        向记录器记录信息。记录的信息会通过队列发送到独立的记录线程。
        当记录器未使能时，使用该函数调用也不会记录。
        
        :param msg: 要记录的信息
        """
        if self._enabled:
            self._queue.put_nowait(msg)

    def _monitor(self):
        """
        Monitor the queue for records, and ask the handler
        to deal with them.

        This method runs on a separate, internal thread.
        The thread will terminate if it sees a sentinel object in the queue.
        """
        newline = True
        while True:
            try:
                data = self._queue.get(block = True)
                if data:
                    self._lock.acquire()

                    if newline:
                        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        header = f"{now} {self._name}: "
                        self._stream.write(header)
                        newline = False

                    if data.endswith("\n"):
                        data = data.rstrip("\n").rstrip("\r") + "\n"
                        newline = True

                    if not self._raw:
                        from .session import Session
                        data = Session.PLAIN_TEXT_REGX.sub("", data)
                        #data = self._esc_regx.sub("", data)

                    self._stream.write(data)

                    self._stream.flush()
                    self._lock.release()

                else:
                    break
            except Empty:
                break
