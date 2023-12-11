"""
MUD会话(session)中, 支持的对象列表
"""

import asyncio, logging, re
from collections.abc import Iterable
from collections import namedtuple
import functools
from typing import Any
from .settings import Settings

class CodeLine:
    """
    PyMUD中可执行的代码块（单行）"""

    @classmethod
    def create_line(cls, line: str) -> tuple:
        code_params = []
        arg = ""
        brace_count, single_quote, double_quote = 0, 0, 0

        if len(line)> 0:
            if line[0] == "#":
                start_idx = 1
                code_params.append("#")
            else:
                start_idx = 0

            for i in range(start_idx, len(line)):
                ch = line[i]
                if ch == "{":
                    brace_count += 1
                    arg += ch
                elif ch == "}":
                    brace_count -= 1
                    if brace_count < 0:
                        raise Exception("错误的代码块，大括号数量不匹配")
                    arg += ch
                elif ch == "'":
                    if single_quote == 0:
                        single_quote = 1
                    elif single_quote == 1:
                        single_quote = 0
                elif ch == '"':
                    if double_quote == 0:
                        double_quote = 1
                    elif double_quote == 1:
                        double_quote = 0

                elif ch == " ":
                    if (brace_count == 0) and (double_quote == 0) and (single_quote == 0):
                        code_params.append(arg)
                        arg = ""
                    else:
                        arg += ch
                else:
                    arg += ch

            if (single_quote > 0) or (double_quote > 0):
                raise Exception("引号的数量不匹配")
            
            if arg:
                code_params.append(arg)

            return tuple(code_params)
        else:
            return tuple()

    def __init__(self, _code: str) -> None:
        self.__code = _code
        self.code = CodeLine.create_line(_code)

    def execute(self, session, wildcards = None):
        asyncio.ensure_future(self.async_execute(session, wildcards))

    async def async_execute(self, session, wildcards = None):           
        new_code_str = self.__code
        new_code = []

        for item in self.code:
            if len(item) == 0: continue
            # %1~%9，特指捕获中的匹配内容
            if item in (f"%{i}" for i in range(1, 10)):
                idx = int(item[1:])
                if idx <= len(wildcards):
                    item_val = wildcards[idx-1]
                else:
                    item_val = None
                new_code.append(item_val)
                new_code_str = new_code_str.replace(item, item_val, 1)

            # 系统变量，%开头，直接%引用，如%line
            elif item[0] == "%":
                item_val = session.getVariable(item, "")
                new_code.append(item_val)
                new_code_str = new_code_str.replace(item, item_val, 1)

            # 非系统变量，@开头，在变量明前加@引用
            elif item[0] == "@":
                item_val = session.getVariable(item[1:], "")
                new_code.append(item_val)
                new_code_str = new_code_str.replace(item, item_val, 1)

            else:
                new_code.append(item)

        if new_code[0] == "#":
            await session.handle_input_async(new_code_str)
        else:
            await session.exec_command_async(" ".join(new_code))


