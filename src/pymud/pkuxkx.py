# 示例脚本：如何在PyMud中玩PKUXKX

import webbrowser, asyncio, ast
from pymud import Session, IConfig, alias, trigger, timer, gmcp, exception, Trigger, SimpleTrigger, SimpleAlias, GMCPTrigger, Command

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

    @trigger("^[> ]*西门.*")
    async def ontri_westgate(self, id, line, wildcards):
        time = 0
        while time < 3:
            self.session.info("I'm at west gate.")
            await asyncio.sleep(2)
            time += 1

    # 多行触发器示例
    @trigger([r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$'], group = "sys")
    def ontri_hpbrief_3lines(self, id, line, wildcards):
        # 注意注意，此处捕获的额内容在wildcards里都是str类型，直接用下面这种方式赋值的时候，保存的变量也是str类型，因此这种在status_window直接调用并用于计算时，需要另行处理
        var_name = [
        "combat_exp", "potential", "max_neili", "neili", "max_jingli", "jingli", 
        "max_qi", "eff_qi", "qi", "max_jing", "eff_jing", "jing", 
        "vigour/qi", "vigour/yuan", "food", "water", "fighting", "busy"
        ]

        # 因为hpbrief捕获到的是文本，因此尝试进行数字转换，若转换不成功则保留为文本
        for k, v in zip(var_name, wildcards):
            val = v
            try:
                val = ast.literal_eval(v)
            except:
                pass

            self.session.setVariable(k, val)

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

    # 自定义状态栏窗口。该函数会被渲染框架高频调用，请注意不要在该函数中 info 或者执行其他输出信息！！！
    def status_window(self):
        styles = {
            "title"         : "bold",
            "value"         : "lightgreen",
            "value.better"  : "lightcyan",
            "value.worse"   : "yellow",
            "value.worst"   : "red"
        }
        
        try:
            formatted_list = list()

            # line 0. hp bar
            jing        = int(self.session.getVariable("jing", 0))
            effjing     = int(self.session.getVariable("eff_jing", 1))
            maxjing     = int(self.session.getVariable("max_jing", 1))
            jingli      = int(self.session.getVariable("jingli", 0))
            maxjingli   = int(self.session.getVariable("max_jingli", 1))
            qi          = int(self.session.getVariable("qi", 0))
            effqi       = int(self.session.getVariable("eff_qi", 1))
            maxqi       = int(self.session.getVariable("max_qi", 1))
            neili       = int(self.session.getVariable("neili", 0))
            maxneili    = int(self.session.getVariable("max_neili", 1))

            barstyle = "━"
            screenwidth = self.session.application.get_width()
            barlength = screenwidth // 2 - 1
            span = screenwidth - 2 * barlength
            qi_bar   = self.create_status_bar(qi, effqi, maxqi, barlength, barstyle)
            jing_bar = self.create_status_bar(jing, effjing, maxjing, barlength, barstyle)

            formatted_list.extend(qi_bar)
            formatted_list.append(("", " " * span))
            formatted_list.extend(jing_bar)
            formatted_list.append(("", "\n"))

            # line 1. char, menpai, deposit, food, water, exp, pot
            formatted_list.append((styles["title"], "【角色】"))
            formatted_list.append((styles["value"], "{0}({1})".format(self.session.getVariable('name'), self.session.getVariable('id'))))
            formatted_list.append(("", " "))
          
            formatted_list.append((styles["title"], "【食物】"))
            
            food      = int(self.session.getVariable('food', '0'))
            max_food  = int(self.session.getVariable('max_food', 350))
            if food < 100:
                style = styles["value.worst"]
            elif food < 200:
                style = styles["value.worse"]
            elif food < max_food:
                style = styles["value"]
            else:
                style = styles["value.better"]

            formatted_list.append((style, "{}".format(food)))
            formatted_list.append(("", " "))

            formatted_list.append((styles["title"], "【饮水】"))
            water       = int(self.session.getVariable('water', '0'))
            max_water   = int(self.session.getVariable('max_water', 350))
            if water < 100:
                style = styles["value.worst"]
            elif water < 200:
                style = styles["value.worse"]
            elif water < max_water:
                style = styles["value"]
            else:
                style = styles["value.better"]
            formatted_list.append((style, "{}".format(water)))
            formatted_list.append(("", " "))
            formatted_list.append((styles["title"], "【经验】"))
            formatted_list.append((styles["value"], "{}".format(self.session.getVariable('combat_exp'))))
            formatted_list.append(("", " "))
            formatted_list.append((styles["title"], "【潜能】"))
            formatted_list.append((styles["value"], "{}".format(self.session.getVariable('potential'))))
            formatted_list.append(("", " "))

            formatted_list.append((styles["title"], "【门派】"))
            formatted_list.append((styles["value"], "{}".format(self.session.getVariable('family/family_name'))))
            formatted_list.append(("", " "))
            formatted_list.append((styles["title"], "【存款】"))
            formatted_list.append((styles["value"], "{}".format(self.session.getVariable('deposit'))))
            formatted_list.append(("", " "))
            
            # line 2. hp
            # a new-line
            formatted_list.append(("", "\n"))

            formatted_list.append((styles["title"], "【精神】"))
            if effjing < maxjing:
                style = styles["value.worst"]
            elif jing < 0.8 * effjing:
                style = styles["value.worse"]
            else:
                style = styles["value"]
            
            if maxjing == 0: 
                pct1 = pct2 = 0
            else:
                pct1 = 100.0 * jing / maxjing
                pct2 = 100.0 * effjing / maxjing
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(jing, pct1, effjing, pct2)))

            formatted_list.append(("", " "))

            formatted_list.append((styles["title"], "【气血】"))
            if effqi < maxqi:
                style = styles["value.worst"]
            elif qi < 0.8 * effqi:
                style = styles["value.worse"]
            else:
                style = styles["value"]

            if maxqi == 0: 
                pct1 = pct2 = 0
            else:
                pct1 = 100.0 * qi / maxqi
                pct2 = 100.0 * effqi / maxqi
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(qi, pct1, effqi, pct2)))
            formatted_list.append(("", " "))

            # 内力
            formatted_list.append((styles["title"], "【内力】"))
            if neili < 0.6 * maxneili:
                style = styles["value.worst"]
            elif  neili < 0.8 * maxneili:
                style = styles["value.worse"]
            elif neili < 1.2 * maxneili:
                style = styles["value"]   
            else:
                style = styles["value.better"]

            if maxneili == 0: 
                pct = 0
            else:
                pct = 100.0 * neili / maxneili
            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(neili, maxneili, pct)))
            formatted_list.append(("", " "))

            # 精力
            formatted_list.append((styles["title"], "【精力】"))
            if jingli < 0.6 * maxjingli:
                style = styles["value.worst"]
            elif jingli < 0.8 * maxjingli:
                style = styles["value.worse"]
            elif jingli < 1.2 * maxjingli:
                style = styles["value"]   
            else:
                style = styles["value.better"]
            
            if maxjingli == 0: 
                pct = 0
            else:
                pct = 100.0 * jingli / maxjingli

            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(jingli, maxjingli, pct)))
            formatted_list.append(("", " "))
            
            return formatted_list
    
        except Exception as e:
            return f"{e}"
        

