import asyncio
from pymud import Session, Command, Trigger, GMCPTrigger, IConfig

# 房间名匹配正则表达式
REGX_ROOMNAME = r'^[>]*(?:\s)?(\S.+)\s-\s*(?:杀戮场)?(?:\[(\S+)\]\s*)*(?:㊣\s*)?[★|☆|∞|\s]*$'

# 移动命令中的各种方位清单
DIRECTIONS = (
    "n","s","w","e","ne","nw","se","sw",
    "u","d","nu","su","wu","eu","nd","sd","wd","ed",
    "north", "south", "west", "east", "northeast", "northwest", "southeast", "southwest", 
    "up", "down","northup","southup","westup","eastup","northdown","southdown","westdown","eastdown",
    "enter(\s\S+)?", "out", "zuan(\s\S+)?", "\d", "leave(\s\S+)?", "jump\s(jiang|out)", "climb(\s(ya|yafeng|up|west|wall|mount))?",
    "sheshui", "tang", "act zuan to mao wu", "wander", "xiaolu", "cai\s(qinyun|tingxiang|yanziwu)", "row mantuo", "leave\s(\S+)"
    )

# 移动失败（无法移动）的描述正则匹配清单
MOVE_FAIL = (
    r'^[> ]*哎哟，你一头撞在墙上，才发现这个方向没有出路。$', 
    r'^[> ]*这个方向没有出路。$',
    r'^[> ]*守军拦住了你的去路，大声喝到：干什么的？要想通过先问问我们守将大人！$',
)

# 本次移动失败（但可以重新再走的）的描述正则匹配清单
MOVE_RETRY = (
    r'^[> ]*你正忙着呢。$', 
    r'^[> ]*你的动作还没有完成，不能移动。$', 
    r'^[> ]*你还在山中跋涉，一时半会恐怕走不出这(六盘山|藏边群山|滇北群山|西南地绵绵群山)！$', 
    r'^[> ]*你一脚深一脚浅地沿着(\S+)向着(\S+)方走去，虽然不快，但离目标越来越近了。',
    r'^[> ]*你一脚深一脚浅地沿着(\S+)向着(\S+)方走去，跌跌撞撞，几乎在原地打转。',
    r'^[> ]*你小心翼翼往前挪动，遇到艰险难行处，只好放慢脚步。$', 
    r'^[> ]*山路难行，你不小心给拌了一跤。$', 
    r'^[> ]*你忽然不辨方向，不知道该往哪里走了。',
    r'^[> ]*走路太快，你没在意脚下，被.+绊了一下。$',
    r'^[> ]*你不小心被什么东西绊了一下，差点摔个大跟头。$',
    r'^[> ]*青海湖畔美不胜收，你不由停下脚步，欣赏起了风景。$', 
    r'^[> ]*(荒路|沙石地|沙漠中)几乎没有路了，你走不了那么快。$', 
    r'^[> ]*你小心翼翼往前挪动，生怕一不在意就跌落山下。$',
)

