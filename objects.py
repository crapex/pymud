"""
MUD会话(session)中, 支持的对象列表
"""

import asyncio, logging, re
from collections.abc import Iterable
from collections import namedtuple
import functools

class BaseObject:
    """MUD会话支持的对象基类"""

    State = namedtuple("State", ("result", "id", "line", "wildcards"))
    NOTSET  = N = -1
    FAILURE = F = 0
    SUCCESS = S = 1
    TIMEOUT = T = 2
    ABORT   = A = 3

    __abbr__ = "obj"
    def __init__(self, session, *args, **kwargs):
        self.session    = session

        self.log        = logging.getLogger(f"pymud.{self.__class__.__name__}")
        self.id         = kwargs.get("id", session.getUniqueID(self.__class__.__abbr__))
        self.group      = kwargs.get("group", "")                  # 组
        self._enabled   = kwargs.get("enabled", True)              # 使能与否
        self.priority   = kwargs.get("priority", 100)              # 优先级
        self.timeout    = kwargs.get("timeout", 10)                # 超时时间
        self.sync       = kwargs.get("sync", True)                 # 同步模式，默认
        self.oneShot    = kwargs.get("oneShot", False)             # 单次执行，非默认

        self.args       = args
        self.kwarg      = kwargs

        # 成功完成，失败完成，超时的处理函数(若有指定)，否则使用类的自定义函数
        self._onSuccess = kwargs.get("onSuccess", self.onSuccess)
        self._onFailure = kwargs.get("onFailure", self.onFailure)
        self._onTimeout = kwargs.get("onTimeout", self.onTimeout)

        self.log.debug(f"对象实例 {self} 创建成功.")

    @property
    def enabled(self):
        "使能或取消使能本对象"
        return self._enabled

    @enabled.setter
    def enabled(self, en: bool):
        self._enabled = en

    def onSuccess(self, *args, **kwargs):
        "成功后执行的默认回调函数"
        self.log.debug(f"{self} 缺省成功回调函数被执行.")

    def onFailure(self, *args, **kwargs):
        "失败后执行的默认回调函数"
        self.log.debug(f"{self} 缺省失败回调函数被执行.")

    def onTimeout(self, *args, **kwargs):
        "超时后执行的默认回调函数"
        self.log.debug(f"{self} 缺省超时回调函数被执行.")

    def expandInnerVariables(self, input: str):
        "内部变量扩展。使用内部变量应直接使用python格式化方式: {0} 以此之类"
        # TODO: 后续设计
        pass

    def expandOutterVariables(self, input: str):
        "外部变量扩展。使用外部变量，应使用@varname格式，且前后有空格表示"
        # TODO: 后续设计
        pass 

    def debug(self, msg):
        "在logging中记录debug信息"
        self.log.debug(msg)

    def info(self, msg, *args):
        "若session存在，session中输出info；不存在则在logging中输出info"
        if self.session:
            self.session.app.info(msg, *args)
        else:
            self.log.info(msg)

    def warning(self, msg, *args):
        "若session存在，session中输出warning；同时在logging中输出warning"
        if self.session:
            self.session.app.warning(msg, *args)
        
        self.log.warning(msg)

    def error(self, msg, *args):
        "若session存在，session中输出error；同时在logging中输出error"
        if self.session:
            self.session.app.error(msg, *args)
        
        self.log.error(msg)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}> id = "{self.id}" group = "{self.group}" enabled = {self.enabled}'
    
    def __detailed__(self) -> str:
        return self.__repr__

