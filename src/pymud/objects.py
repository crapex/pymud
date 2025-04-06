"""
MUD会话(session)中, 支持的对象列表
"""

import asyncio, logging, re, importlib
from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Iterable
from collections import namedtuple
from typing import Any
from .settings import Settings

class CodeLine:
    """
    PyMUD中可执行的代码块（单行），不应由脚本直接调用。
    若脚本需要生成自己的代码块，应使用 CodeBlock。
    """

    @classmethod
    def create_line(cls, line: str):
        hasvar = False
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
                        raise Exception(Settings.gettext("excpetion_brace_not_matched"))
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
                raise Exception(Settings.gettext("exception_quote_not_matched"))
            
            if arg:
                code_params.append(arg)
                if arg[0] in ("@", "%"):
                    hasvar = True

            syncmode = "dontcare"
            if len(code_params) >= 2:
                if (code_params[0] == "#"):
                    if code_params[1] in ("gag", "replace"):
                        syncmode = "sync"
                    elif code_params[1] in ("wa", "wait"):
                        syncmode = "async"
        
            return syncmode, hasvar, tuple(code_params), 
        else:
            return syncmode, hasvar, tuple()

    def __init__(self, _code: str) -> None:
        self.__code = _code
        self.__syncmode, self.__hasvar, self.code = CodeLine.create_line(_code)

    @property
    def length(self):
        return len(self.code)

    @property
    def hasvar(self):
        return self.__hasvar

    @property
    def commandText(self):
        return self.__code
    
    @property
    def syncMode(self):
        return self.__syncmode

    def execute(self, session, *args, **kwargs):
        session.exec_code(self, *args, **kwargs)

    def expand(self, session, *args, **kwargs):
        new_code_str = self.__code
        new_code = []

        line = kwargs.get("line", None) or session.getVariable("%line", "None")
        raw  = kwargs.get("raw", None) or session.getVariable("%raw", "None")
        wildcards = kwargs.get("wildcards", None)

        for item in self.code:
            if len(item) == 0: continue
            # %1~%9，特指捕获中的匹配内容
            if item in (f"%{i}" for i in range(1, 10)):
                idx = int(item[1:])
                if idx <= len(wildcards):
                    item_val = wildcards[idx-1]
                else:
                    item_val = "None"
                new_code.append(item_val)
                new_code_str = new_code_str.replace(item, f"{item_val}", 1)

            # 系统变量，%开头
            elif item == "%line":
                new_code.append(line)
                new_code_str = new_code_str.replace(item, f"{line}", 1)

            elif item == "%raw":
                new_code.append(raw)
                new_code_str = new_code_str.replace(item, f"{raw}", 1)

            elif item[0] == "%":
                item_val = session.getVariable(item, "")
                new_code.append(item_val)
                new_code_str = new_code_str.replace(item, f"{item_val}", 1)

            # 非系统变量，@开头，在变量明前加@引用
            elif item[0] == "@":
                item_val = session.getVariable(item[1:], "")
                new_code.append(item_val)
                new_code_str = new_code_str.replace(item, f"{item_val}", 1)

            else:
                new_code.append(item)

        return new_code_str, new_code

    async def async_execute(self, session, *args, **kwargs):           
        return await session.exec_code_async(self, *args, **kwargs)

