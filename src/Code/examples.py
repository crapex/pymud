# 示例脚本：如何在PyMud中玩PKUXKX

import webbrowser
from pymud import Alias, Trigger, SimpleCommand, Timer, SimpleTrigger, SimpleAlias

# 在PyMud中，使用#load {filename}可以加载对应的配置作为脚本文件以提供支撑。支持多脚本加载
# 本示例脚本对PyMud支持的变量(Variable)、触发器(Trigger，包含单行与多行触发)、别名(Alias)、定时器(Timer)、命令(Command，本示例中使用了SimpleCommand子类)都进行了代码示例
# 使用#load {filename}加载的配置文件中，若有一个类型名为Coniguration，则在#load操作时，会自动创建此类型；若没有Configuration类，则仅将文件引入
# 例如，加载本文件指定的配置，则使用 #load pymud.pkuxkx即可

# PyMud中，触发器Trigger、别名Alias、命令Command，都是匹配对象(MatchObject)的子类，使用同一种处理逻辑
# 匹配对象，意味着有匹配的pattern。在匹配对象成功后，会调用对象的onSuccess方法
# Trigger、Alias仅有成功，即仅onSuccess方法会被调用，该方法参数参考了MushClient，会传递name, line, wildcards三个参数，含义与MushClient相同；


