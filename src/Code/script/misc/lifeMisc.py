from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, traceback, json
from collections import namedtuple

# set hpbrief long情况下的含义
HP_KEYS = (
    "combat_exp", "potential", "max_neili", "neili", "max_jingli", "jingli", 
    "max_qi", "eff_qi", "qi", "max_jing", "eff_jing", "jing", 
    "vigour/qi", "vigour/yuan", "food", "water", "is_fighting", "is_busy"
    )

FOODS = ("baozi", "gan liang", "jitui", "Jitui", "doufu", "gou rou", "furong huagu", "shanhu baicai", "bocai fentiao", "liuli qiezi", "mala doufu", "nuomi zhou", "tian ji", "yin si", "xunyang yupian", "shizi tou", "mifen zhengrou", "dian xin", "gao")
DRINKS = ("jiudai", "Jiudai", "jiu dai" "hulu", "wan", "niurou tang", "qingshui hulu", "mudan cha", "haoqiu tang", "suanmei tang")
MONEY = ("gold", "silver", "coin", "thousand-cash")
SELLS = ('cai bao', 'xiuhua zhen', 'changjian', 'duanjian', 'jian', 'chang jian', 'armor', 'blade', 'dao', 'xiao lingdang', 'fangtian ji', 'jun fu', 'junfu', 'changqiang', 'chang qiang', 'tie bishou', 'chang bian', 'qingwa tui', 'nen cao', 'sui rouxie', 'cao zi', 'yu xiao', 'gangzhang', 'golden ring', 'golden necklace', 'heise pifeng', 'pink cloth')
SELLS_DESC = ('财宝', '长剑', '短剑', '钢剑', '铁甲', '钢刀', '武士刀', '小铃铛', '方天画戟', '军服', '长枪', '铁匕首', '长鞭', '玉箫', '钢杖', '黑色披风', '金戒指', '金项链', '青蛙腿', '嫩草', '碎肉屑', '草籽', '粉红绸衫', '绣花针')
TRASH = ('xiao lingdang', 'bone', 'iron falun', 'shi tan', 'yun tie', 'huo tong', 'xuan bing',) 

splits_ch = ('亿', '万', '千', '百', '十')
splits_val = (100000000, 10000, 1000, 100, 10)

Inventory = namedtuple('Inventory', ("id", "name", "count"))

def hz2number(hz):
    "将中文汉字转化为对应的数字"
    return '零一二三四五六七八九'.find(hz)

def word2number(word: str, split_idx = 0):
    "将中文汉字串转化为对应的数"
    split_ch = splits_ch[split_idx]
    split_val = splits_val[split_idx]
    
    if not word:
        return 0

    pos = word.find(split_ch)
    if pos >= 0:
        left = word[:pos]
        right = word[pos+1:]
        
        if not left:
            left_num = 1
        else:
            if split_idx < len(splits_ch) - 1:
                left_num = word2number(left, split_idx + 1)
            else:
                left_num = hz2number(left.replace('零', ''))
                
        if not right:
            right_num = 0
        else:
            if split_idx < len(splits_ch) - 1:
                right_num = word2number(right, split_idx + 1)
            else:
                right_num = hz2number(right.replace('零', ''))
                
        val = left_num * split_val + right_num
    else:
        if split_idx < len(splits_ch) - 1:
            val = word2number(word, split_idx + 1)
        else:
            val = hz2number(word.replace('零', ''))
            
    return val 

def money2str(coin):
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

