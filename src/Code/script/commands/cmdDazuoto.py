from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, traceback
from collections import namedtuple
import re, asyncio, random, math, traceback, json

class cmdDazuoto(Command):
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
        self._triggers["tri_dz_done"]   = self.tri_dz_done      = Trigger(
            self.session, 
            r'^[> ]*(..\.\.)*你运功完毕，深深吸了口气，站了起来。$', 
            id = "tri_dz_done", 
            keepEval = True, 
            group = "dazuoto"
        )
        self._triggers["tri_dz_noqi"]   = self.tri_dz_noqi      = Trigger(
            self.session, 
            r'^[> ]*你现在的气太少了，无法产生内息运行全身经脉。|^[> ]*你现在气血严重不足，无法满足打坐最小要求。|^[> ]*你现在的气太少了，无法产生内息运行小周天。$', 
            id = "tri_dz_noqi", 
            group = "dazuoto"
        )
        self._triggers["tri_dz_nojing"] = self.tri_dz_nojing    = Trigger(
            self.session, 
            r'^[> ]*你现在精不够，无法控制内息的流动！$', 
            id = "tri_dz_nojing", 
            group = "dazuoto"
        )
        self._triggers["tri_dz_wait"]   = self.tri_dz_wait      = Trigger(
            self.session, 
            r'^[> ]*你正在运行内功加速全身气血恢复，无法静下心来搬运真气。$', 
            id = "tri_dz_wait",
            group = "dazuoto"
        )
        self._triggers["tri_dz_halt"]   = self.tri_dz_halt      = Trigger(
            self.session, 
            r'^[> ]*你把正在运行的真气强行压回丹田，站了起来。', 
            id = "tri_dz_halt", 
            group = "dazuoto"
        )
        self._triggers["tri_dz_finish"] = self.tri_dz_finish    = Trigger(
            self.session, 
            r'^[> ]*你现在内力接近圆满状态。', 
            id = "tri_dz_finish", 
            group = "dazuoto"
        )
        # self._triggers['tri_dz_add'] = self.tri_dz_add = Trigger(
        #     self.session,
        #     r'^[> ]*你的内力增加了！！',
        #     id = 'tri_dz_add',
        #     group = 'dazuoto',
        #     onSuccess = self.dz_add
        # )
        self._triggers["tri_dz_dz"]     = self.tri_dz_dz        = Trigger(
            self.session, 
            r'^[> ]*你将运转于全身经脉间的内息收回丹田，深深吸了口气，站了起来。|^[> ]*你的内力增加了！！', 
            id = "tri_dz_dz", 
            group = "dazuoto"
        )

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
        maxneili = int(self.session.getVariable("max_neili", 0))
        force_info = self.session.getVariable("eff-force", ("none", 0))
        # self.session.info(to)
        if to == "dz":
            cmd_dazuo = "dz"
            self.tri_dz_dz.enabled = True
            self.info('即将开始进行dz，以实现小周天循环', '打坐')
            # self.session.writeline("dz")

        elif to == "max":
            cmd_dazuo = "dazuo max"
            self.info('当前内力：{}，需打坐到：{}，还需{}, 打坐命令{}'.format(neili, 2 * maxneili - 10, 2 * maxneili - neili - 10, cmd_dazuo), '打坐')
        
        elif to == "once":
            cmd_dazuo = "dazuo max"
            self.info('将打坐1次 {dazuo max}.', '打坐')
        
        elif to == 'always':
            if int(self.session.getVariable('qi'))*0.91 > maxneili * 2 - int(self.session.getVariable('neili')):
                # self.session.info("OKKKKKKKKKKKKKK")
                dazuo_point = maxneili * 2 - int(self.session.getVariable('neili'))
                if dazuo_point<10:
                    dazuo_point = 10
                cmd_dazuo = f"dazuo {dazuo_point}"
            else:
                cmd_dazuo = 'dazuo max'
            self.session.writeline(cmd_dazuo)

        # self.session.writeline('tune gmcp Status off')

        while (to == "dz") or (to == "always") or (neili / maxneili < 1.95):
            if to not in ('dz', 'max', 'once'):
                # await self.session.exec_command_async("hpbrief")
                # await asyncio.sleep(0.1)
                _, name, line, wildcards = await self.session._gmcp['GMCP.Status'].triggered()
                # 检查 wildcards 是否是字典，如果不是则尝试解析 line
                if not isinstance(wildcards, dict):
                    try:
                        wildcards = json.loads(line, strict=False)
                    except json.JSONDecodeError:
                        self.session.error(f"GMCP数据解析错误: {line}")
                        return
                Status_list = {}
                for i in wildcards:
                    if isinstance(wildcards[i], str):
                        wildcards[i] = re.sub('\[.*?m','',wildcards[i])
                    Status_list[i] = wildcards[i]

                is_busy = Status_list.get("is_busy", None)
                if is_busy != 'false':
                    continue

                self.session.writeline("exert recover")
                await self.session._gmcp['GMCP.Status'].triggered()
                maxneili = int(self.session.getVariable("max_neili", 0))
                
                if int(self.session.getVariable('qi'))*0.91 > maxneili * 2 - int(self.session.getVariable('neili')):
                    dazuo_point = maxneili * 2 - int(self.session.getVariable('neili'))
                    if dazuo_point<10:
                        dazuo_point = 10
                    cmd_dazuo = f"dazuo {dazuo_point}"
                    # maxneili += 1
                    # neili = maxneili
                else:
                    cmd_dazuo = 'dazuo max'
                # cmd_dazuo = f"dazuo {self._dazuo_point}"
                # self.info('开始持续打坐, 打坐命令 {}'.format(cmd_dazuo), '打坐')

            if self._halted:
                # self.session.writeline
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
                    if to != 'always':
                        self.info("内力已最大，将停止打坐。", '打坐')
                        break
                
                if (to == "always"):
                    self.session.writeline("exert recover")
                    await self.session._gmcp['GMCP.Status'].triggered()
                    maxneili = int(self.session.getVariable("max_neili", '0'))
                    if int(self.session.getVariable('qi'))*0.91 > maxneili * 2 - int(self.session.getVariable('neili')):
                        # self.session.info("OKKKKKKKKKKKKKK")
                        dazuo_point = maxneili * 2 - int(self.session.getVariable('neili'))
                        if dazuo_point<10:
                            dazuo_point = 10
                        cmd_dazuo = f"dazuo {dazuo_point}"
                    else:
                        cmd_dazuo = 'dazuo max'
                    self.session.writeline(cmd_dazuo)

            else:
                # self.session.writeline("tune gmcp Status on")
                self.info("命令执行中发生错误，请人工检查", '打坐')
                return self.FAILURE
            
        # self.session.writeline("tune gmcp Status on")
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