class Configuration:

    # hpbrief long情况下的含义
    HP_KEYS = (
        "exp", "pot", "maxneili", "neili", "maxjingli", "jingli", 
        "maxqi", "effqi", "qi", "maxjing", "effjing", "jing", 
        "zhenqi", "zhenyuan", "food", "water", "fighting", "busy"
        )

    # 类的构造函数，传递参数session，是会话本身
    def __init__(self, session) -> None:
        self.session = session
        self._triggers = {}
        self._commands = {}
        self._aliases  = {}
        self._timers   = {}

        self._initTriggers()
        self._initCommands()
        self._initAliases()
        self._initTimers()

    def _initTriggers(self):
        '''
        初始化触发器。
        本示例中创建了2个触发器，分别对应fullme的链接触发自动打开浏览器访问该网址，以及hpbrief命令的触发器
        '''
        # Trigger的构造函数中，给定的位置参数仅有session(会话)和pattern(匹配模式)两个，其他所有参数都是使用命名参数进行实现
        # 支持的命名参数详细可参见 BaseObject与MatchObject 的构造方法，此处简单列举
        # id         : 唯一标识，不指定时自动生成
        # group      : 组名，不指定时为空
        # enabled    : 使能状态，默认True
        # priority   : 优先级，默认100，越小越高
        # oneShot    : 单次匹配，默认False
        # ignoreCase : 忽略大小写，默认False
        # isRegExp   : 正则表达式模式，默认True
        # keepEval   : 持续匹配，默认False
        # raw        : 原始匹配方式，默认False。原始匹配方式下，不对VT100下的ANSI颜色进行解码，因此可以匹配颜色；正常匹配仅匹配文本
        
        # 1. fullme的链接对应的触发器，匹配URL
        # 当匹配成功后，调用ontri_webpage
        self._triggers["tri_webpage"] = self.tri_webpage = Trigger(self.session, id = 'tri_webpage', patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', group = "sys", onSuccess = self.ontri_webpage)
        # 2. fullme的链接对应的触发器，因为要进行多行匹配（3行），因此匹配模式pattern为3个正则表达式模式构成的元组（所有列表类型均可识别），无需像MushClient一样要指定multiline标识和linesToMatch数量
        # 当匹配成功后，调用ontri_hpbrief
        # 特别说明：此处的hpbrief触发匹配，需要set hpbrief long后才可以支持
        self._triggers["tri_hp"]      = self.tri_hp      = Trigger(self.session, id = 'tri_hpbrief', patterns = (r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$',), group = "sys", onSuccess = self.ontri_hpbrief)
        
        # 3. 现在支持简单Trigger了，例如
        self._triggers["tri_gem"] = SimpleTrigger(self.session ,r'^[> ]*从.+身上.+[◎☆★].+', "pack gem", group = "sys")

        self.session.addTriggers(self._triggers)


    def _initCommands(self):
        '''初始化命令，本示例中创建了1个命令，支持hpbrief命令'''

        # Command是异步执行的命令，可以理解为Alias+Trigger+Timer的组合。在MUD中发出一条命令后，会有成功、失败、超时的不同状态，在这三种状态下，会分别调用onSuccess、onFailure、onTimeout方法
        # 举个Command的应用例子说明：加入把移动（s/e/n/w等等）实现为一个Command。
        # 1. 当向某个方向移动时，成功的时候会移动到下一个房间；
        # 2. 不成功的时候，会出现“这个方向没有出路”等描述；
        # 3. 而当角色处于晕倒状态时，移动命令是不会有任何反应的，超出设定超时时间之后，会调用onTimeout
        # 在上述实现情况下，我们在执行命令时，可以明确的根据命令的执行结果再判断下一步该做什么
        # 本示例使用了简单命令SimpleCommand，其在MatchObject的基础上，增加了以下参数：
        # 1. succ_tri: 命令执行成功时的触发器，不能为空
        # 2. fail_tri: 命令执行失败时的触发器，可以为空
        # 3. retry_tri: 需要重新尝试命令的触发器，可以为空（仍以移动为例，当向某个方向移动，出现“你现在正忙着呢”之后，可以在等待2s之后，再次尝试该命令，知道到达最大尝试次数

        # 命令可以同步调用，也可以在异步函数（async）中使用await语法异步调用
        # 例如，下面的hpbrief可以在这样使用：
        # self.session.exec_command("hpbrief")
        # self.session.exec_command_after(2, "hpbrief")
        # await self.cmd_hpbrief.execute("hpbrief")

        # 异步实现意味着，在函数实现过程中可以以循环实现，而不是以回调实现，有利于代码的可读性
        # 假设已经实现了一个 cmd_move 的 Command，现在要从ct 执行"s;s;w"行走指令到达春来茶馆，然后根据当前的hpbrief结果判断是否需要drink，然后走回中央广场，可以在函数中这样实现：
        # async def gotodrink(self):
        #     for step in "s;s;w".split(";"):
        #         await self.cmd_move.execute(step)
        #         await self.cmd_hpbrief.execute("hpbrief")
        #     await asyncio.sleep(1)
        #     water = self.session.getVariable("water")
        #     if int(water) < 300:
        #         self.session.writeline("drink")
        #     await asyncio.sleep(1)
        #     for step in "e;n;n".split(";"):
        #         await self.cmd_move.execute(step)


        self._commands['cmd_hpbrief']    = self.cmd_hpbrief     = SimpleCommand(self.session, id = "cmd_hpbrief", patterns = "^hpbrief$", succ_tri = self.tri_hp, group = "status", onSuccess = self.oncmd_hpbrief)
        self.session.addCommands(self._commands)

    def _initAliases(self):
        '''初始化别名，本示例中创建了1个别名，是get xxx from corpse'''

        #  get xxx from corpse的别名操作，匹配成功后会自动调用getfromcorpse函数
        #  例如， gp silver 相当于 get silver from corpse
        self._aliases['ali_get'] = Alias(self.session, r"^gp\s(.+)$", id = "ali_get", onSuccess = self.getfromcorpse)

        # 3. 现在支持简单Alias了，在其中也可以支持#wait（缩写为#wa操作）等待，当然，Trigger也支持
        # 从扬州中心广场到西门的行走，每步中间插入100ms等待
        self._aliases["ali_yz_xm"] = SimpleAlias(self.session ,'^yz_xm$', "w;#wa 100;w;#wa 100;w;#wa 100;w", group = "sys")

        self.session.addAliases(self._aliases)

    def _initTimers(self):
        '''初始化定时器，本示例中创建了1个定时器，每隔2秒打印信息'''

        self._timers["tm_test"] = self.tm_test = Timer(self.session, timeout = 2, id = "tm_test", onSuccess = self.onTimer)
        self.session.addTimers(self._timers)

    def getfromcorpse(self, name, line, wildcards):
        cmd = f"get {wildcards[0]} from corpse"
        self.session.writeline(cmd)

    def onTimer(self, name, *args, **kwargs):
        self.session.info("每2秒都会打印本信息", "定时器测试")

    def ontri_webpage(self, name, line, wildcards):
        webbrowser.open(line)

    def ontri_hpbrief(self, name, line, wildcards):
        self.session.setVariables(self.HP_KEYS, wildcards)

    def oncmd_hpbrief(self, name, cmd, line, wildcards):
        # 为了节省服务器资源，应使用hpbrief来代替hp指令
        # 但是hpbrief指令的数据看起来太麻烦，所以将hpbrief的一串数字输出成类似hp的样式
        # ┌───个人状态────────────────────┬─────────────────────────────┐
        # │【精神】 1502    / 1502     [100%]    │【精力】 4002    / 4002    (+   0)    │
        # │【气血】 2500    / 2500     [100%]    │【内力】 5324    / 5458    (+   0)    │
        # │【真气】 0       / 0        [  0%]    │【禅定】 101%               [正常]    │
        # │【食物】 222     / 400      [缺食]    │【潜能】 36,955                       │
        # │【饮水】 247     / 400      [缺水]    │【经验】 2,341,005                    │
        # ├─────────────────────────────┴─────────────────────────────┤
        # │【状态】 健康、怒                                                             │
        # └────────────────────────────────────────────北大侠客行────────┘
        var1 = self.session.getVariables(("jing", "effjing", "maxjing", "jingli", "maxjingli"))
        line1 = "【精神】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【精力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var1[0], var1[1], 100 * float(var1[1]) / float(var1[2]), var1[3], var1[4], 100 * float(var1[0]) / float(var1[2]), 100 * float(var1[3]) / float(var1[4]))
        var2 = self.session.getVariables(("qi", "effqi", "maxqi", "neili", "maxneili"))
        line2 = "【气血】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【内力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var2[0], var2[1], 100 * float(var2[1]) / float(var2[2]), var2[3], var2[4], 100 * float(var2[0]) / float(var2[2]), 100 * float(var2[3]) / float(var2[4]))
        var3 = self.session.getVariables(("food", "water", "exp", "pot", "fighting", "busy"))
        line3 = "【食物】 {0:<4} 【饮水】{1:<4} 【经验】{2:<9} 【潜能】{3:<10}【{4}】【{5}】".format(var3[0], var3[1], var3[2], var3[3],  "未战斗" if var3[4] == "0" else "战斗中", "不忙" if var3[5] == "0" else "忙")
        self.session.info(line1, "状态")
        self.session.info(line2, "状态")
        self.session.info(line3, "状态")