class CmdScore(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd.score")
        super().__init__(session, "^(score|sc)$", *args, **kwargs)

    # 因为此处所有对象都是由IConfig自动管理的，在__unload__中若只存在 super().__unload__()时，该函数可以省略
    # def __unload__(self):
    #     super().__unload__()

    @trigger(r'^┌[─]+人物详情[─┬]+┐$', id = "cmd.score.start", group = "cmd.score")
    def start(self, name, line, wildcards):
        self.session.enableGroup("cmd.score", types = [Trigger])

    @trigger(r'^└[─┴]+[^└─┴┘]+[─]+┘$', id = "cmd.score.end", group = "cmd.score")
    def stop(self, name, line, wildcards):
        self.session.enableGroup("cmd.score", enabled = False, types = [Trigger])

    @trigger(r'^│\s+(?:(\S+)\s)+(\S+)\((\S+)\)\s+│.+│$', group = "cmd.score")
    def charinfo(self, name, line, wildcards):
        # 从此行获取角色id和名称信息
        self.session.setVariables(["name", "id"], [wildcards[1], wildcards[2].lower()])

    def getmenpai(self):
        menpai = self.session.getVariable("family/family_name")
        menpai_abbr = "NA"
        
        if menpai:
            if menpai.find('丐帮') >= 0:
                menpai_abbr = "GB"
            elif menpai.find('武当派') >= 0:
                menpai_abbr = "WD"
            elif menpai.find('桃花岛') >= 0:
                menpai_abbr = "TH"
            elif menpai.find('天龙寺') >= 0:
                menpai_abbr = "TL"
            elif menpai.find('灵鹫宫') >= 0:
                menpai_abbr = "LJ"
            elif menpai.find('朝廷') >= 0:
                menpai_abbr = "CT"
            elif menpai.find('明教') >= 0:
                menpai_abbr = "MJ"
            elif menpai.find('古墓') >= 0:
                menpai_abbr = "GM"
            elif menpai.find('星宿') >= 0:
                menpai_abbr = "XX"
            elif menpai.find('无门派') >= 0:
                menpai_abbr = "BX"

        return menpai_abbr

    @trigger(r'^│\s*国籍：\S+\s+户籍：(\S+).+│门派：(\S+)(?:\s\S+)*\s+│$', group = "cmd.score")
    def menpaiinfo(self, name, line, wildcards):
        menpai = wildcards[1]
        self.session.setVariable("family/family_name", menpai)
        self.session.setVariable("menpai", self.getmenpai())

    @trigger(r'^│\s*性别：\S+\s+上线：(\S+).+│师承：(\S+)(?:\s\S+)*\s+│$', group = "cmd.score")
    def logininfo(self, name, line, wildcards):
        self.session.setVariable("loginroom", wildcards[0])

    @trigger(r'^│\s*杀生：\S+\s+│职业：.+│存款：(\S*(?:\s\S+)?)\s+│$', group = "cmd.score")
    def bankinfo(self, name, line, wildcards):
        self.session.setVariable("deposit", wildcards[0])

    @exception
    async def execute(self, cmd = "score", *args, **kwargs):
        self.reset()

        self.session.tris["cmd.score.start"].enabled = True
        await self.session.waitfor(cmd, self.session.tris["cmd.score.end"].triggered())

        return self.SUCCESS


class CmdHp(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd.hp")
        super().__init__(session, "^hp$", *args, **kwargs)

        options = {"group" : "cmd.hp", "enabled" : False}
        self._tris = {
            "start"     : Trigger(session, r"^[┌─]+个人状态[─┬┐]+$", onSuccess = self.hpstart, **options),
            "line1"     : Trigger(session, r'^│【(\S+)】\s*(\d+)\s+/\s*(\d+)\s+\[([^\]]+)\]\s+│\s*【(\S+)】\s*(\d+)\s+/\s*(\d+)\s+\(([^\)]+)\).+', onSuccess = self.hpstatus, **options),
            "line2"     : Trigger(session, r'^│【(\S+)】\s*(\d+)\s+/\s*(\d+)\s+\[([^\]]+)\]\s+│\s*【(\S+)】\s*([\d,KM]+)\s+│', onSuccess = self.hpstatus, **options),
            "status"    : Trigger(session, r'^│.+【(\S+)】\s(\S+)\s+\S+│', raw = True, onSuccess = self.hpstatus, **options),
            "stop"      : Trigger(session, r'^└[─┴]+[^└─┴┘]+[─]+┘$', keeyEval = True, **options),

            "raw_hp"    : GMCPTrigger(session, "GMCP.raw_hp", onSuccess = self.raw_hp, group = "cmd.hp"),
            "raw_sm"    : GMCPTrigger(session, "GMCP.raw_status_me", onSuccess = self.raw_status, group = "cmd.hp"),
        }

    # 此处由于unload时，需要卸载 self._tris 对象，因此不能省略，也不应遗漏 super().__unload__()
    def __unload__(self):
        self.session.delObjects(self._tris)
        super().__unload__()

    def raw_hp(self, id, line, wildcards): 
        hp = wildcards[0]

        if isinstance(hp, dict):
            self.session.vars["qi"] = hp["qi"]["current"]
            self.session.vars["eff_qi"] = hp["qi"]["effective"]
            self.session.vars["max_qi"] = hp["qi"]["max"]

            self.session.vars["jing"] = hp["jing"]["current"]
            self.session.vars["eff_jing"] = hp["jing"]["effective"]
            self.session.vars["max_jing"] = hp["jing"]["max"]

            self.session.vars["jingli"] = hp["jingli"]["current"]
            self.session.vars["max_jingli"] = hp["jingli"]["max"]

            self.session.vars["neili"] = hp["neili"]["current"]
            self.session.vars["max_neili"] = hp["neili"]["max"]

            self.session.vars["food"] = hp["food"]["current"]
            self.session.vars["water"] = hp["water"]["current"]
            self.session.vars["vigour/qi"] = hp["vigour/qi"]["current"]

            self.session.vars["combat_exp"] = hp["combat_exp"]["current"]

            self.info("HP查询hp *执行完毕", "HP")
        
        else:
            self.warning(f"raw_hp * 不是一个dict，而是一个 {type(hp)}, 解析失败")

    def raw_status(self, id, line, wildcards): 
        # raw_status_me 解析
        sm = wildcards[0]

        if isinstance(sm, dict):
            self.session.vars["status_me"] = sm

            self.info("自身查询sm *执行完毕", id)
        else:
            self.warning(f"raw_status_me * 不是一个dict，而是一个 {type(sm)}, 解析失败")

    def hpstart(self, id, line, wildcards):
        self.session.enableGroup("cmd.hp", enabled = True, types = [Trigger])

    def hpstatus(self, id, line, wildcards):
        self.info(line)
        if wildcards[0] == "精神":
            self.session.vars["jing"] = int(wildcards[1])
            self.session.vars["eff_jing"] = int(wildcards[2])
            if wildcards[3] == "100%":
                self.session.vars["max_jing"] = int(wildcards[2])
            self.session.vars["jingli"] = int(wildcards[5])
            self.session.vars["max_jingli"] = int(wildcards[6])

        elif wildcards[0] == "气血":
            self.session.vars["qi"] = int(wildcards[1])
            self.session.vars["eff_qi"] = int(wildcards[2])

            if wildcards[3] == "100%":
                self.session.vars["max_qi"] = int(wildcards[2])
            self.session.vars["neili"] = int(wildcards[5])
            self.session.vars["max_neili"] = int(wildcards[6])
            self.session.vars["jiali"] = int(wildcards[7][2:].strip())

        elif wildcards[0] == "食物":
            self.session.vars["food"] = int(wildcards[1])
            self.session.vars["max_food"] = int(wildcards[2])
            self.session.vars["potential"] = int(wildcards[5])

        elif wildcards[0] == "饮水":
            self.session.vars["water"] = int(wildcards[1])
            self.session.vars["max_water"] = int(wildcards[2])
            self.session.vars["combat_exp"] = int(wildcards[5])

        elif wildcards[0] == "状态":
            self.session.vars["status"] = wildcards[1].split("、")

    @exception
    async def execute(self, cmd = "hp", *args, **kwargs):
        self.reset()
        self._tris["start"].enabled = True
        await self.session.waitfor(cmd, self._tris["stop"].triggered())
        self.session.enableGroup("cmd.hp", enabled = False, types = [Trigger])
        return self.SUCCESS