class lifeMisc:
    class cmdLifeMisc(Command):
        def __init__(self, session, cmd_inv, *args, **kwargs):
            super().__init__(session, "^(sellall|convertall|saveall|savegold|feed|liaoshang)$", *args, **kwargs)
            self._cmdInventory = cmd_inv

            self._triggers = {}
            self._initTriggers()

        def _initTriggers(self):       
            self._triggers["eat_none"]   = Trigger(
                self.session, 
                r'^[> ]*你将剩下的.*吃得干干净净', 
                id = "eat_none", 
                group = "life", 
                onSuccess = self.oneatnone
            )
            self._triggers["eat_next"]   = Trigger(
                self.session, 
                r'^[> ]*你拿起.+咬了几口。|^[> ]*你捧起.*狠狠地喝了几口。', 
                id = "eat_next", 
                group = "life", 
                onSuccess = self.oneat
            )
            self._triggers["eat_done"]   = Trigger(
                self.session, 
                r'^[> ]*你已经吃太饱了，再也塞不下任何东西了', 
                id = "eat_done", 
                group = "life"
            )
            self._triggers["drink_none"] = Trigger(
                self.session, 
                r'^[> ]*你已经将.*里的.*喝得一滴也不剩了|^[> ]*.*已经被喝得一滴也不剩了。', 
                id = "drink_none", 
                group = "life", 
                onSuccess = self.ondrinknone
            )
            self._triggers["drink_next"] = Trigger(
                self.session, 
                r'^[> ]*你拿起.*咕噜噜地喝了几口.*|^[> ]*你端起牛肉汤，连汤带肉囫囵吃了下去。|^[> ]*你端起桌上的.+，咕噜咕噜地喝了几口', 
                id = "drink_next", 
                group = "life", 
                onSuccess = self.ondrink
            )
            self._triggers["drink_done"] = Trigger(
                self.session, 
                r'^[> ]*你已经喝太多了，再也灌不下一滴.*了|^[> ]*你已经喝饱了，再也喝不下一丁点了', 
                id = "drink_done", 
                group = "life"
            )

            self._triggers["yh_cont"]    = Trigger(
                self.session, 
                r'^[> ]*你全身放松，坐下来开始运功疗伤。', 
                id = "yh_cont", 
                onSuccess = self.exertheal
            )
            self._triggers["yh_done"]    = Trigger(
                self.session, 
                r'^[> ]*你现在气血充盈，没有受伤。', 
                id = "yh_done"
            )
            self._triggers["yf_cont"]    = Trigger(
                self.session, 
                r'^[> ]*你全身放松，运转真气进行疗伤。', 
                id = "yf_cont", 
                onSuccess = self.exertinspire
            )
            self._triggers["yf_done"]    = Trigger(
                self.session, 
                r'^[> ]*你根本就没有受伤，疗什么伤啊！', 
                id = "yf_done"
            )

            self.session.addTriggers(self._triggers)

        def exertheal(self, *arg):
            self.session.exec_command_after(1, "exert heal")
        
        def exertinspire(self, *arg):
            self.session.exec_command_after(1, "exert inspire")

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

    class cmdEnable(Command):
        def __init__(self, session, *args, **kwargs):
            super().__init__(session, "^(jifa|enable)", *args, **kwargs)
            self._triggers = {}

            self.tri_start = Trigger(
                session, 
                id = 'enable_start', 
                patterns = r'^┌[─]+基本功夫[─┬]+┐$', 
                onSuccess = self.start, 
                group = "enable"
            )
            self.tri_stop = Trigger(
                session, 
                id = 'enable_end',   
                patterns = r'^└[─┴]+北大侠客行[─]+┘$', 
                onSuccess = self.stop, 
                group = "enable", 
                keepEval = True
            )
            self.tri_info = Trigger(
                session, 
                id = 'enable_item',  
                patterns = r'^│(\S+)\s\((\S+)\)\s+│(\S+)\s+│有效等级：\s+(\d+)\s+│$', 
                onSuccess = self.item, 
                group = "enable"
            )

            self._eff_enable = self.session.getVariable("eff-enable", {})
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
            self.session.setVariable("eff-enable", self._eff_enable)

        def item(self, name, line, wildcards):
            b_ch_name = wildcards[0]
            b_en_name = wildcards[1]
            sp_ch_name = wildcards[2]
            sp_level   = int(wildcards[3])
            if sp_ch_name != "无":
                self._eff_enable[b_en_name] = (sp_ch_name, sp_level)
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
                # self.session.info("OKKKKKKKKKKKKKK")
                return self.SUCCESS

            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")

    class cmdInventory(Command):
        "执行PKUXKX中的id命令"
        def __init__(self, session, *args, **kwargs):
            super().__init__(session, "^i2$", *args, **kwargs)

            self._triggers = {}
            self._triggers["inv_start"] = self.tri_start = Trigger(
                session, id = "inv_start", 
                patterns = r'^[> ]*你身上带著下列这些东西\(负重.+\)：$', 
                onSuccess = self.start, 
                group = "inv"
            )
            self._triggers["inv_item"]  = self.tri_item  = Trigger(
                session, 
                id = "inv_item", 
                patterns = r'^(?:(\S+?)(?:张|枚|根|包|柄|把|碗|盘|盆|片|串|只|个|件|块|文|两|锭))?(\S+)\((.*)\)$', 
                onSuccess = self.item, 
                group = "inv"
            )
            self._triggers["inv_end"]   = self.tri_end   = Trigger(
                session, 
                id = "inv_end", 
                patterns = r'^你身上穿着：|^你正光着个身子呀！你身上什么也没穿！', 
                onSuccess = self.end, 
                group = "inv"
            )
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
                item_cnt = word2number(item_cnt_ch)
            else:
                item_cnt = 1
            
            # id, name, count
            item = Inventory(item_id, item_desc, item_cnt)
            self._items.append(item)

            if item_id in MONEY:
                self._money.append(item)
                if item_id == "thousand-cash":
                    self.total_money += item_cnt * 1000
                elif item_id == "gold":
                    self.total_money += item_cnt * 100
                elif item_id == "silver":
                    self.total_money += item_cnt
                elif item_id == "coin":
                    self.total_money += item_cnt / 100.0

            elif item_id in FOODS:
                self._foods.append(item)
            elif item_id in DRINKS:
                self._drink.append(item)
            elif item_id in SELLS and item_desc in SELLS_DESC:
                self._sells.append(item)
            elif item_id in TRASH:
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


