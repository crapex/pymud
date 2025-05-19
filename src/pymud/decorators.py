import sys, functools, traceback
from typing import Union, Optional, List

def print_exception(session, e: Exception):
    """打印异常信息"""
    from .settings import Settings
    from .session import Session
    if isinstance(session, Session):
        # tb = sys.exc_info()[2]
        # frames = traceback.extract_tb(tb)
        # frame = frames[-1]
        # session.error(Settings.gettext("exception_traceback", frame.filename, frame.lineno, frame.name), Settings.gettext("script_error"))
        # if frame.line:
        #     session.error(f"    {frame.line}", Settings.gettext("script_error"))

        # session.error(Settings.gettext("exception_message", type(e).__name__, e), Settings.gettext("script_error"))
        # session.error("===========================", Settings.gettext("script_error"))
        session.error(traceback.format_exc(), Settings.gettext("script_error"))

def exception(func):
    """方法异常处理装饰器，捕获异常后通过会话的session.error打印相关信息"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        from .objects import BaseObject
        from .modules import ModuleInfo, IConfig
        from .session import Session
        from .settings import Settings
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            # 调用类的错误处理方法
            if isinstance(self, Session):
                session = self
            elif isinstance(self, (BaseObject, IConfig, ModuleInfo)):
                session = self.session
            else:
                session = None
                
            if isinstance(session, Session):
                print_exception(session, e)
                #session.error(Settings.gettext("exception_message", e, type(e)))
                #session.error(Settings.gettext("exception_traceback", traceback.format_exc()))
            else:
                raise  # 当没有会话时，选择重新抛出异常
    return wrapper

def async_exception(func):
    """异步方法异常处理装饰器，捕获异常后通过会话的session.error打印相关信息"""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        from .objects import BaseObject
        from .modules import ModuleInfo, IConfig
        from .session import Session
        from .settings import Settings
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            if isinstance(self, Session):
                session = self
            elif isinstance(self, (BaseObject, IConfig, ModuleInfo)):
                session = self.session
            else:
                session = None

            if isinstance(session, Session):
                print_exception(session, e)

            else:
                raise  # 当没有会话时，选择重新抛出异常
    return wrapper


class PymudDecorator:
    """
    装饰器基类。使用装饰器可以快捷创建各类Pymud基础对象。
    
        :param type: 装饰器的类型，用于区分不同的装饰器，为字符串类型。
        :param args: 可变位置参数，用于传递额外的参数。
        :param kwargs: 可变关键字参数，用于传递额外的键值对参数。
    """
    def __init__(self, type: str, *args, **kwargs):
        self.type = type
        self.args = args
        self.kwargs = kwargs

    def __call__(self, func):
        decos = getattr(func, "__pymud_decorators__", [])
        decos.append(self)
        func.__pymud_decorators__ = decos

        return func

    def __repr__(self):
        return f"<{self.__class__.__name__} type = {self.type} args = {self.args} kwargs = {self.kwargs}>"


def alias(
        patterns: Union[List[str], str], 
        id: Optional[str] = None, 
        group: str = "", 
        enabled: bool = True, 
        ignoreCase: bool = False, 
        isRegExp: bool = True, 
        keepEval: bool = False, 
        expandVar: bool = True, 
        priority: int = 100, 
        oneShot: bool = False,  
        *args, **kwargs):
    """
    使用装饰器创建一个别名（Alias）对象。被装饰的函数将在别名成功匹配时调用。
    被装饰的函数，除第一个参数为类实例本身self之外，另外包括id, line, wildcards三个参数。
    其中id为别名对象的唯一标识符，line为匹配的文本行，wildcards为匹配的通配符列表。

    :param patterns: 别名匹配的模式。
    :param id: 别名对象的唯一标识符，不指定时将自动生成唯一标识符。
    :param group: 别名所属的组名，默认为空字符串。
    :param enabled: 别名是否启用，默认为 True。
    :param ignoreCase: 匹配时是否忽略大小写，默认为 False。
    :param isRegExp: 模式是否为正则表达式，默认为 True。
    :param keepEval: 若存在多个可匹配的别名时，是否持续匹配，默认为 False。
    :param expandVar: 是否展开变量，默认为 True。
    :param priority: 别名的优先级，值越小优先级越高，默认为 100。
    :param oneShot: 别名是否只触发一次后自动失效，默认为 False。
    :param args: 可变位置参数，用于传递额外的参数。
    :param kwargs: 可变关键字参数，用于传递额外的键值对参数。
    :return: PymudDecorator 实例，类型为 "alias"。
    """
    # 将传入的参数更新到 kwargs 字典中
    kwargs.update({
        "patterns": patterns,
        "id": id, 
        "group": group, 
        "enabled": enabled, 
        "ignoreCase": ignoreCase, 
        "isRegExp": isRegExp, 
        "keepEval": keepEval, 
        "expandVar": expandVar, 
        "priority": priority, 
        "oneShot": oneShot})
    
    # 如果 id 为 None，则从 kwargs 中移除 "id" 键
    if not id:
        kwargs.pop("id")

    return PymudDecorator("alias", *args, **kwargs)

def trigger(
        patterns: Union[List[str], str], 
        id: Optional[str] = None, 
        group: str = "", 
        enabled: bool = True, 
        ignoreCase: bool = False, 
        isRegExp: bool = True, 
        keepEval: bool = False, 
        expandVar: bool = True, 
        raw: bool = False, 
        priority: int = 100, 
        oneShot: bool = False,  
        *args, **kwargs):
    """
    使用装饰器创建一个触发器（Trigger）对象。

    :param patterns: 触发器匹配的模式。单行模式可以是字符串或正则表达式，多行模式必须是元组或列表，其中每个元素都是字符串或正则表达式。
    :param id: 触发器对象的唯一标识符，不指定时将自动生成唯一标识符。
    :param group: 触发器所属的组名，默认为空字符串。
    :param enabled: 触发器是否启用，默认为 True。
    :param ignoreCase: 匹配时是否忽略大小写，默认为 False。
    :param isRegExp: 模式是否为正则表达式，默认为 True。
    :param keepEval: 若存在多个可匹配的触发器时，是否持续匹配，默认为 False。
    :param expandVar: 是否展开变量，默认为 True。
    :param raw: 是否使用原始匹配方式，默认为 False。原始匹配方式下，不对 VT100 下的 ANSI 颜色进行解码，因此可以匹配颜色；正常匹配仅匹配文本。
    :param priority: 触发器的优先级，值越小优先级越高，默认为 100。
    :param oneShot: 触发器是否只触发一次后自动失效，默认为 False。
    :param args: 可变位置参数，用于传递额外的参数。
    :param kwargs: 可变关键字参数，用于传递额外的键值对参数。
    :return: PymudDecorator 实例，类型为 "trigger"。
    """
    # 将传入的参数更新到 kwargs 字典中
    kwargs.update({
        "patterns": patterns,
        "id": id, 
        "group": group, 
        "enabled": enabled, 
        "ignoreCase": ignoreCase, 
        "isRegExp": isRegExp, 
        "keepEval": keepEval, 
        "expandVar": expandVar, 
        "raw": raw,
        "priority": priority, 
        "oneShot": oneShot})
    if not id:
        kwargs.pop("id")
    return PymudDecorator("trigger", *args, **kwargs)

def timer(timeout: float, id: Optional[str] = None, group: str = "", enabled: bool = True, *args, **kwargs):
    """
    使用装饰器创建一个定时器（Timer）对象。

    :param timeout: 定时器超时时间，单位为秒。
    :param id: 定时器对象的唯一标识符，不指定时将自动生成唯一标识符。
    :param group: 定时器所属的组名，默认为空字符串。
    :param enabled: 定时器是否启用，默认为 True。
    :param args: 可变位置参数，用于传递额外的参数。
    :param kwargs: 可变关键字参数，用于传递额外的键值对参数。
    :return: PymudDecorator 实例，类型为 "timer"。
    """
    kwargs.update({
        "timeout": timeout,
        "id": id,
        "group": group,
        "enabled": enabled
        })
    if not id:
        kwargs.pop("id")
    return PymudDecorator("timer", *args, **kwargs)

def gmcp(name: str, group: str = "", enabled: bool = True, *args, **kwargs):
    """
    使用装饰器创建一个GMCP触发器（GMCPTrigger）对象。

    :param name: GMCP触发器的名称。
    :param group: GMCP触发器所属的组名，默认为空字符串。
    :param enabled: GMCP触发器是否启用，默认为 True。
    :param args: 可变位置参数，用于传递额外的参数。
    :param kwargs: 可变关键字参数，用于传递额外的键值对参数。
    :return: PymudDecorator 实例，类型为 "gmcp"。
    """
    kwargs.update({
        "id": name,
        "group": group,
        "enabled": enabled
        })
    
    return PymudDecorator("gmcp", *args, **kwargs)
