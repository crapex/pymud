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
    # 类的构造函数，传递参数session，是会话本身。另外请保留*args和**kwargs，以便后续扩展
    def __init__(self, session: Session, *args, **kwargs) -> None:
        # 建议将 super().__init__()放在类型init的首句代码，该代码用于对装饰器@alias等函数所装饰的对象进行管理
        # 调用super().__init__()时，会自动将session传递给父类，以便后续使用。
        # 因此此处无需再使用self.session = session来保存传递的会话类型
        # 
        super().__init__(session, *args, **kwargs)

        # 所有自行构建的对象， 建议统一放到self._objs中，方便管理和卸载。
        # 目前加载卸载可以支持字典、列表、单个对象均可。此处使用字典，是为了方便后续处理其中某个单个对象。
        # 对象创建时将自动增加到会话中，不需要手动调用session.addObject操作了
        self._objs = {
            # 别名，触发器可以通过创建一个对应类型的实例来生成
            "tri_gem"   : SimpleTrigger(self.session ,r'^[> ]*从.+身上.+[◎☆★].+', "pack gem", group = "sys"),
            "ali_yz_xm" : SimpleAlias(self.session ,'^yz_xm$', "w;#wa 100;w;#wa 100;w;#wa 100;w", group = "sys")
        }

        # 将自定义的状态窗口函数赋值给会话的status_maker属性，这样会话就会使用该函数来显示状态信息。
        self.session.status_maker = self.status_window

        
    # 如果仅使用了装饰器定义的PyMUD对象（Alias，Trigger等），则无需实现__unload__方法。
    # 但如果自定义了PyMUD对象，那么必须实现__unload__方法，否则会导致加载的对象无法被正常卸载。
    # 如果实现了__unload__方法，那么在该方法中必须调用super().__unload__()，否则会导致@alias等函数装饰器生成的对象不能被正常卸载
    def __unload__(self):
        # 在__unload__方法中定义卸载时需要从会话中清除的对象。
        # 目前加载卸载可以支持字典、列表、单个对象均可。
        self.session.delObjects(self._objs)

        # 不要遗漏 super().__unload__()，否则会导致@alias等函数装饰器生成的对象不能被正常卸载
        super().__unload__()

    # 别名， gp gold = get gold from corpse
    @alias(r"^gp\s(.+)$", id = "ali_get", group = "sys")
    def getfromcorpse(self, id, line, wildcards):
        cmd = f"get {wildcards[0]} from corpse"
        self.session.writeline(cmd)

    # 定时器，每5秒打印一次信息
    @timer(5)
    def onTimer(self, id, *args, **kwargs):
        self.session.info("每5秒都会打印本信息", "定时器测试")

    # 导航触发器示例
    @trigger('^http://fullme.pkuxkx.net/robot.php.+$', group = "sys")
    def ontri_webpage(self, id, line, wildcards):
        webbrowser.open(line)

    # 若多个对象共用同一个处理函数，也可以同时使用多个装饰器实现
    @trigger(r"^\s+你可以获取(.+)")
    @trigger(r"^\s+这里位于(.+)和(.+)的.+")
    def ontri_multideco(self, id, line, wildcards):
        self.session.info("触发器触发，ID: {0}, 内容: {1}, 匹配项: {2}".format(id, line, wildcards), "测试")

    # 多行触发器示例
    @trigger([r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$'], group = "sys")
    def ontri_hpbrief_3lines(self, id, line, wildcards):
        # 注意注意，此处捕获的额内容在wildcards里都是str类型，直接用下面这种方式赋值的时候，保存的变量也是str类型，因此这种在status_window直接调用并用于计算时，需要另行处理
        self.session.setVariables([
        "combat_exp", "potential", "max_neili", "neili", "max_jingli", "jingli", 
        "max_qi", "eff_qi", "qi", "max_jing", "eff_jing", "jing", 
        "vigour/qi", "vigour/yuan", "food", "water", "fighting", "busy"
        ]
        , wildcards)
        # 因为GMCP.Status传递来的是busy和fighting，与hpbrief逻辑相反，因此重新处理下，保证hpbrief和GMCP.Status一致
        is_busy = not wildcards[-1]
        is_fighting = not wildcards[-2]
        self.session.setVariables(['is_busy', 'is_fighting'], [is_busy, is_fighting])

    # gmcp定义式，name的大小写必须与GMCP的大小写一致，否则无法触发
    @gmcp("GMCP.Status")
    def ongmcp_status(self, id, line, wildcards):
        # GMCP.Status in pkuxkx
        # 自己的Status和敌人的Status均会使用GMCP.Status发送
        # 区别在于，敌人的Status会带有id属性。但登录首次自己也会发送id属性，但同时有很多属性，因此增加一个实战经验属性判定
        if isinstance(wildcards, dict):     # 正常情况下，GMCP.Status应该是一个dict
            if ("id" in wildcards.keys()) and (not "combat_exp" in wildcards.keys()):
                # 说明是敌人的，暂时忽略
                #self.session.info(f"GMCP.Status 收到非自己信息： {wildcards}")
                pass

            else:
                # GMCP.status收到的wildcards是一个json格式转换过来的字典信息，可以直接用于变量赋值
                # 但json过来的true/false时全小写字符串，此处转换为bool类型使用
                #self.session.info(f"GMCP.Status 收到个人信息： {wildcards}")
                for key, value in wildcards.items():
                    if value == "false": value = False
                    elif value == "true": value = True
                    self.session.setVariable(key, value)

        # 如果这些变量显示在状态窗口中，可以调用下面代码强制刷新状态窗口
        self.session.application.invalidate()

    # 创建自定义的健康条用作分隔符
    def create_status_bar(self, current, effective, maximum, barlength = 20, barstyle = "—"):
        from wcwidth import wcswidth
        barline = list()
        stylewidth = wcswidth(barstyle)
        filled_length = int(round(barlength * current / maximum / stylewidth))
        # 计算有效健康值部分的长度
        effective_length = int(round(barlength * effective / maximum / stylewidth))

        # 计算剩余部分长度
        remaining_length = barlength - effective_length

        # 构造健康条
        barline.append(("fg:lightcyan", barstyle * filled_length))
        barline.append(("fg:yellow", barstyle * (effective_length - filled_length)))
        barline.append(("fg:red", barstyle * remaining_length))

        return barline

    # 自定义状态栏窗口
    def status_window(self):
        from pymud.settings import Settings
        try:
            formatted_list = list()

            # line 0. hp bar
            jing = self.session.getVariable("jing", 0)
            effjing = self.session.getVariable("eff_jing", 0)
            maxjing = self.session.getVariable("max_jing", 0)
            jingli = self.session.getVariable("jingli", 0)
            maxjingli = self.session.getVariable("max_jingli", 0)
            qi = self.session.getVariable("qi", 0)
            effqi = self.session.getVariable("eff_qi", 0)
            maxqi = self.session.getVariable("max_qi", 0)
            neili = self.session.getVariable("neili", 0)
            maxneili = self.session.getVariable("max_neili", 0)

            barstyle = "━"
            screenwidth = self.session.application.get_width()
            barlength = screenwidth // 2 - 1
            span = screenwidth - 2 * barlength
            qi_bar = self.create_status_bar(qi, effqi, maxqi, barlength, barstyle)
            jing_bar = self.create_status_bar(jing, effjing, maxjing, barlength, barstyle)

            formatted_list.extend(qi_bar)
            formatted_list.append(("", " " * span))
            formatted_list.extend(jing_bar)
            formatted_list.append(("", "\n"))

            # line 1. char, menpai, deposit, food, water, exp, pot
            formatted_list.append((Settings.styles["title"], "【角色】"))
            formatted_list.append((Settings.styles["value"], "{0}({1})".format(self.session.getVariable('name'), self.session.getVariable('id'))))
            formatted_list.append(("", " "))
          
            formatted_list.append((Settings.styles["title"], "【食物】"))
            
            food = int(self.session.getVariable('food', '0'))
            max_food = self.session.getVariable('max_food', 350)
            if food < 100:
                style = Settings.styles["value.worst"]
            elif food < 200:
                style = Settings.styles["value.worse"]
            elif food < max_food:
                style = Settings.styles["value"]
            else:
                style = Settings.styles["value.better"]

            formatted_list.append((style, "{}".format(food)))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【饮水】"))
            water = int(self.session.getVariable('water', '0'))
            max_water = self.session.getVariable('max_water', 350)
            if water < 100:
                style = Settings.styles["value.worst"]
            elif water < 200:
                style = Settings.styles["value.worse"]
            elif water < max_water:
                style = Settings.styles["value"]
            else:
                style = Settings.styles["value.better"]
            formatted_list.append((style, "{}".format(water)))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【经验】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('combat_exp'))))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【潜能】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('potential'))))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【门派】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('family/family_name'))))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【存款】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('deposit'))))
            formatted_list.append(("", " "))
            
            # line 2. hp
            # a new-line
            formatted_list.append(("", "\n"))

            formatted_list.append((Settings.styles["title"], "【精神】"))
            if int(effjing) < int(maxjing):
                style = Settings.styles["value.worst"]
            elif int(jing) < 0.8 * int(effjing):
                style = Settings.styles["value.worse"]
            else:
                style = Settings.styles["value"]
            
            if maxjing == 0: 
                pct1 = pct2 = 0
            else:
                pct1 = 100.0*float(jing)/float(maxjing)
                pct2 = 100.0*float(effjing)/float(maxjing)
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(jing, pct1, effjing, pct2)))

            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【气血】"))
            if int(effqi) < int(maxqi):
                style = Settings.styles["value.worst"]
            elif int(qi) < 0.8 * int(effqi):
                style = Settings.styles["value.worse"]
            else:
                style = Settings.styles["value"]

            if maxqi == 0: 
                pct1 = pct2 = 0
            else:
                pct1 = 100.0*float(qi)/float(maxqi)
                pct2 = 100.0*float(effqi)/float(maxqi)
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(qi, pct1, effqi, pct2)))
            formatted_list.append(("", " "))

            # 内力
            formatted_list.append((Settings.styles["title"], "【内力】"))
            if int(neili) < 0.6 * int(maxneili):
                style = Settings.styles["value.worst"]
            elif int(neili) < 0.8 * int(maxneili):
                style = Settings.styles["value.worse"]
            elif int(neili) < 1.2 * int(maxneili):
                style = Settings.styles["value"]   
            else:
                style = Settings.styles["value.better"]

            if maxneili == 0: 
                pct = 0
            else:
                pct = 100.0*float(neili)/float(maxneili)
            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(neili, maxneili, pct)))
            formatted_list.append(("", " "))

            # 精力
            formatted_list.append((Settings.styles["title"], "【精力】"))
            if int(jingli) < 0.6 * int(maxjingli):
                style = Settings.styles["value.worst"]
            elif int(jingli) < 0.8 * int(maxjingli):
                style = Settings.styles["value.worse"]
            elif int(jingli) < 1.2 * int(maxjingli):
                style = Settings.styles["value"]   
            else:
                style = Settings.styles["value.better"]
            
            if maxjingli == 0: 
                pct = 0
            else:
                pct = 100.0*float(jingli)/float(maxjingli)

            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(jingli, maxjingli, pct)))
            formatted_list.append(("", " "))
            
            return formatted_list
    
        except Exception as e:
            return f"{e}"