from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, traceback, json
from collections import namedtuple


class cmdTest(Command):
        def __init__(self, session, *args, **kwargs):
            super().__init__(session, "^(testcmd)(?:\s+(\S+))?$", *args, **kwargs)
            self._triggers = {}

            self.tri_start = Trigger(
                session, 
                id = 'test_room', 
                patterns = r'(.*?) - \[(.*?)\] \[(.*?)\](?: \[(.*?)\])?',   #匹配room第一行
                onSuccess = self.start, 
                group = "enable"
            )
            self.tri_exits = Trigger(
                session, 
                id = 'test_room', 
                patterns = r'^\s*(?:这里明显的方向有|这里明显的出口有)\s*([\w\s、和]+)',   #匹配exit
                onSuccess = self.tri_exits, 
                group = "enable"
            )

            self._triggers[self.tri_start.id] = self.tri_start
            self._triggers[self.tri_exits.id] = self.tri_exits            
            self.session.addTriggers(self._triggers)

            self.reset()

        def reset(self):
            self.tri_start.enabled = False
            self.tri_exits.enabled = False

        def start(self, name, line, wildcards):
            for wc in wildcards:
                self.session.info(wc)
            self.tri_start.enabled = False

        def tri_exits(self, name, line, wildcards):
            for wc in wildcards:
                self.session.info(wc)
            self.tri_start.enabled = False

        async def execute(self, cmd, *args, **kwargs):
            try:
                self.reset()
                self.info(cmd)
                for arg in args:
                    self.info("this is arg:{}".format(args))
                for kwarg in kwargs:
                    self.info(kwarg)
                
                self.tri_start.enabled = True
                self.tri_exits.enabled = True
                self.session.writeline('look')

                await self.tri_exits.triggered()

                return self.SUCCESS

            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")


