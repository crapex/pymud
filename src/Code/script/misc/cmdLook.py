from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, traceback, json
from collections import namedtuple
#from mapDB import mapDB

class cmdLook(Command):
        "执行PKUXKX中的Look命令"

        State = namedtuple("State", ("result", "room"))

        def __init__(self, session, mapper, **kwargs):
            super().__init__(session, patterns = "^(?:l|look)$", **kwargs)
            self.mapper = mapper            
            kwargs = {"keepEval": True, "group": "room"}
            self._triggers = {}
            
            self.tri_start    = Trigger(session, id = 'room_name', patterns = r'(.*?) - ((?:\[.*?\] ?)+)', onSuccess = self.roomname, **kwargs)
            self.tri_exits    = Trigger(session, id = 'room_exits', patterns = r'^\s*(?:这里明显的方向有|这里明显的出口有|这里唯一的出口|这里没有任何明显的出路)\s*([\w\s、和]+)', onSuccess = self.roomexits, **kwargs)
            self.tri_relation = Trigger(session, id = 'room_relation', patterns = r'^[>]*\s{7,}(\S.*)\s*$', onSuccess = self.relation, **kwargs)
            self.tri_weather  = Trigger(session, id = 'room_weather', patterns = r'^\s*「(.*)」: (.*)$', onSuccess = self.weather, **kwargs)
            self.tri_desc     = Trigger(session, id = 'room_desc', patterns = '^\s{0,6}\S.*\s*$', onSuccess = self.description, **kwargs)
            self.tri_node     = Trigger(session, id = 'room_node', patterns = '^\s*你可以看看', onSuccess = self.node, **kwargs)
            self.tri_extra    = Trigger(session, id = "room_extra", patterns = '^\s*(┌|│|└)', **kwargs)
            self.tri_empty    = Trigger(session, id = "room_empty", patterns = '^\s*$', onSuccess = self.emptyline, **kwargs)
            self._triggers[self.tri_start.id] = self.tri_start
            self._triggers[self.tri_exits.id] = self.tri_exits
            self._triggers[self.tri_relation.id] = self.tri_relation
            self._triggers[self.tri_weather.id] = self.tri_weather
            self._triggers[self.tri_desc.id] = self.tri_desc
            self._triggers[self.tri_node.id] = self.tri_node
            self._triggers[self.tri_extra.id] = self.tri_extra
            self._triggers[self.tri_empty.id] = self.tri_empty

            self.tri_desc.enabled = False
            self.tri_empty.enabled = False


            session.addTriggers(self._triggers)

            self.reset()

        def reset(self):
            self.tri_start.enabled = False
            self.tri_relation.enabled = False
            self.tri_desc.enabled = False
            self.tri_empty.enabled = False
            self.tri_extra.enabled = False
            self.tri_exits.enabled = False
            self._roomname = ""
            self._desc = ""
            self._relation = ""


        def roomname(self, id, line, wildcards):
            self.tri_start.enabled = False
            self.tri_desc.enabled = True
            self.tri_empty.enabled = True
            self.tri_relation.enabled = True
            self.tri_extra.enabled = True
            self.tri_exits.enabled = True
            self._roomname = wildcards[0]
            self._roomattr = str(wildcards[1])

            self._desc = ""
            self._relation = ""

        def roomexits(self, name, line, wildcards):
            self.tri_desc.enabled = False
            self.tri_empty.enabled = False
            self.tri_relation.enabled = False
            self.tri_extra.enabled = False

        def relation(self, name, line, wildcards):
            self._relation += wildcards[0].strip()

        def weather(self, name, line, wildcards):
            self.tri_desc.enabled = False 

        def node(self, name, line, wildcards):
            self.tri_desc.enabled = False 
    
        def emptyline(self, name, line, wildcards):
            self.tri_desc.enabled = False

        def description(self, name, line, wildcards):
            desc = line.strip()
            omit = False

            if (self.tri_exits.match(line).result == Trigger.SUCCESS) or    \
                (self.tri_weather.match(line).result == Trigger.SUCCESS) or   \
                (self.tri_relation.match(line).result == Trigger.SUCCESS) or   \
                (self.tri_node.match(line).result == Trigger.SUCCESS) or   \
                (self.tri_extra.match(line).result == Trigger.SUCCESS) or   \
                (self.tri_start.match(line).result == Trigger.SUCCESS):
                omit = True

            if omit:
                 desc = ""
            else:
                self.tri_relation.enabled = False

            self._desc += desc


        def onSuccess(self, room):
            #self.info('捕获一个房间: {0}， 其出口为 {2}， 关联关系为{3}，描述为： {1}'.format(room["name"], room["desc"], room["exits"], room["relation"]))           
            if room["name"].find("剑心居") >= 0:
                self.session.setVariable("%room", "剑心居")
                self.info('通过名称匹配，确认你在剑心居.', "地形匹配")
            else:
                self.info('捕获一个房间 {0}， 其出口为 {1}， 关联关系为{2}'.format(room["name"], room["exits"], room["relation"]), "地形匹配")
                dbrooms = self.mapper.findRoomsByRoom(room)
                cnt = len(dbrooms)
                if cnt > 0:
                    for dbroom in dbrooms:
                        if cnt == 1:
                            self.info('地形匹配room')


        async def execute(self, cmd = None, *args, **kwargs):
            try:
                self.reset()
                room = {}
                # 1. 输入命令
                self.tri_start.enabled = True
                self.tri_exits.reset()
                self.session.writeline(cmd)
                # 2. 中间过程由Trigger直接出发，同步方式完成，无需异步等待

                # 3. 等待房间出口被触发      
                done, pending = await asyncio.wait([self.create_task(self.tri_exits.triggered()),], timeout = 8) 
                if len(done) > 0:
                    task = tuple(done)[0]
                    state = task.result()

                    room["name"] = self._roomname
                    room["attr"] = self._roomattr
                    room["relation"] = self._relation
                    room["desc"] = self._desc
                    
                    if len(state.wildcards) == 1:
                        exits = state.wildcards[0] or ""
                        exits = exits.strip()
                        exits = exits.replace('。','').replace(' ', '').replace('、', ';').replace('和', ';')  # 去除句号、空格；将顿号、和转换为;
                        exit_list = exits.split(';')
                        exit_list.sort()
                        room["exits"] = ';'.join(exit_list)
                    else:
                        room["exits"] = ""

                    room["neighbors"] = ""


                    # 首先执行默认onSuccess，然后若存在外部参数onSuccess，再执行
                    self._onSuccess(room)
                    _afterSucc = kwargs.get("onSuccess", None)
                    if callable(_afterSucc): _afterSucc(room)
                    result = self.SUCCESS
                else:
                    # timeout，同success
                    self._onTimeout()
                    _afterTime = kwargs.get("onTimeout", None)
                    if callable(_afterTime): _afterTime()
                    result = self.TIMEOUT
                
                self.reset()
                return self.State(result, room)
            
            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")
