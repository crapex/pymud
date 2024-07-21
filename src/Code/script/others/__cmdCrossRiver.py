import traceback, asyncio
from pymud import Command, Trigger

from .cmdMove import CmdMove

class CmdCrossRiver(Command):
    def __init__(self, session, triRoom: Trigger, cmdMove: CmdMove, *args, **kwargs):
        super().__init__(session, "^(changjiang|jiang|huanghe|长江|黄河)$", *args, **kwargs)
        kwargs = {"keepEval": True, "group": "river"}
        self._triggers  = {}                                                                                      
        self._triggers['rv_boat']   = self.tri_boat   = Trigger(session, r'^[> ]*一叶扁舟缓缓地驶了过来，艄公将一块踏脚板搭上堤岸，以便乘客|^[> ]*岸边一只渡船上的艄公说道：正等着你呢，上来吧。|^[> ]*渡船缓缓靠岸，船上的船工摆出跳板，方便客人上下船。', id = 'rv_boat', onSuccess = self.onBoat, **kwargs)
        self._triggers['rv_wait']   = self.tri_wait   = Trigger(session, r'^[> ]*只听得江面上隐隐传来：“别急嘛，这儿正忙着呐……”$', id = 'rv_wait', onSuccess = self.onWait, **kwargs)
        self._triggers['rv_money']  = self.tri_money  = Trigger(session, r'^[> ]*艄公一把拉住你，你还没付钱呢？$', id = 'rv_money', onSuccess = self.onMoney, **kwargs)
        self._triggers['rv_arrive'] = self.tri_arrive = Trigger(session, r'^[> ]*艄公说“到啦，上岸吧”，随即把一块踏脚板搭上堤岸。$|^[> ]*船工放下跳板，招呼大家下船了。', id = 'rv_arrive', **kwargs)
        self._triggers['rv_forceout'] = self.tri_out  = Trigger(session, r'^[> ]*艄公要继续做生意了，所有人被赶下了渡船。', id = 'rv_forceout', **kwargs)
        #渡船缓缓靠岸，船上的船工摆出跳板，方便客人上下船。
        #船工收回跳板，开船驶向岳阳的北门码头了。
        #船工放下跳板，招呼大家下船了。
        
        self.tri_boat.enabled = False
        self.session.addTriggers(self._triggers)
        self.tri_room = triRoom
        self._cmdMove = cmdMove
        self._boat_arrived = False
        self._noMoney = False
        self.hubiao_processing = False

    def onBoat(self, name, line, widlcards):
        self._boat_arrived = True
        if self.hubiao_processing:
            self.session.writeline("gan che to enter")
        else:
            self.session.writeline("enter")
        self.tri_boat.enabled = False

    def onWait(self, name, line, wildcards):
        self._boat_arrived = False

    def onMoney(self, name, line, wildcards):
        self._noMoney = True

    async def execute(self, cmd, *args, **kwargs):
        try:
            self.reset()
            _outer_success = kwargs.get("onSuccess", None)
            _outer_failure = kwargs.get("onFailure", None)
            _outer_timeout = kwargs.get("onTimeout", None)
            self.hubiao_processing  = kwargs.get("hubiao", False)

            river = "jiang"
            if (cmd == "changjiang") or (cmd == "jiang") or (cmd == "长江"):
                river = "jiang"
            elif (cmd == "huanghe") or (cmd == "黄河"):
                river = "huanghe"
            # 以下是往西南，定时坐船的
            elif (cmd == "river") or (cmd == "river"):
                river = "river"
            else:
                self._onFailure(cmd)
                if callable(_outer_failure): _outer_failure(cmd)
                return self.FAILURE

            self.tri_boat.enabled = True
            self._boat_arrived = False
            self._noMoney = False
            if river != "river":
                #self.session.writeline(f"ask shao gong about {river}")
                self.session.writeline(f"yell boat")
            await asyncio.sleep(0.5)
            while not self._boat_arrived:
                await asyncio.sleep(2.5)
                if river != "river":
                    self.session.writeline("yell boat")
                await asyncio.sleep(0.5)
            
            if self._noMoney:
                self._onFailure("nomoney")
                if callable(_outer_failure): _outer_failure("nomoney")
                return self.FAILURE

            awts = list()
            awts.append(self.create_task(self.tri_arrive.triggered()))
            awts.append(self.create_task(self.tri_out.triggered()))
            done, pending = await asyncio.wait(awts, return_when = "FIRST_COMPLETED")

            
            tasks_pending = list(pending)
            for t in tasks_pending:
                #t.cancel()
                self.remove_task(t)

            tasks_done = list(done)
            if len(tasks_done) > 0:
                task = tasks_done[0]
                _, name, line, wildcards = task.result()
                if name == self.tri_arrive.id:
                    if self.hubiao_processing:
                        self.session.writeline("gan che to out")
                    else:
                        self.session.writeline("out")
                elif name == self.tri_out.id:
                    self.session.writeline("l")

            # await self.tri_arrive.triggered()
            # if self.hubiao_processing:
            #     self.session.writeline("gan che to out")
            # else:
            #     self.session.writeline("out")
            #     self.session.writeline("look")
            state = await self.tri_room.triggered()
            await asyncio.sleep(0.5)

            # 将cmd_room信息传递到cmd_move，以实现惯导系统跟踪，传递的命令类似为cross_river(changjiang)
            #self._cmdMove.onSuccess(self.id, f"cross_river({river})", state.line, state.wildcards)
            self._cmdMove.update_ins_location(f"cross_river({river})", state.wildcards[0])
            self._onSuccess()
            if callable(_outer_success): _outer_success()
            return self.SUCCESS
        
        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")