class CodeBlock:
    """
    PyMUD中可以执行的代码块，可以进行命令、别名检测，以及完成变量替代。

    但一般情况下，不需要手动创建 CodeBlock 对象，而是在 SimpleTrigger, SimpleAlias 等类型中直接使用字符串进行创建。或者在命令行输入文本将自动创建。

    :param code: 代码块的代码本身。可以单行、多行、以及多层代码块
    """

    @classmethod
    def create_block(cls, code: str) -> tuple:
        "创建代码块，并返回对象自身"
        #若block由{}包裹，则去掉大括号直接分解

        if (len(code) >= 2) and (code[0] == '{') and (code[-1] == '}'):
            code = code[1:-1]

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
                    raise Exception(Settings.gettext("excpetion_brace_not_matched"))
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

        self.__syncmode = "dontcare"

        for code in self.codes:
            if isinstance(code, CodeLine):
                if code.syncMode == "dontcare":
                    continue
                elif code.syncMode == "sync":
                    if self.__syncmode in ("dontcare", "sync"):
                        self.__syncmode = "sync"
                    elif self.__syncmode == "async":
                        self.__syncmode = "conflict"
                        break

                elif code.syncMode == "async":
                    if self.__syncmode in ("dontcare", "async"):
                        self.__syncmode = "async"
                    elif self.__syncmode == "sync":
                        self.__syncmode = "conflict"
                        break

    @property
    def syncmode(self):
        """
        只读属性: 同步模式。在创建代码块时，根据代码内容自动判定模式。
        
        该属性有四个可能值
            - ``dontcare``: 同步异步均可，既不存在强制同步命令，也不存在强制异步命令
            - ``sync``: 强制同步，仅存在强制同步模式命令及其他非同步异步命令
            - ``async``: 强制异步，仅存在强制异步模式命令及其他非同步异步命令
            - ``conflict``: 模式冲突，同时存在强制同步和强制异步命令

        强制同步模式命令包括:
            - #gag
            - #replace

        强制异步模式命令包括:
            - #wait
        """

        return self.__syncmode

    def execute(self, session, *args, **kwargs):
        """
        执行该 CodeBlock。执行前判断 syncmode。
        - 仅当 syncmode 为 sync 时，才使用同步方式执行。
        - 当 syncmode 为其他值时，均使用异步方式执行
        - 当 syncmode 为 conflict 时，同步命令失效，并打印警告

        :param session: 命令执行的会话实例
        :param args: 兼容与扩展所需，用于变量替代及其他用途
        :param kwargs: 兼容与扩展所需，用于变量替代及其他用途
        """
        sync = kwargs.get("sync", None)
        if sync == None:
            if self.syncmode in ("dontcare", "async"):
                sync = False
            elif self.syncmode == "sync":
                sync = True
            elif self.syncmode == "conflict":
                session.warning(Settings.gettext("exception_forced_async"))
                sync = False

        if sync:
            for code in self.codes:
                if isinstance(code, CodeLine):
                    code.execute(session, *args, **kwargs)
        else:
            session.create_task(self.async_execute(session, *args, **kwargs))
        
    async def async_execute(self, session, *args, **kwargs):
        """
        以异步方式执行该 CodeBlock。参数与 execute 相同。
        """
        result = None
        for code in self.codes:
            if isinstance(code, CodeLine):
                result = await code.async_execute(session, *args, **kwargs)

            if Settings.client["interval"] > 0:
                await asyncio.sleep(Settings.client["interval"] / 1000.0)

        session.clean_finished_tasks()
        return result

class BaseObject:
    """
    MUD会话支持的对象基类。
    
    :param session: 所属会话对象
    :param args: 兼容与扩展所需
    :param kwargs: 兼容与扩展所需

    kwargs支持的关键字:
        :id: 唯一ID。不指定时，默认使用 __abbr__ + UniqueID 来生成
        :group: 所属的组名。不指定时，默认使用空字符串
        :enabled: 使能状态。不指定时，默认使用 True
        :priority: 优先级，越小优先级越高。不指定时，默认使用 100
        :timeout: 超时时间，单位为秒。不指定时，默认使用 10
        :sync: 同步模式。不指定时，默认为 True
        :oneShot: 仅执行一次标识。不指定时，默认为 False
        :onSuccess: 成功时的同步回调函数。不指定时，默认使用 self.onSuccess
        :onFailure: 失败时的同步回调函数。不指定时，默认使用 self.onFailure
        :onTimeout: 超时时的同步回调函数。不指定时，默认使用 self.onTimeout
    """

    State = namedtuple("State", ("result", "id", "line", "wildcards"))

    NOTSET  = N = -1
    FAILURE = F = 0
    SUCCESS = S = 1
    TIMEOUT = T = 2
    ABORT   = A = 3

    __abbr__ = "obj"
    "内部缩写代码前缀"

    def __init__(self, session, *args, **kwargs):
        from .session import Session
        if isinstance(session, Session):
            self.session    = session
        else:
            assert(Settings.gettext("exception_session_type_fail"))
            
        self._enabled   = True              # give a default value
        self.log        = logging.getLogger(f"pymud.{self.__class__.__name__}")
        self.id         = kwargs.get("id", session.getUniqueID(self.__class__.__abbr__))
        self.group      = kwargs.get("group", "")                  # 组
        self.enabled    = kwargs.get("enabled", True)              # 使能与否
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

        self.session.addObject(self)

    @property
    def enabled(self):
        "可读写属性，使能或取消使能本对象"
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
        group = f'group = "{self.group}" ' if self.group else ''
        return f'<{self.__class__.__name__}> id = "{self.id}" {group}enabled = {self.enabled}'

