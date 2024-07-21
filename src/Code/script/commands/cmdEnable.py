from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, traceback
from collections import namedtuple
import re, asyncio, random, math, traceback, json

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