class CodeBlock:
    """
    PyMUD中可以执行的代码块（最终使用，单行或多行）
    """

    @classmethod
    def create_block(cls, code: str) -> tuple:
        "创建代码块，并返回对象自身"

        code_lines = []
        line = ""
        brace_count = 0
        for i in range(0, len(code)):
            ch = code[i]
            if ch == "{":
                brace_count += 1
                line += ch
            elif ch == "}":
                brace_count -= 1
                if brace_count < 0:
                    raise Exception("错误的代码块，大括号数量不匹配")
                line += ch
            elif ch == ";":
                if brace_count == 0:
                    code_lines.append(line)
                    line = ""
                else:
                    line += ch
            else:
                line += ch

        if line:
            code_lines.append(line)

        if len(code_lines) == 1:
            return (CodeLine(code),)
        else:
            codes = []
            for line in code_lines:
                codes.extend(CodeBlock.create_block(line))

            return tuple(codes)

    def __init__(self, code) -> None:
        self.__code = code
        self.codes = CodeBlock.create_block(code)

    def execute(self, session, wildcards = None):
        asyncio.ensure_future(self.async_execute(session, wildcards))

    async def async_execute(self, session, wildcards = None):
        for code in self.codes:
            if isinstance(code, CodeLine):
                await code.async_execute(session, wildcards)

            if Settings.client["interval"] > 0:
                await asyncio.sleep(Settings.client["interval"] / 1000.0)

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
            self.session.info(msg, *args)
        else:
            self.log.info(msg)

    def warning(self, msg, *args):
        "若session存在，session中输出warning；不存在则在logging中输出warning"
        if self.session:
            self.session.warning(msg, *args)
        else:
            self.log.warning(msg)

    def error(self, msg, *args):
        "若session存在，session中输出error；同时在logging中输出error"
        if self.session:
            self.session.error(msg, *args)
        else:
            self.log.error(msg)

    def __repr__(self) -> str:
        return self.__detailed__()
    
    def __detailed__(self) -> str:
        return f'<{self.__class__.__name__}> id = "{self.id}" group = "{self.group}" enabled = {self.enabled}'

class GMCPTrigger(BaseObject):
    """
    支持GMCP收到数据的处理，可以类似于Trigger的使用用法
    GMCP必定以指定name为触发，触发时，其值直接传递给对象本身
    """
    def __init__(self, session, name, *args, **kwargs):
        self.event = asyncio.Event()
        self.value = None
        super().__init__(session, id = name, *args, **kwargs)

    def reset(self):
        "复位事件，用于async执行"
        self.event.clear()

    async def triggered(self):
        self.reset()
        await self.event.wait()
        self.reset()

    def __call__(self, value) -> Any:
        self.value = value
        if callable(self._onSuccess):
            self.event.set()
            self._onSuccess(self.id, value)

    def __detailed__(self) -> str:
        return f'<{self.__class__.__name__}> name = "{self.id}" value = "{self.value}" group = "{self.group}" enabled = {self.enabled} '
            
class MatchObject(BaseObject):
    "支持匹配内容的对象，包括Alias, Trigger, Command, Module等等"
    __abbr__ = "mob"
    def __init__(self, session, patterns, *args, **kwargs):
        self.patterns = patterns

        self.ignoreCase    = kwargs.get("ignoreCase", False)          # 忽略大小写，非默认
        self.isRegExp      = kwargs.get("isRegExp", True)             # 正则表达式，默认
        self.expandVar     = kwargs.get("expandVar", True)            # 扩展变量（将变量用值替代），默认
        self.keepEval      = kwargs.get("keepEval", False)            # 不中断，非默认
        self.raw           = kwargs.get("raw", False)                 # 原始数据匹配。当原始数据匹配时，不对VT100指令进行解析
        
        if isinstance(patterns, str):
            self.multiline = False
            self.linesToMatch = 1
        elif isinstance(patterns, Iterable):
            self.multiline = True
            self.linesToMatch = len(patterns)

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

    def set(self):
        "设置事件标记，用于人工强制触发"
        self.event.set()

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
                self.event.set()
                self._onSuccess(state.id, state.line, state.wildcards)
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
        return f'<{self.__class__.__name__}> id = "{self.id}" group = "{self.group}" enabled = {self.enabled} patterns = "{self.patterns}"'

class Alias(MatchObject):
    """别名，实现方式-MatchObject"""
    __abbr__ = "ali"

class SimpleAlias(Alias):
    "简单Alias，使用类似Zmud方法的处理方式"

    def __init__(self, session, patterns, code, *args, **kwargs):
        self._code = code
        self._codeblock = CodeBlock(code)
        super().__init__(session, patterns, *args, **kwargs)

    def onSuccess(self, id, line, wildcards):
        self._codeblock.execute(self.session, wildcards)

    def __detailed__(self) -> str:
        return f'<{self.__class__.__name__}> id = "{self.id}" group = "{self.group}" enabled = {self.enabled} patterns = "{self.patterns}" code = "{self._code}"'
    
    def __repr__(self) -> str:
        return self.__detailed__()

