
import importlib
from abc import ABC, ABCMeta

class ModuleInfo:
    def __init__(self, module_name: str, session):
        self.session = session
        self._name = module_name 
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
                        self._config[f"{self.name}.{attr_name}"] = attr(self.session)
                        self.session.info(f"配置对象 {self.name}.{attr_name} 创建成功.")
                    except Exception as e:
                        result = False
                        self.session.error(f"配置对象 {self.name}.{attr_name} 创建失败. 错误信息为: {e}")

        return result
    
    def _unload(self):
        for key, config in self._config.items():
            if hasattr(config, "__unload__"):
                unload = getattr(config, "__unload__", None)
                if callable(unload): unload()
                
            if hasattr(config, "unload"):
                unload = getattr(config, "unload", None)
                if callable(unload): unload()

            del config
        self._config.clear()

    def load(self):
        if self._load():
            self.session.info(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 加载完成.")
        else:
            self.session.error(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 加载失败.")

    def unload(self):
        self._unload()
        self.session.info(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 卸载完成.")

    def reload(self):
        self._unload()
        self._load(reload = True)
        self.session.info(f"{'主' if self.ismainmodule else '从'}配置模块 {self.name} 重新加载完成.")

    @property
    def name(self):
        return self._name

    @property
    def module(self):
        return self._module
    
    @property
    def config(self):
        return self._config
    
    @property
    def ismainmodule(self):
        return self._config != {}

class IConfig(metaclass = ABCMeta):
    def __init__(self, session, *args, **kwargs):
        self.session = session

    def __unload__(self):
        self.session.delObject(self)