class CmdMove(Command, IConfig):
    MAX_RETRY = 3

    def __init__(self, session: Session, *args, **kwargs):
        # 将所有可能的行走命令组合成匹配模式
        pattern = "^({0})$".format("|".join(DIRECTIONS))
        super().__init__(session, pattern, *args, **kwargs)
        self.session = Session
        self.timeout = 10
        self._executed_cmd = ""

        self._objs = list()

        # 此处使用的GMCPTrigger和Trigger全部使用异步模式，因此均无需指定onSuccess
        self._objs.append(GMCPTrigger(self.session, "GMCP.Move"))
        self._objs.append(Trigger(self.session, REGX_ROOMNAME, id = "tri_move_succ", group = "cmdmove", keepEval = True, enabled = False))

        idx = 1
        for s in MOVE_FAIL:
            self._objs.append(Trigger(self.session, patterns = s, id = f"tri_move_fail{idx}", group = "cmdmove", enabled = False))
            idx += 1

        idx = 1
        for s in MOVE_RETRY:
            self._objs.append(Trigger(self.session, patterns = s, id = f"tri_move_retry{idx}", group = "cmdmove", enabled = False))
            idx += 1

        self.session.addObjects(self._objs)

    def unload(self):
        self.session.delObjects(self._objs)

    async def execute(self, cmd, *args, **kwargs):
        self.reset()

        retry_times = 0
        self.session.enableGroup("cmdMove")

        while True:

            tasklist = list()
            for tr in self._objs:
                tasklist.append(self.create_task(tr.triggered()))

            done, pending = await self.session.waitfor(cmd, asyncio.wait(tasklist, timeout = self.timeout, return_when = "FIRST_COMPLETED"))

            for t in list(pending):
                self.remove_task(t)

            result = self.NOTSET
            tasks_done = list(done)
            if len(tasks_done) > 0:
                task = tasks_done[0]

                # 所有触发器在 onSuccess 时需要的参数，在此处都可以通过 task.result() 获取
                # result返回值与 await tri.triggered() 返回值完全相同
                # 这种返回值比onSuccess中多一个state参数，该参数在触发器中必定为 self.SUCCESS 值
                state, id, line, wildcards = task.result()
                
                # success
                if id == 'GMCP.Move':
                    # GMCP.Move: [{"result":"true","dir":["west"],"short":"林间小屋"}]
                    move_info = wildcards[0]
                    if move_info["result"] == "true":
                        roomname = move_info["short"]
                        self.session.setVariable("roomname", roomname)
                        result = self.SUCCESS
                    elif move_info["result"] == "false":
                        result = self.FAILURE
                    
                    break

                elif id == 'tri_move_succ':
                    roomname = wildcards[0]
                    self.session.setVariable("roomname", roomname)
                    result = self.SUCCESS
                    break

                elif id.startswith('tri_move_fail'):
                    self.error(f'执行{cmd}，移动失败，错误信息为{line}', '移动')
                    result = self.FAILURE
                    break

                elif id.startswith('tri_move_retry'):
                    retry_times += 1
                    if retry_times > self.MAX_RETRY:
                        result = self.FAILURE
                        break

                    await asyncio.sleep(2)

            else:
                self.warning(f'执行{cmd}超时{self.timeout}秒', '移动')  
                result = self.TIMEOUT
                break

        self.session.enableGroup("cmdMove", False)
        return result

import re, traceback, math

import traceback, re, asyncio, math
from pymud import Command, Trigger, IConfig


