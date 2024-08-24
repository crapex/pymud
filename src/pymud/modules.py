
import importlib, importlib.util
from abc import ABC, ABCMeta
from typing import Any
from .objects import BaseObject, Command

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
                        self.session.info(f"配置对象 {self.name}.{attr_name} {'重新' if reload else ''}创建成功.")
                    except Exception as e:
                        result = False
                        self.session.error(f"配置对象 {self.name}.{attr_name} 创建失败. 错误信息为: {e}")
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
            self.session.info(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 加载完成.")
        else:
            self.session.error(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 加载失败.")

    def unload(self):
        "卸载模块内容"
        self._unload()
        self._loaded = False
        self.session.info(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 卸载完成.")

    def reload(self):
        "模块文件更新后调用，重新加载已加载的模块内容"
        self._unload()
        self._load(reload = True)
        self.session.info(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 重新加载完成.")

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

class IConfig(metaclass = ABCMeta):
    """
    用于提示PyMUD应用是否自动创建该配置类型的基础类（模拟接口）。
    
    继承 IConfig 类型让应用自动管理该类型，唯一需要的是，构造函数中，仅存在一个必须指定的参数 Session。

    在应用自动创建 IConfig 实例时，除 session 参数外，还会传递一个 reload 参数 （bool类型），表示是首次加载还是重新加载特性。
    可以从kwargs 中获取该参数，并针对性的设计相应代码。例如，重新加载相关联的其他模块等。
    """
    def __init__(self, session, *args, **kwargs):
        self.session = session

    def __unload__(self):
        if self.session:
            self.session.delObject(self)

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

        self._app_init = self.mod.__dict__["PLUGIN_PYMUD_START"]
        self._session_create = self.mod.__dict__["PLUGIN_SESSION_CREATE"]
        self._session_destroy = self.mod.__dict__["PLUGIN_SESSION_DESTROY"]
        
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

    def __getattr__(self, __name: str) -> Any:
        if hasattr(self.mod, __name):
            return self.mod.__getattribute__(__name)