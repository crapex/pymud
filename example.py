"用于处理PKUXKX的环境"
import re, asyncio, random, math, webbrowser, traceback
from collections import namedtuple

from objects import Alias, Trigger, Command, SimpleCommand


class Configuration:
    # set hpbrief long情况下的含义
    HP_KEYS = (
        "exp", "pot", "maxneili", "neili", "maxjingli", "jingli", 
        "maxqi", "effqi", "qi", "maxjing", "effjing", "jing", 
        "zhenqi", "zhenyuan", "food", "water", "fighting", "busy"
        )

    FOODS = ("baozi", "gan liang", "jitui", "doufu", "gou rou", "furong huagu", "shanhu baicai", "bocai fentiao", "liuli qiezi", "mala doufu", "nuomi zhou", "tian ji", "yin si", "xunyang yupian", "shizi tou", "mifen zhengrou", "dian xin", "gao")
    DRINKS = ("jiudai", "jiu dai" "hulu", "wan", "niurou tang", "qingshui hulu", "mudan cha", "haoqiu tang", "suanmei tang")
    MONEY = ("gold", "silver", "coin", "thousand-cash")
    SELLS = ('cai bao', 'xiuhua zhen', 'changjian', 'duanjian', 'jian', 'chang jian', 'armor', 'blade', 'dao', 'xiao lingdang', 'fangtian ji', 'jun fu', 'junfu', 'changqiang', 'chang qiang', 'tie bishou', 'chang bian', 'qingwa tui', 'nen cao', 'sui rouxie', 'cao zi', 'yu xiao', 'gangzhang', 'golden ring', 'golden necklace', 'heise pifeng', 'pink cloth')
    SELLS_DESC = ('财宝', '长剑', '短剑', '钢剑', '铁甲', '钢刀', '武士刀', '小铃铛', '方天画戟', '军服', '长枪', '铁匕首', '长鞭', '玉箫', '钢杖', '黑色披风', '金戒指', '金项链', '青蛙腿', '嫩草', '碎肉屑', '草籽', '粉红绸衫', '绣花针')
    TRASH = ('xiao lingdang', 'bone', 'iron falun', 'shi tan', 'yun tie', 'huo tong', 'xuan bing',) 

    Inventory = namedtuple('Inventory', ("id", "name", "count"))

    splits_ch = ('亿', '万', '千', '百', '十')
    splits_val = (100000000, 10000, 1000, 100, 10)

    @classmethod
    def hz2number(cls, hz):
        "将中文汉字转化为对应的数字"
        return '零一二三四五六七八九'.find(hz)

    @classmethod
    def word2number(cls, word: str, split_idx = 0):
        "将中文汉字串转化为对应的数"
        split_ch = cls.splits_ch[split_idx]
        split_val = cls.splits_val[split_idx]
        
        if not word:
            return 0

        pos = word.find(split_ch)
        if pos >= 0:
            left = word[:pos]
            right = word[pos+1:]
            
            if not left:
                left_num = 1
            else:
                if split_idx < len(cls.splits_ch) - 1:
                    left_num = cls.word2number(left, split_idx + 1)
                else:
                    left_num = cls.hz2number(left.replace('零', ''))
                    
            if not right:
                right_num = 0
            else:
                if split_idx < len(cls.splits_ch) - 1:
                    right_num = cls.word2number(right, split_idx + 1)
                else:
                    right_num = cls.hz2number(right.replace('零', ''))
                    
            val = left_num * split_val + right_num
        else:
            if split_idx < len(cls.splits_ch) - 1:
                val = cls.word2number(word, split_idx + 1)
            else:
                val = cls.hz2number(word.replace('零', ''))
                
        return val 

    @classmethod
    def money2str(cls, coin):
        "将游戏中的钱转化为字符串"
        if coin == 0:
            return "不花钱"
    
        gold = math.floor(coin/10000)
        coin = coin - (gold * 10000)
        silver = math.floor(coin/100)
        coin = coin - (silver * 100)

        goldStr = '{0:.0f}锭黄金'.format(gold) if gold > 0 else ''
        silverStr = '{0:.0f}两白银'.format(silver) if silver > 0 else ''
        coinStr = '{0:.0f}文铜板'.format(coin) if coin > 0 else ''

        return "{}{}{}".format(goldStr, silverStr, coinStr)


    class CmdLifeMisc(Command):
        def __init__(self, session, cmd_inv, *args, **kwargs):
            super().__init__(session, "^(sellall|convertall|saveall|savegold|feed|liaoshang)$", *args, **kwargs)
            self._cmdInventory = cmd_inv

            self._triggers = {}
            self._initTriggers()

        def _initTriggers(self):       
            self._triggers["eat_none"]   = Trigger(self.session, r'^[> ]*你将剩下的.*吃得干干净净', id = "eat_none", group = "life", onSuccess = self.oneatnone)
            self._triggers["eat_next"]   = Trigger(self.session, r'^[> ]*你拿起.+咬了几口。|^[> ]*你捧起.*狠狠地喝了几口。', id = "eat_next", group = "life", onSuccess = self.oneat)
            self._triggers["eat_done"]   = Trigger(self.session, r'^[> ]*你已经吃太饱了，再也塞不下任何东西了', id = "eat_done", group = "life")
            self._triggers["drink_none"] = Trigger(self.session, r'^[> ]*你已经将.*里的.*喝得一滴也不剩了|^[> ]*.*已经被喝得一滴也不剩了。', id = "drink_none", group = "life", onSuccess = self.ondrinknone)
            self._triggers["drink_next"] = Trigger(self.session, r'^[> ]*你拿起.*咕噜噜地喝了几口.*|^[> ]*你端起牛肉汤，连汤带肉囫囵吃了下去。|^[> ]*你端起桌上的.+，咕噜咕噜地喝了几口', id = "drink_next", group = "life", onSuccess = self.ondrink)
            self._triggers["drink_done"] = Trigger(self.session, r'^[> ]*你已经喝太多了，再也灌不下一滴.*了|^[> ]*你已经喝饱了，再也喝不下一丁点了', id = "drink_done", group = "life")

            self._triggers["yh_cont"]    = Trigger(self.session, r'^[> ]*你全身放松，坐下来开始运功疗伤。', id = "yh_cont", onSuccess = self.exertheal)
            self._triggers["yh_done"]    = Trigger(self.session, r'^[> ]*你现在气血充盈，没有受伤。', id = "yh_done")
            self._triggers["yf_cont"]    = Trigger(self.session, r'^[> ]*你全身放松，运转真气进行疗伤。', id = "yf_cont", onSuccess = self.exertinspire)
            self._triggers["yf_done"]    = Trigger(self.session, r'^[> ]*你根本就没有受伤，疗什么伤啊！', id = "yf_done")

            self.session.addTriggers(self._triggers)

        def oneat(self, name, line, wildcards):
            if hasattr(self, "food"):
                self.session.exec_command_after(0.2, "eat {}".format(self.food_id))

        def oneatnone(self, name, line, wildcards):
            if hasattr(self, "foods") and isinstance(self.foods, list):
                self.food_count -= 1
                if self.food_count <= 0:
                    self.foods.remove(self.food)
                    if len(self.foods) > 0:
                        self.food = random.choice(self.foods)
                        self.food_id = self.food.id
                        self.food_count = self.food.count
                        self.oneat("eat_next", "", tuple())
                    else:
                        self.warning("你身上已经没有记录的食物了", '生活')
                else:
                    self.oneat("eat_next", "", tuple())

        def ondrink(self, name, line, wildcards):
            if hasattr(self, "drink"):
                self.session.exec_command_after(0.2, "drink {} {}".format(self.drink_id, self.drink_count))

        def ondrinknone(self, name, line, wildcards):
            if hasattr(self, "drinks") and isinstance(self.drinks, list):
                self.drink_count -= 1
                if self.drink_count == 0:
                    self.drinks.remove(self.drink)
                    if len(self.drinks) > 0:
                        self.drink = random.choice(self.drinks)
                        self.drink_id = self.drink.id
                        self.drink_count = self.drink.count
                        self.ondrink("drink_next", "", tuple())
                    else:
                        self.warning("你身上已经没有记录的饮水了", '生活')
                else:
                    self.ondrink("drink_next", "", tuple())

        async def eat_and_drink(self):
            self.foods = self.session.getVariable("foods")
            self.drinks = self.session.getVariable("drink")
            if isinstance(self.foods, list) and len(self.foods) > 0:
                self.food = random.choice(self.foods)
                self.food_id = self.food.id
                self.food_count = self.food.count
                self.oneat("eat_next", "", tuple())
                task = self.create_task(self._triggers["eat_done"].triggered())
                done, pending = await asyncio.wait((task,), timeout=10)
                if task in pending:
                    task.cancel("执行超时")
            else:
                self.warning("你身上已经没有可吃的食物了", '生活')

            if isinstance(self.drinks, list) and len(self.drinks) > 0:
                self.drink = random.choice(self.drinks)
                self.drink_id = self.drink.id
                self.drink_count = self.drink.count
                self.ondrink("drink_next", "", tuple())
                task = self.create_task(self._triggers["drink_done"].triggered())
                done, pending = await asyncio.wait((task,), timeout = 10)
                if task in pending:
                    task.cancel("执行超时")
            else:
                self.warning("你身上已经没有可喝的饮品了", '生活')

            self.info("吃喝完毕。", "生活")
            return self.SUCCESS

        async def sell(self):
            sells = self.session.getVariable("sells")
            if isinstance(sells, list) and len(sells) > 0:
                for item in sells:
                    sell_cmd = "sell {0} for {1}".format(item.id, item.count)
                    self.session.writeline(sell_cmd)
                    await asyncio.sleep(1)

            sells.clear()
            self.session.setVariable("sells", sells)
            self.info('身上所有可卖物品已典当完毕。', "生活")

        async def convert(self):
            money = self.session.getVariable("money")
            if isinstance(money, list) and len(money) > 0:
                for item in money:
                    cmd = ""
                    if (item.id == "coin") and (item.count >= 100):
                        cmd = "convert {0} coin to silver".format(item.count // 100 * 100)
                        
                    elif (item.id == "silver") and (item.count >= 100):
                        cmd = "convert {0} silver to gold".format(item.count // 100 * 100)
                    
                    if cmd:
                        self.session.writeline(cmd)
                        await asyncio.sleep(2)

            self.info('身上所有铜板/白银已转换完毕。', "生活")

        async def deposit(self, type = 'all'):
            if type == "gold":
                self.session.writeline("cun all cash")
                self.session.writeline("cun all gold")

            elif type == "all":
                self.session.writeline("cun all cash")
                self.session.writeline("cun all gold")
                await asyncio.sleep(2)
                self.session.writeline("cun all silver")
                await asyncio.sleep(2)
                self.session.writeline("cun all coin")

            self.info('身上所有{}已存到银行。'.format("现金" if type == "all" else "黄金"), "生活")

        async def execute(self, cmd, *args, **kwargs):
            try:
                self.reset()

                if cmd == 'saveall':
                        await self.deposit()

                elif cmd == 'savegold':
                    await self.deposit('gold')

                else:
                    await self._cmdInventory.execute()
                    if cmd == "sellall":
                        await self.sell()

                    elif cmd == "convertall":
                        await self.convert()

                    elif cmd == 'feed':
                        await self.eat_and_drink()

            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")

    class CmdEnable(Command):
        def __init__(self, session, *args, **kwargs):
            super().__init__(session, "^(jifa|enable)", *args, **kwargs)
            self._triggers = {}

            self.tri_start     = Trigger(session, id = 'enable_start', patterns = r'^┌[─]+基本功夫[─┬]+┐$', onSuccess = self.start, group = "enable")
            self.tri_stop      = Trigger(session, id = 'enable_end',   patterns = r'^└[─┴]+北大侠客行[─]+┘$', onSuccess = self.stop, group = "enable", keepEval = True)
            self.tri_info      = Trigger(session, id = 'enable_item',  patterns = r'^│(\S+)\s\((\S+)\)\s+│(\S+)\s+│有效等级：\s+(\d+)\s+│$', onSuccess = self.item, group = "enable")

            self._triggers[self.tri_start.id] = self.tri_start
            self._triggers[self.tri_stop.id]  = self.tri_stop
            self._triggers[self.tri_info.id]  = self.tri_info

            self.tri_start.enabled = True
            self.tri_stop.enabled = False
            self.tri_info.enabled = False
            session.addTriggers(self._triggers)

        def start(self, name, line, wildcards):
            self.tri_info.enabled = True
            self.tri_stop.enabled = True

        def stop(self, name, line, wildcards):
            self.tri_start.enabled = True
            self.tri_stop.enabled = False
            self.tri_info.enabled = False

        def item(self, name, line, wildcards):
            b_ch_name = wildcards[0]
            b_en_name = wildcards[1]
            sp_ch_name = wildcards[2]
            sp_level   = int(wildcards[3])
            
            self.session.setVariable(f"eff-{b_en_name}", (sp_ch_name, sp_level))

        async def execute(self, cmd = "enable", *args, **kwargs):
            try:
                self.reset()
                self.tri_start.enabled = True
                self.session.writeline(cmd)

                await self.tri_stop.triggered()

                self._onSuccess(self.id, cmd, None, None)
                external_on_success = kwargs.get("onSuccess", None)
                if external_on_success:
                    external_on_success(self.id, cmd, None, None)
                
                return self.SUCCESS

            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")

    class CmdInventory(Command):
        "执行PKUXKX中的id命令"
        def __init__(self, session, *args, **kwargs):
            super().__init__(session, "^i2$", *args, **kwargs)

            self._triggers = {}
            self._triggers["inv_start"] = self.tri_start = Trigger(session, id = "inv_start", patterns = r'^[> ]*你身上带著下列这些东西\(负重.+\)：$', onSuccess = self.start, group = "inv")
            self._triggers["inv_item"]  = self.tri_item  = Trigger(session, id = "inv_item", patterns = r'^(?:(\S+?)(?:张|枚|根|包|柄|把|碗|盘|盆|片|串|只|个|件|块|文|两|锭))?(\S+)\((.*)\)$', onSuccess = self.item, group = "inv")
            self._triggers["inv_end"]   = self.tri_end   = Trigger(session, id = "inv_end", patterns = r'^你身上穿着：|^你正光着个身子呀！你身上什么也没穿！', onSuccess = self.end, group = "inv")
            self.tri_item.enabled = False

            self.session.addTriggers(self._triggers)

            self._items = []
            self._foods = []
            self._drink = []
            self._sells = []
            self._money = []
            self.total_money = 0

        def start(self, name, line, wildcards):
            self._items.clear()
            self._foods.clear()
            self._drink.clear()
            self._sells.clear()
            self._money.clear()
            self.total_money = 0
            self.tri_item.enabled = True

        def item(self, name, line, wildcards):
            item_cnt_ch = wildcards[0]
            item_id = wildcards[2].lower()
            item_desc = wildcards[1]
            if item_cnt_ch:
                item_cnt = Configuration.word2number(item_cnt_ch)
            else:
                item_cnt = 1
            
            # id, name, count
            item = Configuration.Inventory(item_id, item_desc, item_cnt)
            self._items.append(item)

            if item_id in Configuration.MONEY:
                self._money.append(item)
                if item_id == "thousand-cash":
                    self.total_money += item_cnt * 1000
                elif item_id == "gold":
                    self.total_money += item_cnt * 100
                elif item_id == "silver":
                    self.total_money += item_cnt
                elif item_id == "coin":
                    self.total_money += item_cnt / 100.0

            elif item_id in Configuration.FOODS:
                self._foods.append(item)
            elif item_id in Configuration.DRINKS:
                self._drink.append(item)
            elif item_id in Configuration.SELLS and item_desc in Configuration.SELLS_DESC:
                self._sells.append(item)
            elif item_id in Configuration.TRASH:
                self.session.writeline(f"drop {item_id}")

        def end(self, name, line, wildcards):
            self.tri_item.enabled = False
        
        async def execute(self, cmd = "i2", *args, **kwargs):
            try:
                self.reset()
                self.session.writeline(cmd)
                await self.tri_end.triggered()
                self.session.setVariable("money", self._money)
                self.session.setVariable("foods", self._foods)
                self.session.setVariable("drink", self._drink)
                self.session.setVariable("sells", self._sells)
                self.session.setVariable("cash", self.total_money)

                self._onSuccess(self.id, cmd, None, None)
                return self.SUCCESS
            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")

    class CmdDazuoto(Command):
        "持续打坐或打坐到max"
        def __init__(self, session, cmdEnable, cmdHpbrief, cmdLifeMisc, *args, **kwargs):
            super().__init__(session, "^(dzt)(?:\s+(\S+))?$", *args, **kwargs)
            self._cmdEnable = cmdEnable
            self._cmdHpbrief = cmdHpbrief
            self._cmdLifeMisc = cmdLifeMisc
            self._triggers = {}

            self._initTriggers()

            self._force_level = 0
            self._dazuo_point = 10

            self._halted = False

        def _initTriggers(self):
            self._triggers["tri_dz_done"]   = self.tri_dz_done      = Trigger(self.session, r'^[> ]*(..\.\.)*你运功完毕，深深吸了口气，站了起来。$', id = "tri_dz_done", keepEval = True, group = "dazuoto")
            self._triggers["tri_dz_noqi"]   = self.tri_dz_noqi      = Trigger(self.session, r'^[> ]*你现在的气太少了，无法产生内息运行全身经脉。|^[> ]*你现在气血严重不足，无法满足打坐最小要求。|^[> ]*你现在的气太少了，无法产生内息运行小周天。$', id = "tri_dz_noqi", group = "dazuoto")
            self._triggers["tri_dz_nojing"] = self.tri_dz_nojing    = Trigger(self.session, r'^[> ]*你现在精不够，无法控制内息的流动！$', id = "tri_dz_nojing", group = "dazuoto")
            self._triggers["tri_dz_wait"]   = self.tri_dz_wait      = Trigger(self.session, r'^[> ]*你正在运行内功加速全身气血恢复，无法静下心来搬运真气。$', id = "tri_dz_wait", group = "dazuoto")
            self._triggers["tri_dz_halt"]   = self.tri_dz_halt      = Trigger(self.session, r'^[> ]*你把正在运行的真气强行压回丹田，站了起来。', id = "tri_dz_halt", group = "dazuoto")
            self._triggers["tri_dz_finish"] = self.tri_dz_finish    = Trigger(self.session, r'^[> ]*你现在内力接近圆满状态。', id = "tri_dz_finish", group = "dazuoto")
            self._triggers["tri_dz_dz"]     = self.tri_dz_dz        = Trigger(self.session, r'^[> ]*你将运转于全身经脉间的内息收回丹田，深深吸了口气，站了起来。|^[> ]*你的内力增加了！！', id = "tri_dz_dz", group = "dazuoto")

            self.session.addTriggers(self._triggers)    

        def stop(self):
            self.tri_dz_done.enabled = False
            self._halted = True
            self._always = False

        async def dazuo_dz(self):
            dazuo_times = 0
            self.tri_dz_dz.enabled = True

            while True:
                if self._halted:
                    self.info("打坐(dz)任务已被手动中止。", '打坐')
                    break

                waited_tris = []
                waited_tris.append(self.create_task(self.tri_dz_dz.triggered()))
                self.session.writeline("dz")

                done, pending = await asyncio.wait(waited_tris, return_when = "FIRST_COMPLETED")
                tasks_done = list(done)
                tasks_pending = list(pending)
                for t in tasks_pending:
                    t.cancel()

                if len(tasks_done) == 1:
                    task = tasks_done[0]
                    _, name, _, _ = task.result()
                    
                    if name == self.tri_dz_dz.id:
                        dazuo_times += 1
                        if dazuo_times > 100:
                            # 此处，每打坐dz100次，补满水食物
                            self.info('该吃东西了', '打坐')
                            await self._cmdLifeMisc.execute("feed")
                            dazuo_times = 0


        async def dazuo_to(self, to):
            # 开始打坐
            dazuo_times = 0
            self.tri_dz_done.enabled = True
            if not self._force_level:
                await self._cmdEnable.execute("enable")
                force_info = self.session.getVariable("eff-force", ("none", 0))
                self._force_level = force_info[1]

            self._dazuo_point = (self._force_level - 5) // 10
            if self._dazuo_point < 10:  self._dazuo_point = 10
            
            await self._cmdHpbrief.execute("hpbrief")

            neili = int(self.session.getVariable("neili", 0))
            maxneili = int(self.session.getVariable("maxneili", 0))
            force_info = self.session.getVariable("eff-force", ("none", 0))

            if to == "dz":
                cmd_dazuo = "dz"
                self.tri_dz_dz.enabled = True
                self.info('即将开始进行dz，以实现小周天循环', '打坐')

            elif to == "max":
                cmd_dazuo = "dazuo max"
                self.info('当前内力：{}，需打坐到：{}，还需{}, 打坐命令{}'.format(neili, 2 * maxneili - 100, 2 * maxneili - neili - 100, cmd_dazuo), '打坐')
            elif to == "once":
                cmd_dazuo = "dazuo max"
                self.info('将打坐1次 {dazuo max}.', '打坐')
            else:
                cmd_dazuo = f"dazuo {self._dazuo_point}"
                self.info('开始持续打坐, 打坐命令 {}'.format(cmd_dazuo), '打坐')

            while (to == "dz") or (to == "always") or (neili / maxneili < 1.95):
                if self._halted:
                    self.info("打坐任务已被手动中止。", '打坐')
                    break
        
                waited_tris = []
                waited_tris.append(self.create_task(self.tri_dz_done.triggered()))
                waited_tris.append(self.create_task(self.tri_dz_noqi.triggered()))
                waited_tris.append(self.create_task(self.tri_dz_nojing.triggered()))
                waited_tris.append(self.create_task(self.tri_dz_wait.triggered()))
                waited_tris.append(self.create_task(self.tri_dz_halt.triggered()))
                if to != "dz":
                    waited_tris.append(self.create_task(self.tri_dz_finish.triggered()))
                else:
                    waited_tris.append(self.create_task(self.tri_dz_dz.triggered()))

                self.session.writeline(cmd_dazuo)

                done, pending = await asyncio.wait(waited_tris, return_when = "FIRST_COMPLETED")
                tasks_done = list(done)
                tasks_pending = list(pending)
                for t in tasks_pending:
                    t.cancel()

                if len(tasks_done) == 1:
                    task = tasks_done[0]
                    _, name, _, _ = task.result()
                    
                    if name in (self.tri_dz_done.id, self.tri_dz_dz.id):
                        if (to == "always"):
                            dazuo_times += 1
                            if dazuo_times > 100:
                                # 此处，每打坐200次，补满水食物
                                self.info('该吃东西了', '打坐')
                                await self._cmdLifeMisc.execute("feed")
                                dazuo_times = 0

                        elif (to == "dz"):
                            dazuo_times += 1
                            if dazuo_times > 50:
                                # 此处，每打坐50次，补满水食物
                                self.info('该吃东西了', '打坐')
                                await self._cmdLifeMisc.execute("feed")
                                dazuo_times = 0

                        elif (to == "max"):
                            await self._cmdHpbrief.execute("hpbrief")
                            neili = int(self.session.getVariable("neili", 0))

                            if self._force_level >= 161:
                                self.session.writeline("exert recover")
                                await asyncio.sleep(0.2)

                        elif (to == "once"):
                            self.info('打坐1次任务已成功完成.', '打坐')
                            break



                    elif name == self.tri_dz_noqi.id:
                        if self._force_level >= 161:
                            await asyncio.sleep(0.1)
                            self.session.writeline("exert recover")
                            await asyncio.sleep(0.1)
                        else:
                            await asyncio.sleep(15)

                    elif name == self.tri_dz_nojing.id:
                        await asyncio.sleep(1)
                        self.session.writeline("exert regenerate")
                        await asyncio.sleep(1)

                    elif name == self.tri_dz_wait.id:
                        await asyncio.sleep(5)

                    elif name == self.tri_dz_halt.id:
                        self.info("打坐已被手动halt中止。", '打坐')
                        break

                    elif name == self.tri_dz_finish.id:
                        self.info("内力已最大，将停止打坐。", '打坐')
                        break

                else:
                    self.info("命令执行中发生错误，请人工检查", '打坐')
                    return self.FAILURE

            self.info('已成功完成', '打坐')
            self.tri_dz_done.enabled = False
            self.tri_dz_dz.enabled = False
            self._onSuccess()
            return self.SUCCESS

        async def execute(self, cmd, *args, **kwargs):
            try:
                self.reset()
                if cmd:
                    m = re.match(self.patterns, cmd)
                    if m:
                        cmd_type = m[1]
                        param = m[2]
                        self._halted = False
    
                        if param == "stop":
                            self._halted = True
                            self.info('已被人工终止，即将在本次打坐完成后结束。', '打坐')
                            #self._onSuccess()
                            return self.SUCCESS

                        elif param in ("dz",):
                            #return await self.dazuo_dz()
                            return await self.dazuo_to("dz")

                        elif param in ("0", "always"):
                            return await self.dazuo_to("always")

                        elif param in ("1", "once"):
                            return await self.dazuo_to("once")

                        elif not param or param == "max":
                            return await self.dazuo_to("max")
                        
            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")
 
    ########### 分隔符以上，是各小类型的定义内容 ###########
    #################### 这里是分隔符 ####################
    ######### 分割符以下，是Configutation类的本体 #########

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
        self.tri_webpage = Trigger(self.session, id = 'tri_webpage', patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', group = "sys", onSuccess = self.ontri_webpage)
        self._triggers[self.tri_webpage.id] = self.tri_webpage
        self.tri_hp = Trigger(self.session, id = 'tri_hpbrief', patterns = (r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$',), group = "sys", onSuccess = self.ontri_hpbrief)
        self._triggers[self.tri_hp.id] = self.tri_hp
        
        self.session.addTriggers(self._triggers)

    def packgem(self, name, line, wildcards):
        self.session.writeline("pack gem")
            
    def autoget(self, item, name, line, wildcards):
        get_cmd = f"get {item}"
        self.session.writeline(get_cmd)

    def _initCommands(self):
        self._commands['cmd_inv']        = self.cmd_inv         = Configuration.CmdInventory(self.session, id = "cmd_inv", group = "status", onSuccess = self.oncmd_inv)
        self._commands['cmd_lifemisc']   = self.cmd_lifemisc    = Configuration.CmdLifeMisc(self.session, self.cmd_inv, id = "cmd_lifemisc", group = "life")
        self._commands['cmd_enable']     = self.cmd_enable      = Configuration.CmdEnable(self.session, id = "cmd_enable", group = "status")
        self._commands['cmd_hpbrief']    = self.cmd_hpbrief     = SimpleCommand(self.session, id = "cmd_hpbrief", patterns = "^hpbrief$", succ_tri = self.tri_hp, group = "status", onSuccess = self.oncmd_hpbrief)
        self._commands['mod_dazuoto']    = self.mod_dazuoto     = Configuration.CmdDazuoto(self.session, self.cmd_enable, self.cmd_hpbrief, self.cmd_lifemisc, id = "mod_dazuoto")
        
        self.session.addCommands(self._commands)

    def _initAliases(self):
        self._aliases['ali_get'] = Alias(self.session, "^gp(\d+)?\s(.+)$", id = "ali_get", onSuccess = self.getfromcorpse)
        
        self.session.addAliases(self._aliases)

    def _initTimers(self):

        self.session.addTimers(self._timers)

    def getfromcorpse(self, name, line, wildcards):
        index = wildcards[0]
        item  = wildcards[1]

        if index:
            cmd = f"get {item} from corpse {index}"
        else:
            cmd = f"get {item} from corpse"

        self.session.writeline(cmd)

    def ontri_webpage(self, name, line, wildcards):
        "不能删，fullme自动打开网页"
        webbrowser.open(line)


    def ontri_hpbrief(self, name, line, wildcards):
        "不能删，hpbrief自动保存属性变量参数"
        self.session.setVariables(self.HP_KEYS, wildcards)

    def oncmd_hpbrief(self, name, cmd, line, wildcards):
        var1 = self.session.getVariables(("jing", "effjing", "maxjing", "jingli", "maxjingli"))
        line1 = "【精神】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【精力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var1[0], var1[1], 100 * float(var1[1]) / float(var1[2]), var1[3], var1[4], 100 * float(var1[0]) / float(var1[2]), 100 * float(var1[3]) / float(var1[4]))
        var2 = self.session.getVariables(("qi", "effqi", "maxqi", "neili", "maxneili"))
        line2 = "【气血】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【内力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var2[0], var2[1], 100 * float(var2[1]) / float(var2[2]), var2[3], var2[4], 100 * float(var2[0]) / float(var2[2]), 100 * float(var2[3]) / float(var2[4]))
        var3 = self.session.getVariables(("food", "water", "exp", "pot", "fighting", "busy"))
        line3 = "【食物】 {0:<4} 【饮水】{1:<4} 【经验】{2:<9} 【潜能】{3:<10}【{4}】【{5}】".format(var3[0], var3[1], var3[2], var3[3],  "未战斗" if var3[4] == "0" else "战斗中", "不忙" if var3[5] == "0" else "忙")
        self.session.info(line1, "状态")
        self.session.info(line2, "状态")
        self.session.info(line3, "状态")

    def oncmd_inv(self, name, cmd, line, wildcawrds):
        cash = self.session.getVariable("cash", 0)
        cash_str = self.money2str(cash * 100)

        if cash == 0:
            self.session.info("命令i2执行完成。你身上没有随身携带现金!")
        elif cash > 100:
            self.session.info(f'身上现金已达到 {cash_str}，应该存钱了！')
        else:
            self.session.info(f"命令i2执行完成。你身上随身携带现金有 {cash_str}")