class CmdDazuoto(Command, IConfig):
    "持续打坐或打坐到max"
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, r"^(dzt)(?:\s+(\S+))?$", *args, **kwargs)

        self._triggers = {}

        self._initTriggers()

        self._force_level = 0
        self._dazuo_point = 10

        self._halted = False

    def _initTriggers(self):
        self._triggers["done"]   = self.tri_dz_done      = Trigger(self.session, r'^[> ]*你运功完毕，深深吸了口气，站了起来。', id = "tri_dz_done", keepEval = True, group = "dazuoto")
        self._triggers["noqi"]   = self.tri_dz_noqi      = Trigger(self.session, r'^[> ]*你现在的气太少了，无法产生内息运行全身经脉。|^[> ]*你现在气血严重不足，无法满足打坐最小要求。|^[> ]*你现在的气太少了，无法产生内息运行小周天。', id = "tri_dz_noqi", group = "dazuoto")
        self._triggers["nojing"] = self.tri_dz_nojing    = Trigger(self.session, r'^[> ]*你现在精不够，无法控制内息的流动！', id = "tri_dz_nojing", group = "dazuoto")
        self._triggers["wait"]   = self.tri_dz_wait      = Trigger(self.session, r'^[> ]*你正在运行内功加速全身气血恢复，无法静下心来搬运真气。', id = "tri_dz_wait", group = "dazuoto")
        self._triggers["halt"]   = self.tri_dz_halt      = Trigger(self.session, r'^[> ]*你把正在运行的真气强行压回丹田，站了起来。', id = "tri_dz_halt", group = "dazuoto")
        self._triggers["finish"] = self.tri_dz_finish    = Trigger(self.session, r'^[> ]*你现在内力接近圆满状态。', id = "tri_dz_finish", group = "dazuoto")
        self._triggers["dz"]     = self.tri_dz_dz        = Trigger(self.session, r'^[> ]*你将运转于全身经脉间的内息收回丹田，深深吸了口气，站了起来。|^[> ]*你的内力增加了！！', id = "tri_dz_dz", group = "dazuoto")

    def __unload__(self):
        self.session.delObjects(self._triggers)

    def stop(self):
        self.tri_dz_done.enabled = False
        self._halted = True
        self._always = False

    async def dazuo_to(self, to):
        # 开始打坐
        dazuo_times = 0
        self.tri_dz_done.enabled = True
        if not self._force_level:
            await self.session.exec_async("enable")
            force_info = self.session.getVariable("eff-force", ("none", 0))
            self._force_level = force_info[1]

        self._dazuo_point = (self._force_level - 5) // 10
        if self._dazuo_point < 10:  self._dazuo_point = 10
        
        if self.session.getVariable("status_type", "hpbrief") == "hpbrief":
            self.session.writeline("tune gmcp status on")

        neili = int(self.session.getVariable("neili", 0))
        maxneili = int(self.session.getVariable("max_neili", 0))
        force_info = self.session.getVariable("eff-force", ("none", 0))
        self._force_level = force_info[1]

        TIMEOUT_DEFAULT = 10
        TIMEOUT_MAX = 360

        timeout = TIMEOUT_DEFAULT

        if to == "dz":
            cmd_dazuo = "dz"
            timeout = TIMEOUT_MAX
            self.tri_dz_dz.enabled = True
            self.info('即将开始进行dz，以实现小周天循环', '打坐')

        elif to == "max":
            cmd_dazuo = "dazuo max"
            timeout = TIMEOUT_MAX
            need = math.floor(1.90 * maxneili)
            self.info('当前内力：{}，需打坐到：{}，还需{}, 打坐命令{}'.format(neili, need, need - neili, cmd_dazuo), '打坐')

        elif to == "once":
            cmd_dazuo = "dazuo max"
            timeout = TIMEOUT_MAX
            self.info('将打坐1次 {dazuo max}.', '打坐')

        else:
            cmd_dazuo = f"dazuo {self._dazuo_point}"
            self.info('开始持续打坐, 打坐命令 {}'.format(cmd_dazuo), '打坐')

        while (to == "dz") or (to == "always") or (neili / maxneili < 1.90):
            if self._halted:
                self.info("打坐任务已被手动中止。", '打坐')
                break
    
            awts = [self.create_task(self._triggers[key].triggered()) for key in ["done", "noqi", "nojing", "wait", "halt"]]

            if to != "dz":
                awts.append(self.create_task(self._triggers["finish"].triggered()))
            else:
                awts.append(self.create_task(self._triggers["dz"].triggered()))

            done, pending = await self.session.waitfor(cmd_dazuo, asyncio.wait(awts, timeout = timeout, return_when = "FIRST_COMPLETED"))

            tasks_pending = list(pending)
            for t in tasks_pending:
                self.remove_task(t)

            tasks_done = list(done)
            if len(tasks_done) == 0:
                self.info('打坐中发生了超时问题，将会继续重新来过', '打坐')

            elif len(tasks_done) == 1:
                task = tasks_done[0]
                _, name, _, _ = task.result()
                
                if name in (self.tri_dz_done.id, self.tri_dz_dz.id):
                    if (to == "always"):
                        dazuo_times += 1
                        if dazuo_times > 100:
                            # 此处，每打坐200次，补满水食物
                            self.info('该吃东西了', '打坐')
                            await self.session.exec_async("feed")
                            dazuo_times = 0


                    elif (to == "dz"):
                        dazuo_times += 1
                        if dazuo_times > 10:
                            # 此处，每打坐10次，补满水食物 （剑心居 feed 同样句子无反馈信息)
                            self.info('该吃东西了', '打坐')
                            await self.session.exec_async("feed")
                            dazuo_times = 0

                    elif (to == "max"):
                        if self.session.getVariable("status_type", "hpbrief") == "hpbrief":
                            self.session.writeline("tune gmcp status on")

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
                ids = []
                for task in tasks_done:
                    _, name, _, _ = task.result()
                    ids.append(name)

                self.info(f"命令执行中发生错误，应完成1个任务，实际完成{len(tasks_done)}个，任务ID分别为{ids}, 将等待5秒后继续", '打坐')

                await asyncio.sleep(5)

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
    