
import importlib, importlib.util
from abc import ABC, ABCMeta
from typing import Any
from .objects import BaseObject, Command, Trigger, Alias, Timer, GMCPTrigger
from .settings import Settings
from .extras import DotDict

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
        return self

    def __repr__(self):
        return f"<{self.__class__.__name__} type = {self.type} args = {self.args} kwargs = {self.kwargs}>"


def alias(patterns, id = None, group = "", enabled = True, ignoreCase = False, isRegExp = True, keepEval = False, expandVar = True, priority = 100, oneShot = False,  *args, **kwargs):
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
def trigger(patterns, id = None, group = "", enabled = True, ignoreCase = False, isRegExp = True, keepEval = False, expandVar = True, raw = False, priority = 100, oneShot = False,  *args, **kwargs):
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

def timer(timeout, *args, **kwargs):
    kwargs.update({"timeout": timeout})
    return PymudDecorator("timer", *args, **kwargs)

def gmcp(name, *args, **kwargs):
    kwargs.update({"id": name})
    return PymudDecorator("gmcp", *args, **kwargs)
class PymudMeta(type):
    def __new__(cls, name, bases, attrs):
        decorator_funcs = {}
        for name, value in attrs.items():
            if hasattr(value, "__pymud_decorators__"):
                decorator_funcs[value.__name__] = getattr(value, "__pymud_decorators__", [])
                
        attrs["_decorator_funcs"] = decorator_funcs

        return super().__new__(cls, name, bases, attrs)
    
class ModuleInfo:
    """
    模块管理类。对加载的模块文件进行管理。该类型由Session类进行管理，无需人工创建和干预。

    有关模块的分类和使用的详细信息，请参见 `脚本 <scripts.html>`_

    :param module_name: 模块的名称, 应与 import xxx 语法中的 xxx 保持一致
    :param session: 加载/创建本模块的会话

    """
    def __init__(self, module_name: str, session):
        self.session = session
        self._name = module_name 
        self._ismainmodule = False
        self.load()
       
    def _load(self, reload = False):
        result = True
        if reload:
            self._module = importlib.reload(self._module)
        else:
            self._module = importlib.import_module(self.name)
        self._config = {}
        for attr_name in dir(self._module):
            attr = getattr(self._module, attr_name)
            if isinstance(attr, type) and attr.__module__ == self._module.__name__:
                if (attr_name == "Configuration") or issubclass(attr, IConfig):
                    try:
                        self._config[f"{self.name}.{attr_name}"] = attr(self.session, reload = reload)
                        if not reload:
                            self.session.info(Settings.gettext("configuration_created", self.name, attr_name))
                        else:
                            self.session.info(Settings.gettext("configuration_recreated", self.name, attr_name))

                    except Exception as e:
                        result = False
                        self.session.error(Settings.gettext("configuration_fail", self.name, attr_name, e))
        self._ismainmodule = (self._config != {})
        return result
    
    def _unload(self):
        for key, config in self._config.items():
            if isinstance(config, Command):
                # Command 对象在从会话中移除时，自动调用其 unload 系列方法，因此不能产生递归
                self.session.delObject(config)
            
            else:

                if hasattr(config, "__unload__"):
                    unload = getattr(config, "__unload__", None)
                    if callable(unload): unload()
                    
                if hasattr(config, "unload"):
                    unload = getattr(config, "unload", None)
                    if callable(unload): unload()

                if isinstance(config, BaseObject):
                    self.session.delObject(config)

            del config
        self._config.clear()

    def load(self):
        "加载模块内容"
        if self._load():
            self.session.info(f"{Settings.gettext('entity_module' if self.ismainmodule else 'non_entity_module')} {self.name} {Settings.gettext('load_ok')}")
        else:
            self.session.info(f"{Settings.gettext('entity_module' if self.ismainmodule else 'non_entity_module')} {self.name} {Settings.gettext('load_fail')}")

    def unload(self):
        "卸载模块内容"
        self._unload()
        self._loaded = False
        self.session.info(f"{Settings.gettext('entity_module' if self.ismainmodule else 'non_entity_module')} {self.name} {Settings.gettext('unload_ok')}")

    def reload(self):
        "模块文件更新后调用，重新加载已加载的模块内容"
        self._unload()
        self._load(reload = True)
        self.session.info(f"{Settings.gettext('entity_module' if self.ismainmodule else 'non_entity_module')} {self.name} {Settings.gettext('reload_ok')}")

    @property
    def name(self):
        "只读属性，模块名称"
        return self._name

    @property
    def module(self):
        "只读属性，模块文件的 ModuleType 对象"
        return self._module
    
    @property
    def config(self):
        "只读字典属性，根据模块文件 ModuleType 对象创建的其中名为 Configuration 的类型或继承自 IConfig 的子类型实例（若有）"
        return self._config
    
    @property
    def ismainmodule(self):
        "只读属性，区分是否主模块（即包含具体config的模块）"
        return self._ismainmodule

