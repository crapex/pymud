from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, traceback
from collections import namedtuple
import re, asyncio, random, math, traceback, json


class Main:
    def __init__(self, session, *args, **kwargs):
        self.session = session
        self._aliases  = {}
        self._timers   = {}
        self._triggers = {}
        self._commands = {}

        self._initAliases()
        self._initTimers()
        self._initTriggers()
        self._initCommands()

    def _initTriggers(self):
        self.tri_hp = Trigger(
            self.session, 
            id = 'tri_hpbrief', 
            patterns = (r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', 
                        r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', 
                        r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$',
                        ), 
            group = "sys",
            onSuccess = self.ontri_hpbrief
            )
        self._triggers[self.tri_hp.id] = self.tri_hp
        
        self.session.addTriggers(self._triggers)

    def _initAliases(self):
        pass

    def _initTimers(self):
        pass    

    def _initCommands(self):
        self._commands = {}

        self._commands['cmd_hpbrief']    = cmd_hpbrief     = SimpleCommand(
            self.session, 
            id = "cmd_hpbrief", 
            patterns = "^hpbrief$", 
            succ_tri = self.tri_hp, 
            group = "status", 
            onSuccess = self.oncmd_hpbrief
        )

        #misc
        self.mapDB = self.session.modules["script.misc.mapDB"]["module"].mapDB()
        lifeMisc = self.session.modules["script.misc.lifeMisc"]["module"].lifeMisc()
        self._commands['cmdInv'] = cmdInv = lifeMisc.cmdInventory(self.session)
        self._commands['cmdLifeMisc'] = cmdLifeMisc = lifeMisc.cmdLifeMisc(self.session, cmdInv)

        self._commands['cmdLook'] = cmdLook = self.session.modules["script.misc.cmdLook"]["module"].cmdLook(self.session,self.mapDB)
        self._commands['cmdTest'] = self.session.modules["script.misc.cmdTest"]["module"].cmdTest(self.session)
        self._commands['cmdBuildMap'] = self.session.modules["script.misc.cmdBuildMap"]["module"].cmdBuildMap(self.session,cmdLook)

        #command            
        self._commands['cmdEnable'] = cmdEnable = self.session.modules["script.commands.cmdEnable"]["module"].cmdEnable(self.session)
        self._commands['cmdDazuoto'] = self.session.modules["script.commands.cmdDazuoto"]["module"].cmdDazuoto(self.session,cmdEnable, cmd_hpbrief, cmdLifeMisc)


    def ontri_hpbrief(self, name, line, wildcards):
        "不能删，hpbrief自动保存属性变量参数"
        wildcards = list(wildcards)
        if 'K' in wildcards[0]:
            wildcards[0] = float(wildcards[0].replace("K", ""))*1000
        elif 'M' in wildcards[0]:
            wildcards[0] = float(wildcards[0].replace("M", ""))*1000000
        else:
            wildcards[0] = float(wildcards[0])
        wildcards[0] = round(wildcards[0])
        self.session.setVariables(self.HP_KEYS, tuple(wildcards))

    def oncmd_hpbrief(self, name, cmd, line, wildcards):
        var1 = self.session.getVariables(("jing", "eff_jing", "max_jing", "jingli", "max_jingli"))
        if float(var1[2])>1.0 and float(var1[4])>1.0:
            line1 = "【精神】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【精力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var1[0], var1[1], 100 * float(var1[1]) / float(var1[2]), var1[3], var1[4], 100 * float(var1[0]) / float(var1[2]), 100 * float(var1[3]) / float(var1[4]))
        else:
            line1 = "【精神】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【精力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var1[0], var1[1], var1[3], var1[4], )
        
        var2 = self.session.getVariables(("qi", "eff_qi", "max_qi", "neili", "max_neili"))
        if float(var2[2])>1.0 and float(var2[4])>1.0:
            line2 = "【气血】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【内力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var2[0], var2[1], 100 * float(var2[1]) / float(var2[2]), var2[3], var2[4], 100 * float(var2[0]) / float(var2[2]), 100 * float(var2[3]) / float(var2[4]))
        else:
            line2 = "【气血】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【内力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(var2[0], var2[1], 100 * float(var2[1]) / float(var2[2]), var2[3], var2[4], 100 * float(var2[0]) / float(var2[0]), 100 * float(var2[3]) / float(var2[3]))            
        var3 = self.session.getVariables(("food", "water", "combat_exp", "potential", "is_fighting", "is_busy"))
        line3 = "【食物】 {0:<4} 【饮水】{1:<4} 【经验】{2:<9} 【潜能】{3:<10}【{4}】【{5}】".format(var3[0], var3[1], var3[2], var3[3],  "未战斗" if var3[4] == "0" else "战斗中", "不忙" if var3[5] == "0" else "忙")
        self.session.info(line1, "状态")
        self.session.info(line2, "状态")
        self.session.info(line3, "状态")