class GMCPTrigger(BaseObject):
    """
    GMCP触发器 GMCPTrigger 类型，继承自 BaseObject。

    GMCP触发器处于基于 GMCP 协议的数据，其使用方法类似于 Trigger 对象
    
    但 GMCPTrigger 必定以指定name为触发，触发时，其值直接传递给对象本身

    :param session: 本对象所属的会话
    :param name: 触发对应的 GMCP 的 name
    """
    def __init__(self, session, name, *args, **kwargs):
        self.event = asyncio.Event()
        self.value = None
        super().__init__(session, id = name, *args, **kwargs)

    def __del__(self):
        self.reset()

    def reset(self):
        "复位事件，用于async执行"
        self.event.clear()

    async def triggered(self):
        """
        异步触发的可等待函数。其使用方法和 Trigger.triggered() 类似，且参数与返回值均与之兼容。
        """
        self.reset()
        await self.event.wait()
        state = BaseObject.State(True, self.id, self.line, self.value)
        self.reset()
        return state

    def __call__(self, value) -> Any:
        try:
            #import json
            value_exp = eval(value)
        except:
            value_exp = value

        self.line  = value
        self.value = value_exp

        if callable(self._onSuccess):
            self.event.set()
            self._onSuccess(self.id, value, value_exp)

    def __detailed__(self) -> str:
        group = f'group = "{self.group}" ' if self.group else ''
        return f'<{self.__class__.__name__}> name = "{self.id}" value = "{self.value}" {group}enabled = {self.enabled} '
            