class IConfig(metaclass = PymudMeta):
    """
    用于提示PyMUD应用是否自动创建该配置类型的基础类（模拟接口）。
    
    继承 IConfig 类型让应用自动管理该类型，唯一需要的是，构造函数中，仅存在一个必须指定的参数 Session。

    在应用自动创建 IConfig 实例时，除 session 参数外，还会传递一个 reload 参数 （bool类型），表示是首次加载还是重新加载特性。
    可以从kwargs 中获取该参数，并针对性的设计相应代码。例如，重新加载相关联的其他模块等。
    """
    def __init__(self, session, *args, **kwargs):
        from .session import Session
        if isinstance(session, Session):
            self.session = session
        self.__inline_objects__ = DotDict()

        if hasattr(self, "_decorator_funcs"):
            for func_name, decorators in self._decorator_funcs.items():
                func = getattr(self, func_name)
                for deco in decorators:
                    if isinstance(deco, PymudDecorator):
                        if deco.type == "alias":
                            patterns = deco.kwargs.pop("patterns")
                            ali = Alias(self.session, patterns, *deco.args, **deco.kwargs, onSccess = func)
                            self.__inline_objects__[ali.id] = ali
                        
                        elif deco.type == "trigger":
                            patterns = deco.kwargs.pop("patterns")
                            tri = Trigger(self.session, patterns, *deco.args, **deco.kwargs, onSuccess = func)
                            self.__inline_objects__[tri.id] = tri

                        elif deco.type == "timer":
                            tim = Timer(self.session, *deco.args, **deco.kwargs, onSuccess = func)
                            self.__inline_objects__[tim.id] = tim

                        elif deco.type == "gmcp":
                            gmcp = GMCPTrigger(self.session, deco.kwargs.get("id"), *deco.args, **deco.kwargs, onSuccess = func)
                            self.__inline_objects__[gmcp.id] = gmcp

    def __unload__(self):
        if self.session:
            self.session.delObjects(self.__inline_objects__)
            if isinstance(self, BaseObject):
                self.session.delObject(self)

    @property
    def objs(self) -> DotDict:
        "返回内联自动创建的对象字典"
        return self.__inline_objects__
    
    def obj(self, obj_id: str) -> BaseObject:
        "根据对象ID返回内联自动创建的对象"
        return self.__inline_objects__.get(obj_id)

class Plugin:
    """
    插件管理类。对加载的插件文件进行管理。该类型由PyMudApp进行管理，无需人工创建。

    有关插件的详细信息，请参见 `插件 <plugins.html>`_

    :param name: 插件的文件名, 如'myplugin.py'
    :param location: 插件所在的目录。自动加载的插件包括PyMUD包目录下的plugins目录以及当前目录下的plugins目录

    """
    def __init__(self, name, location):
        self._plugin_file = name
        self._plugin_loc  = location

        self.reload()

    def reload(self):
        "加载/重新加载插件对象"
        #del self.modspec, self.mod
        self.modspec = importlib.util.spec_from_file_location(self._plugin_file[:-3], self._plugin_loc)
        self.mod     = importlib.util.module_from_spec(self.modspec)
        self.modspec.loader.exec_module(self.mod)
        
        # self._app_init = self.mod.__dict__["PLUGIN_PYMUD_START"]
        # self._session_create = self.mod.__dict__["PLUGIN_SESSION_CREATE"]
        # self._session_destroy = self.mod.__dict__["PLUGIN_SESSION_DESTROY"]
        # self._app_destroy = self.mod.__dict__["PLUGIN_PYMUD_DESTROY"]
        self._app_init = self._load_mod_function("PLUGIN_PYMUD_START")
        self._session_create = self._load_mod_function("PLUGIN_SESSION_CREATE")
        self._session_destroy = self._load_mod_function("PLUGIN_SESSION_DESTROY")
        self._app_destroy = self._load_mod_function("PLUGIN_PYMUD_DESTROY")
        
    def _load_mod_function(self, func_name):
        # 定义一个默认函数，当插件文件中未定义指定名称的函数时，返回该函数
        # 该函数接受任意数量的位置参数和关键字参数，但不执行任何操作
        def default_func(*args, **kwargs):
            pass

        result = default_func
        if func_name in self.mod.__dict__:
            func = self.mod.__dict__[func_name]
            if callable(func):
                result = func
        return result

    @property
    def name(self):
        "插件名称，由插件文件中的 PLUGIN_NAME 常量定义"
        return self.mod.__dict__["PLUGIN_NAME"]
    
    @property
    def desc(self):
        "插件描述，由插件文件中的 PLUGIN_DESC 常量定义"
        return self.mod.__dict__["PLUGIN_DESC"]
    
    @property
    def help(self):
        "插件帮助，由插件文件中的文档字符串定义"
        return self.mod.__doc__
    
    def onAppInit(self, app):
        """
        PyMUD应用启动时对插件执行的操作，由插件文件中的 PLUGIN_PYMUD_START 函数定义

        :param app: 启动的 PyMudApp 对象实例
        """
        self._app_init(app)

    def onSessionCreate(self, session):
        """
        新会话创建时对插件执行的操作，由插件文件中的 PLUGIN_SESSION_CREATE 函数定义

        :param session: 新创建的会话对象实例
        """
        self._session_create(session)

    def onSessionDestroy(self, session):
        """
        会话关闭时（注意不是断开）对插件执行的操作，由插件文件中的 PLUGIN_SESSION_DESTROY 函数定义

        :param session: 所关闭的会话对象实例
        """
        self._session_destroy(session)

    def onAppDestroy(self, app):
        """
        PyMUD应用关闭时对插件执行的操作，由插件文件中的 PLUGIN_PYMUD_DESTROY 函数定义
        :param app: 关闭的 PyMudApp 对象实例
        """
        self._app_destroy(app)

    def __getattr__(self, __name: str) -> Any:
        if hasattr(self.mod, __name):
            return self.mod.__getattribute__(__name)