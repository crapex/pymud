# 示例脚本：如何在PyMud中玩PKUXKX

import webbrowser
from pymud import Session, IConfig, alias, trigger, timer, gmcp, Alias, Trigger, Timer, SimpleTrigger, SimpleAlias

# 在PyMud中，使用#load {filename}可以加载对应的配置作为脚本文件以提供支撑。支持多脚本加载
# 本示例脚本对PyMud支持的变量(Variable)、触发器(Trigger，包含单行与多行触发)、别名(Alias)、定时器(Timer)进行了代码示例
# 使用#load {filename}加载的配置文件中，若有一个类型继承自IConfig，则在#load操作时，会自动创建此类型；若没有继承自IConfig的类，则仅将文件引入
# 例如，加载本文件指定的配置，则使用 #load pymud.pkuxkx即可

# 定义一个自定义配置类，并继承自IConfig。
# 目前不在推荐使用Configuration类，而是使用IConfig接口。因为只有使用IConfig接口，才能在类型函数中自动管理由装饰器创建的对象
class MyConfig(IConfig):

    # hpbrief long情况下的含义
    HP_KEYS = (
        "combat_exp", "potential", "max_neili", "neili", "max_jingli", "jingli", 
        "max_qi", "eff_qi", "qi", "max_jing", "eff_jing", "jing", 
        "vigour/qi", "vigour/yuan", "food", "water", "fighting", "busy"
        )

    # 类的构造函数，传递参数session，是会话本身。另外请保留*args和**kwargs，以便后续扩展
    def __init__(self, session: Session, *args, **kwargs) -> None:
        self.session = session
        # 所有自行构建的对象， 统一放到self._objs中，方便管理和卸载。
        # 目前加载卸载可以支持字典、列表、单个对象均可。此处使用字典，是为了方便后续处理其中某个单个对象。
        # 对象创建时将自动增加到会话中，不需要手动调用session.addObject操作了
        self._objs = {
            # 别名，触发器可以通过创建一个对应类型的实例来生成
            "tri_gem": SimpleTrigger(self.session ,r'^[> ]*从.+身上.+[◎☆★].+', "pack gem", group = "sys"),
            "ali_yz_xm": SimpleAlias(self.session ,'^yz_xm$', "w;#wa 100;w;#wa 100;w;#wa 100;w", group = "sys")
        }

        # 不要遗漏 super().__init__()，否则会导致@alias等函数装饰器不能正常创建对象
        super().__init__(session, *args, **kwargs)

    def __unload__(self):
        # 在__unload__方法中定义卸载时需要从会话中清除的对象。
        # 目前加载卸载可以支持字典、列表、单个对象均可。
        self.session.delObjects(self._objs)

        # 不要遗漏 super().__unload__()，否则会导致@alias等函数装饰器生成的对象不能被正常卸载
        super().__unload__()

    @trigger('^http://fullme.pkuxkx.net/robot.php.+$', group = "sys")
    def ontri_webpage(self, id, line, wildcards):
        webbrowser.open(line)

    @alias(r"^gp\s(.+)$", id = "ali_get", group = "sys")
    def getfromcorpse(self, id, line, wildcards):
        cmd = f"get {wildcards[0]} from corpse"
        self.session.writeline(cmd)

    @timer(2)
    def onTimer(self, id, *args, **kwargs):
        self.session.info("每2秒都会打印本信息", "定时器测试")

    @trigger(id = 'tri_hpbrief', patterns = (r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$',), group = "sys")
    def ontri_hpbrief(self, id, line, wildcards):
        self.session.setVariables(self.HP_KEYS, wildcards)


    # 若多个对象共用同一个处理函数，也可以同时使用多个装饰器实现
    @trigger(r"^\s+你可以获取(.+)")
    @trigger(r"^\s+这里位于(.+)和(.+)的.+")
    def ontri_multideco(self, id, line, wildcards):
        self.session.info("触发器触发，ID: {0}, 内容: {1}, 匹配项: {2}".format(id, line, wildcards), "测试")