class MatchObject(BaseObject):
    """
    支持匹配内容的对象，包括Alias, Trigger, Command 等对象以及其子类对象。继承自 BaseObject
    
    :param session: 同 BaseObject , 本对象所属的会话
    :param patterns: 用于匹配的模式。详见 patterns 属性
    :param args: 兼容与扩展所需
    :param kwargs: 兼容与扩展所需

    MatchObject 新增了部分 kwargs 关键字，包括：
        :ignoreCase: 忽略大小写，默认为 False
        :isRegExp: 是否是正则表达式，默认为 True
        :keepEval: 是否持续匹配，默认为 False
        :raw: 是否匹配含有VT100 ANSI标记的原始数据，默认为 False
    """

    __abbr__ = "mob"
    def __init__(self, session, patterns, *args, **kwargs):
        self.ignoreCase    = kwargs.get("ignoreCase", False)          # 忽略大小写，非默认
        self.isRegExp      = kwargs.get("isRegExp", True)             # 正则表达式，默认
        self.expandVar     = kwargs.get("expandVar", True)            # 扩展变量（将变量用值替代），默认
        self.keepEval      = kwargs.get("keepEval", False)            # 不中断，非默认
        self.raw           = kwargs.get("raw", False)                 # 原始数据匹配。当原始数据匹配时，不对VT100指令进行解析
        
        self.wildcards = []
        self.lines = []
        self.event = asyncio.Event()

        self.patterns = patterns

        super().__init__(session, patterns = patterns, *args, **kwargs)

    def __del__(self):
        pass

    @property
    def patterns(self):
        """
        可读写属性， 本对象的匹配模式。该属性可以在运行时动态更改，改后即时生效。

        - 构造函数中的 patterns 用于指定初始的匹配模式。
        - 该属性支持字符串和其他可迭代对象（如元组、列表）两种形式。
            - 当为字符串时，使用单行匹配模式
            - 当为可迭代对象时，使用多行匹配模式。多行的行数由可迭代对象所确定。
        """
        return self._patterns

    @patterns.setter
    def patterns(self, patterns):
        self._patterns = patterns

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

    def reset(self):
        "复位事件，用于async执行未等待结果时，对事件的复位。仅异步有效。"
        self.event.clear()

    def set(self):
        "设置事件标记，可以用于人工强制触发，仅在异步触发器下生效。"
        self.event.set()

    def match(self, line: str, docallback = True) -> BaseObject.State:
        """
        匹配函数。由 Session 调用。

        :param line: 匹配的数据行
        :param docallback: 匹配成功后是否执行回调函数，默认为 True

        :return: BaseObject.State 类型，一个包含 result, id, name, line, wildcards 的命名元组对象
        """
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
                #if line == self.patterns:
                if self.patterns in line:
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
        # 当docallback为真时，是真正的进行匹配和触发，为false时，仅返回匹配结果，不实际触发
        if docallback:
            if self.sync:
                if state.result == self.SUCCESS:
                    self._onSuccess(state.id, state.line, state.wildcards)
                elif state.result == self.FAILURE:
                    self._onFailure(state.id, state.line, state.wildcards)
                elif state.result == self.TIMEOUT:
                    self._onTimeout(state.id, state.line, state.wildcards)
            
            if state.result == self.SUCCESS:
                self.event.set()
                
        self.state = state
        return state
    
    async def matched(self) -> BaseObject.State:
        """
        匹配函数的异步模式，等待匹配成功之后才返回。返回值 BaseObject.state
        
        异步匹配模式用于 Trigger 的异步模式以及 Command 的匹配中。
        """
        # 等待，再复位
        try:
            self.reset()
            await self.event.wait()
            self.reset()
        except Exception as e:
            self.error(Settings.gettext("exception_in_async", e))

        return self.state
    
    def __detailed__(self) -> str:
        group = f'group = "{self.group}" ' if self.group else ''
        return f'<{self.__class__.__name__}> id = "{self.id}" {group}enabled = {self.enabled} patterns = "{self.patterns}"'

class Alias(MatchObject):
    """
    别名 Alias 类型，继承自 MatchObject。

    其内涵与 MatchObject 完全相同，仅对缩写进行了覆盖。
    """
    
    __abbr__ = "ali"

class SimpleAlias(Alias):
    """
    简单别名 SimpleAlias 类型，继承自 Alias, 包含了 Alias 的全部功能， 并使用 CodeBlock 对象创建了 onSuccess 的使用场景。
    
    :param session: 本对象所属的会话， 同 MatchObject
    :param patterns: 匹配模式，同 MatchObject
    :param code: str, 当匹配成功时执行的代码， 使用 CodeBlock 进行实现
    """

    def __init__(self, session, patterns, code, *args, **kwargs):
        self._code = code
        self._codeblock = CodeBlock(code)
        super().__init__(session, patterns, *args, **kwargs)

    def onSuccess(self, id, line, wildcards):
        "覆盖了基类的默认 onSuccess方法，使用 CodeBlock 执行构造函数中传入的 code 参数"
        self._codeblock.execute(self.session, id = id, line = line, wildcards = wildcards)

    def __detailed__(self) -> str:
        group = f'group = "{self.group}" ' if self.group else ''
        return f'<{self.__class__.__name__}> id = "{self.id}" {group}enabled = {self.enabled} patterns = "{self.patterns}" code = "{self._code}"'
    
    def __repr__(self) -> str:
        return self.__detailed__()

class Trigger(MatchObject):
    """
    触发器 Trigger 类型，继承自 MatchObject。

    其内涵与 MatchObject 完全相同，仅对缩写进行了覆盖，并增写了 triggered 异步方法。
    """

    __abbr__ = "tri"

    def __init__(self, session, patterns, *args, **kwargs):
        super().__init__(session, patterns, *args, **kwargs)
        self._task = None

    async def triggered(self):
        """
        异步触发的可等待函数。内部通过 MatchObject.matched 实现

        差异在于对创建的 matched 任务进行了管理。
        """
        if isinstance(self._task, asyncio.Task) and (not self._task.done()):
            self._task.cancel()

        self._task = self.session.create_task(self.matched())
        return await self._task