class MatchObject(BaseObject):
    "支持匹配内容的对象，包括Alias, Trigger, Command, Module等等"
    __abbr__ = "mob"
    def __init__(self, session, patterns, *args, **kwargs):
        self.patterns = patterns

        self.ignoreCase    = kwargs.get("ignoreCase", False)          # 忽略大小写，非默认
        self.isRegExp      = kwargs.get("isRegExp", True)             # 正则表达式，默认
        self.expandVar     = kwargs.get("expandVar", True)            # 扩展变量（将变量用值替代），默认
        #self.multiline     = kwargs.get("multiline", False)          # 多行
        #self.linesToMatch  = kwargs.get("linesToMatch", 2)           # 行数
        self.keepEval      = kwargs.get("keepEval", False)            # 不中断，非默认
        self.raw           = kwargs.get("raw", False)                 # 原始数据匹配。当原始数据匹配时，不对VT100指令进行解析
        

        if isinstance(patterns, str):
            self.multiline = False
            self.linesToMatch = 1
        elif isinstance(patterns, Iterable):
            self.multiline = True
            self.linesToMatch = len(patterns)
        #else: #if isinstance(matcher, str):

        if self.isRegExp:
            flag = 0
            if self.ignoreCase: flag = re.I
            if not self.multiline:
                self._regExp = re.compile(self.patterns, flag)   # 此处可考虑增加flags
            else:
                self._regExps = []
                for line in self.patterns:
                    self._regExps.append(re.compile(line, flag))

                self.linesToMatch = len(self._regExps)
                self._mline = 0

        self.wildcards = []
        self.lines = []
        self.event = asyncio.Event()

        super().__init__(session, patterns = patterns, *args, **kwargs)

    def reset(self):
        "复位事件，用于async执行"
        self.event.clear()

    def match(self, line: str, docallback = True) -> BaseObject.State:
        result = self.NOTSET

        if not self.multiline:                              # 非多行
            if self.isRegExp:
                m = self._regExp.match(line)
                if m:
                    result = self.SUCCESS
                    self.wildcards.clear()
                    if len(m.groups()) > 0:
                        self.wildcards.extend(m.groups())

                    self.lines.clear()
                    self.lines.append(line)
            else:
                #if line.find(self.patterns) >= 0:
                if line == self.patterns:
                    result = self.SUCCESS
                    self.lines.clear()
                    self.lines.append(line)
                    self.wildcards.clear()
        
        else:                                               # 多行匹配情况
            # multilines match. 多行匹配时，受限于行的捕获方式，必须一行一行来，设置状态标志进行处理。
            if self._mline == 0:                            # 当尚未开始匹配时，匹配第1行
                m = self._regExps[0].match(line)
                if m:
                    self.lines.clear()
                    self.lines.append(line)
                    self.wildcards.clear()
                    if len(m.groups()) > 0:
                        self.wildcards.extend(m.groups())
                    self._mline = 1                         # 下一状态 （中间行）
            elif (self._mline > 0) and (self._mline < self.linesToMatch - 1):
                m = self._regExps[self._mline].match(line)
                if m:
                    self.lines.append(line)
                    if len(m.groups()) > 0:
                        self.wildcards.extend(m.groups())
                    self._mline += 1
                else:
                    self._mline = 0
            elif self._mline == self.linesToMatch - 1:      # 最终行
                m = self._regExps[self._mline].match(line)
                if m:
                    self.lines.append(line)
                    if len(m.groups()) > 0:
                        self.wildcards.extend(m.groups())
                    result = self.SUCCESS

                self._mline = 0

        state = BaseObject.State(result, self.id, "\n".join(self.lines), tuple(self.wildcards))

        # 采用回调方式执行的时候，执行函数回调（仅当self.sync和docallback均为真时才执行同步
        if self.sync and docallback:
            if state.result == self.SUCCESS:
                self._onSuccess(state.id, state.line, state.wildcards)
                self.event.set()
            elif state.result == self.FAILURE:
                self._onFailure(state.id, state.line, state.wildcards)
            elif state.result == self.TIMEOUT:
                self._onTimeout(state.id, state.line, state.wildcards)

        self.state = state
        return state
    
    async def matched(self) -> BaseObject.State:
        "异步等待匹配，返回BaseObject.state"
        # 等待，再复位
        try:
            self.reset()
            await self.event.wait()
            self.reset()
        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}")

        return self.state
    
    def __detailed__(self) -> str:
        return f'<{self.__class__.__name__}> id = "{self.id}" group = "{self.group}" enabled = {self.enabled} patterns = "{self.patterns}'

class Alias(MatchObject):
    """别名，实现方式-MatchObject"""
    __abbr__ = "ali"

class Trigger(MatchObject):
    """触发器，实现方式-MatchObject"""
    __abbr__ = "tri"

    async def triggered(self):
        return await self.matched()

class Command(MatchObject):
    """命令，实现方式-MatchObject"""
    __abbr__ = "cmd"
    def __init__(self, session, patterns, *args, **kwargs):
        super().__init__(session, patterns, sync = False, *args, **kwargs)

    async def execute(self, cmd, *args, **kwargs):
        return