class Trigger(MatchObject):
    """触发器，实现方式-MatchObject"""
    __abbr__ = "tri"

    def __init__(self, session, patterns, *args, **kwargs):
        super().__init__(session, patterns, *args, **kwargs)
        self._task = None

    async def triggered(self):
        if isinstance(self._task, asyncio.Task) and (not self._task.done()):
            self._task.cancel("a new task has been settled")

        self._task = self.session.create_task(self.matched())
        return await self._task

class SimpleTrigger(Trigger):
    "简单Trigger，使用类似Zmud方法的处理方式"

    def __init__(self, session, patterns, code, *args, **kwargs):
        self._code = code
        self._codeblock = CodeBlock(code)
        super().__init__(session, patterns, *args, **kwargs)

    def onSuccess(self, id, line, wildcards):
        self._codeblock.execute(self.session, wildcards)

    def __detailed__(self) -> str:
        return f'<{self.__class__.__name__}> id = "{self.id}" group = "{self.group}" enabled = {self.enabled} patterns = "{self.patterns}" code = "{self._code}"'
    
    def __repr__(self) -> str:
        return self.__detailed__()

class Command(MatchObject):
    """命令，实现方式-MatchObject"""
    __abbr__ = "cmd"
    def __init__(self, session, patterns, *args, **kwargs):
        super().__init__(session, patterns, sync = False, *args, **kwargs)
        self._tasks = []

    def create_task(self, coro, *args, name = None):
        task = self.session.create_task(coro, *args, name)
        self._tasks.append(task)
        return task

    def remove_task(self, task: asyncio.Task, msg = None):
        result = self.session.remove_task(task, msg)
        if task in self._tasks:
            self._tasks.remove(task)
        return result
    
    def reset(self):
        super().reset()

        for task in self._tasks:
            if isinstance(task, asyncio.Task) and (not task.done()):
                task.cancel("manual reset.")

    async def execute(self, cmd, *args, **kwargs):
        self.reset()
        return

class SimpleCommand(Command):
    MAX_RETRY = 20

    """简单命令"""
    def __init__(self, session, patterns, succ_tri, *args, **kwargs):
        super().__init__(session, patterns, succ_tri, *args, **kwargs)
        self._succ_tris = list()
        self._fail_tris = list()
        self._retry_tris = list()
        self._executed_cmd = ""

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
        self.reset()
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
                tr.reset()
                tasklist.append(self.session.create_task(tr.triggered()))
            for tr in self._fail_tris:
                tr.reset()
                tasklist.append(self.session.create_task(tr.triggered()))
            for tr in self._retry_tris:
                tr.reset()
                tasklist.append(self.session.create_task(tr.triggered()))

            self.session.writeline(cmd)

            done, pending = await asyncio.wait(tasklist, timeout = self.timeout, return_when = "FIRST_COMPLETED")
            
            # 任务完成后增加0.1s等待（不应该等待)
            # await asyncio.sleep(0.1)

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
        self._task = self.session.create_task(asyncio.sleep(self.timeout), name = self.id)
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

    def onTimer(self, *args, **kwargs):
        "定时器到点时执行"
        if self.enabled:
            if callable(self._onSuccess):
                self._onSuccess(self.id, *args, **kwargs)

            if not self.oneShot:
                self._renewTask()
            else:
                del self._task
                self._task = None
            
class SimpleTimer(Timer):
    def __init__(self, session, code, *args, **kwargs):
        self._code = code
        self._codeblock = CodeBlock(code)
        super().__init__(session, *args, **kwargs)

    def onSuccess(self, *args, **kwargs):
        self._codeblock.execute(self.session)

    def __detailed__(self) -> str:
        return f'<{self.__class__.__name__}> enabled = {self.enabled} timeout = "{self.timeout}" code = "{self._code}"'
    
    def __repr__(self) -> str:
        return self.__detailed__()