class SimpleTrigger(Trigger):
    """
    简单别名 SimpleTrigger 类型，继承自 Trigger, 包含了 Trigger 的全部功能， 并使用 CodeBlock 对象创建了 onSuccess 的使用场景。
    
    :param session: 本对象所属的会话， 同 MatchObject
    :param patterns: 匹配模式，同 MatchObject
    :param code: str, 当匹配成功时执行的代码， 使用 CodeBlock 进行实现
    """

    def __init__(self, session, patterns, code, *args, **kwargs):
        self._code = code
        self._codeblock = CodeBlock(code)
        super().__init__(session, patterns, *args, **kwargs)

    def onSuccess(self, id, line, wildcards):
        "覆盖了基类的默认 onSuccess方法，使用 CodeBlock 执行构造函数中传入的 code 参数"
        
        raw = self.session.getVariable("%raw")
        self._codeblock.execute(self.session, id = id, line = line, raw = raw, wildcards = wildcards)

    def __detailed__(self) -> str:
        group = f'group = "{self.group}" ' if self.group else ''
        return f'<{self.__class__.__name__}> id = "{self.id}" {group}enabled = {self.enabled} patterns = "{self.patterns}" code = "{self._code}"'
    
    def __repr__(self) -> str:
        return self.__detailed__()

class Command(MatchObject):
    """
    命令 Command 类型，继承自 MatchObject。
    命令是 PYMUD 的最大特色，它是一组归纳了同步/异步执行、等待响应、处理的集成对象。
    要使用命令，不能直接使用 Command 类型，应总是继承并使用其子类，务必覆盖基类的 execute 方法。

    有关 Command 的使用帮助，请查看帮助页面

    :param session: 本对象所属的会话
    :param patterns: 匹配模式
    """
    __abbr__ = "cmd"
    def __init__(self, session, patterns, *args, **kwargs):
        super().__init__(session, patterns, sync = False, *args, **kwargs)
        self._tasks = set()

    def __unload__(self):
        """
        当从会话中移除任务时，会自动调用该函数。
        可以将命令管理的各子类对象在此处清除。
        该函数需要在子类中覆盖重写。
        """
        pass

    def unload(self):
        """
        与__unload__方法相同，子类仅需覆盖一种方法就可以
        """
        pass

    def create_task(self, coro, *args, name = None):
        """
        创建并管理任务。由 Command 创建的任务，同时也被 Session 所管理。
        其内部是调用 asyncio.create_task 进行任务创建。

        :param coro: 任务包含的协程或可等待对象
        :param name: 任务名称， Python 3.10 才支持的参数
        """
        task = self.session.create_task(coro, *args, name)
        task.add_done_callback(self._tasks.discard)
        self._tasks.add(task)
        return task

    def remove_task(self, task: asyncio.Task, msg = None):
        """
        取消任务并从管理任务清单中移除。由 Command 取消和移除的任务，同时也被 Session 所取消和移除。

        :param task: 要取消的任务
        :param msg: 取消任务时提供的消息， Python 3.10 才支持的参数
        """

        result = self.session.remove_task(task, msg)
        self._tasks.discard(task)
        # if task in self._tasks:
        #     self._tasks.remove(task)
        return result
    
    def reset(self):
        """
        复位命令，并取消和清除所有本对象管理的任务。
        """

        super().reset()

        for task in list(self._tasks):
            if isinstance(task, asyncio.Task) and (not task.done()):
                self.remove_task(task)

    async def execute(self, cmd, *args, **kwargs):
        """
        命令调用的入口函数。该函数由 Session 进行自动调用。
        通过 ``Session.exec`` 系列方法调用的命令，最终是执行该命令的 execute 方法。

        子类必须实现并覆盖该方法。
        """
        self.reset()
        return