class SimpleCommand(Command):
    MAX_RETRY = 20

    """简单命令"""
    def __init__(self, session, patterns, succ_tri, *args, **kwargs):
        super().__init__(session, patterns, succ_tri, *args, **kwargs)
        self._succ_tris = list()
        self._fail_tris = list()
        self._retry_tris = list()

        if isinstance(succ_tri, Iterable):
            self._succ_tris.extend(succ_tri)
        else:
            if isinstance(succ_tri, Trigger):
                self._succ_tris.append(succ_tri)

        fail_tri = kwargs.get("fail_tri", None)
        if fail_tri:
            if isinstance(fail_tri, Iterable):
                self._fail_tris.extend(fail_tri)
            else:
                if isinstance(fail_tri, Trigger):
                    self._fail_tris.append(fail_tri)

        retry_tri = kwargs.get("retry_tri", None)
        if retry_tri:
            if isinstance(retry_tri, Iterable):
                self._retry_tris.extend(retry_tri)
            else:
                if isinstance(retry_tri, Trigger):
                    self._retry_tris.append(retry_tri)

    async def execute(self, cmd, *args, **kwargs):
        # 0. check command
        cmd = cmd or self.patterns
        # 1. save the command, to use later.
        self._executed_cmd = cmd
        # 2. writer command
        retry_times = 0
        while True:
            # 1. create awaitables
            tasklist = list()
            for tr in self._succ_tris:
                tasklist.append(asyncio.create_task(tr.triggered()))
            for tr in self._fail_tris:
                tasklist.append(asyncio.create_task(tr.triggered()))
            for tr in self._retry_tris:
                tasklist.append(asyncio.create_task(tr.triggered()))

            self.session.writeline(cmd)

            done, pending = await asyncio.wait(tasklist, timeout = self.timeout, return_when = "FIRST_COMPLETED")
            tasks_done = list(done)
            
            tasks_pending = list(pending)
            for t in tasks_pending:
                t.cancel()

            result = self.NOTSET
            if len(tasks_done) > 0:
                task = tasks_done[0]
                _, name, line, wildcards = task.result()
                # success
                if name in (tri.id for tri in self._succ_tris):
                    result = self.SUCCESS
                    break
                    
                elif name in (tri.id for tri in self._fail_tris):
                    result = self.FAILURE
                    break

                elif name in (tri.id for tri in self._retry_tris):
                    retry_times += 1
                    if retry_times > self.MAX_RETRY:
                        result = self.FAILURE
                        break

                    await asyncio.sleep(2)

            else:
                result = self.TIMEOUT
                break

        if result == self.SUCCESS:
            self._onSuccess(name = self.id, cmd = cmd, line = line, wildcards = wildcards)
            _outer_onSuccess = kwargs.get("onSuccess", None)
            if callable(_outer_onSuccess):
                _outer_onSuccess(name = self.id, cmd = cmd, line = line, wildcards = wildcards)

        elif result == self.FAILURE:
            self._onFailure(name = self.id, cmd = cmd, line = line, wildcards = wildcards)
            _outer_onFailure = kwargs.get("onFailure", None)
            if callable(_outer_onFailure):
                _outer_onFailure(name = self.id, cmd = cmd, line = line, wildcards = wildcards)

        elif result == self.TIMEOUT:
            self._onTimeout(name = self.id, cmd = cmd, timeout = self.timeout)
            _outer_onTimeout = kwargs.get("onTimeout", None)
            if callable(_outer_onTimeout):
                _outer_onTimeout(name = self.id, cmd = cmd, timeout = self.timeout)

        return result

class Timer(BaseObject):
    "PYMUD定时器"
    __abbr__ = "tmr"

    def __init__(self, session, *args, **kwargs):
        super().__init__(session, *args, **kwargs)

        if self._enabled:
            self._renewTask()

    def _renewTask(self):
        self._task = asyncio.create_task(asyncio.sleep(self.timeout), name = self.id)
        self._task.add_done_callback(self.onTimer)

    @property
    def enabled(self):
        return self._enabled
    
    @enabled.setter
    def enabled(self, en: bool):
        self._enabled = en
        if not en:
            self._task = None
        else:
            self._renewTask()

    def onTimer(self, task, *args, **kwargs):
        "定时器到点时执行"
        if self.enabled:
            if callable(self._onSuccess):
                self._onSuccess(self.id, *args, **kwargs)

            if not self.oneShot:
                self._renewTask()
            else:
                del self._task
                self._task = None
            

       

        