class SimpleCommand(Command):
    """
    对命令的基本应用进行了基础封装的一种可以直接使用的命令类型，继承自 Command。

    SimpleCommand 并不能理解为 “简单” 命令，因为其使用并不简单。
    只有在熟练使用 Command 建立自己的命令子类之后，对于某些场景的应用才可以简化代码使用 SimpleCommand 类型。

    :param session: 本对象所属的会话
    :param patterns: 匹配模式
    :param succ_tri: 代表成功的响应触发器清单，可以为单个触发器，或一组触发器，必须指定

    kwargs关键字参数特殊支持：
        :fail_tri: 代表失败的响应触发器清单，可以为单个触发器，或一组触发器，可以为 None
        :retry_tri: 代表重试的响应触发器清单，可以为单个触发器，或一组触发器，可以为 None
    """

    MAX_RETRY = 20

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
        """
        覆盖基类的 execute 方法, SimpleCommand 的默认实现。

        :param cmd: 执行时输入的实际指令

        kwargs接受指定以下参数，在执行中进行一次调用:
            :onSuccess: 成功时的回调
            :onFailure: 失败时的回调
            :onTimeout: 超时时的回调
        """
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
            
            await asyncio.sleep(0.1)
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
    """
    定时器 Timer 类型，继承自 MatchObject。PYMUD 支持同时任意多个定时器。

    :param session: 对象所属会话
    
    Timer 中使用的 kwargs 均继承自 BaseObject，包括:
        - id: 标识
        - group: 组名
        - enabled: 使能状态
        - timeout: 定时时间
        - onSuccess: 定时到期执行的函数
    """
    __abbr__ = "ti"

    def __init__(self, session, *args, **kwargs):
        self._task = None
        self._halt = False
        super().__init__(session, *args, **kwargs)

    def __del__(self):
        self.reset()

    def startTimer(self):
        "启动定时器"
        if not isinstance(self._task, asyncio.Task):
            self._halt = False
            self._task = asyncio.create_task(self.onTimerTask())

        asyncio.ensure_future(self._task)

    async def onTimerTask(self):
        "定时任务的调用方法，脚本中无需调用"

        while self._enabled:
            await asyncio.sleep(self.timeout)

            if callable(self._onSuccess):
                self._onSuccess(self.id)

            if self.oneShot or self._halt:
                break


    def reset(self):
        "复位定时器，清除所创建的定时任务"
        try:
            self._halt = True
            if isinstance(self._task, asyncio.Task) and (not self._task.done()):
                self._task.cancel()

            self._task = None
        except asyncio.CancelledError:
            pass

    @property
    def enabled(self):
        "可读写属性，定时器使能状态"
        return self._enabled
    
    @enabled.setter
    def enabled(self, en: bool):
        self._enabled = en
        if not en:
            self.reset()
        else:
            self.startTimer()

    def __detailed__(self) -> str:
        group = f'group = "{self.group}" ' if self.group else ''
        return f'<{self.__class__.__name__}> id = "{self.id}" {group}enabled = {self.enabled} timeout = {self.timeout}'
    
    def __repr__(self) -> str:
        return self.__detailed__()
            
class SimpleTimer(Timer):
    """
    简单定时器 SimpleTimer 类型，继承自 Timer, 包含了 Timer 的全部功能， 并使用 CodeBlock 对象创建了 onSuccess 的使用场景。
    
    :param session: 本对象所属的会话， 同 MatchObject
    :param code: str, 当定时任务到期时执行的代码， 使用 CodeBlock 实现
    """
    def __init__(self, session, code, *args, **kwargs):
        self._code = code
        self._codeblock = CodeBlock(code)
        super().__init__(session, *args, **kwargs)

    def onSuccess(self, id):
        "覆盖了基类的默认 onSuccess方法，使用 CodeBlock 执行构造函数中传入的 code 参数"
        self._codeblock.execute(self.session, id = id)

    def __detailed__(self) -> str:
        group = f'group = "{self.group}" ' if self.group else ''
        return f'<{self.__class__.__name__}> id = "{self.id}" {group}enabled = {self.enabled} timeout = {self.timeout} code = "{self._code}"'

