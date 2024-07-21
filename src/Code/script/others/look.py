from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, webbrowser, traceback, json
from collections import namedtuple

class cmdLook(Command):
        "执行PKUXKX中的Look命令"

        State = namedtuple("State", ("result", "room"))

        def __init__(self, session, cmdMove, **kwargs):
            super().__init__(session, patterns = "^(?:l|look)$", **kwargs)
            self._cmdMove = cmdMove
            kwargs = {"keepEval": True, "group": "room"}
            self._triggers = {}
            self.tri_start    = Trigger(session, id = 'room_name', patterns = Configuration.roomname_regx, onSuccess = self.roomname, **kwargs)
            self.tri_exits    = Trigger(session, id = 'room_exits', patterns = Configuration.roomexit_regx, onSuccess = self.roomexits, **kwargs)
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
            #self.info('捕获一个房间: {0}， 其出口为 {2}， 关联关系为{3}，描述为： {1}'.format(room["name"], room["description"], room["exits"], room["relation"]))
            if room["name"].find("剑心居") >= 0:
                self.session.setVariable("%room", "剑心居")
                self.info('通过名称匹配，确认你在剑心居.', "地形匹配")
            else:
                self.info('捕获一个房间 {0}， 其出口为 {1}， 关联关系为{2}'.format(room["name"], room["exits"], room["relation"]), "地形匹配")
                dbrooms = self.mapper.FindRoomsByRoom(room)

                cnt = len(dbrooms)
                # Inertial Navigation System location, 惯性导航系统匹配确定的位置信息
                ins_loc = self.session.getVariable("ins_loc")
                # terrain matching locations. 通过地形匹配确定的位置信息
                tm_locs = list()
                if cnt > 0:
                    self.info('通过地形匹配从数据库中找到{0}个房间.'.format(cnt), "地形匹配")
                    for dbroom in dbrooms:
                        if isinstance(dbroom, DBRoom):  
                            if cnt == 1:
                                self.info('地形匹配房间ID：{0}，房间名：{1}，房间所在城市：{2}'.format(dbroom.id, dbroom.name, dbroom.city), "地形匹配")
                            tm_loc = {}
                            tm_loc["id"]    = dbroom.id
                            tm_loc["name"]  = dbroom.name
                            tm_loc["city"]  = dbroom.city

                            links = self.mapper.FindRoomLinks_db(dbroom.id)
                            if cnt == 1:
                                self.info(f'该房间共有{len(links)}条路径，分别为：', "地形匹配")
                            for link in links:
                                if cnt == 1:
                                    self.info(f'ID = {link.linkid}, {link.path}，链接到：{link.city} {link.name} ({link.linkto})', "路径")
                                
                                # 增加 Truepath判定，以支持CmdMove
                                path = self._cmdMove.truepath(link.path)

                                if ';' in path:
                                    tm_loc["multisteps"] = True
                                else:
                                    tm_loc["multisteps"] = False
                                
                                tm_loc[path] = link.linkto
                            
                            tm_locs.append(tm_loc)

                            if ins_loc and ins_loc["id"] == dbroom.id:
                                self.info("惯导系统与地形匹配系统印证确定，当前房间为：{2} {1}(ID={0})".format(dbroom.id, dbroom.name, dbroom.city), "地形匹配")
                                
                                # 此时，tmlocs仅保留1个正确的房间
                                tm_locs.clear()
                                tm_locs.append(tm_loc)
                                
                                # 增加autoupdate（额外条件：存在relation时，以防止没有fullme时不显示relation还被更新
                                autoupdate = self.session.getVariable("autoupdate", False)
                                if autoupdate and (len(room["relation"]) > 1):
                                    self.mapper.UpdateRoom(dbroom.id, room)
                                    self.info(f'数据库中房间{room["name"] }(ID = {dbroom.id})内容已更新!', "自动地图更新")
                                
                                break
                else:
                    self.warning('未从数据库中找到相应房间!', '地形匹配')
            
                # tm_locs变量，terrain matching locations. 通过地形匹配确定的位置信息
                self.session.setVariable("tm_locs", tm_locs)

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
                done, pending = await asyncio.wait([self.create_task(self.tri_exits.triggered()),], timeout = 5) 
                if len(done) > 0:
                    task = tuple(done)[0]
                    state = task.result()

                    room["name"] = self._roomname
                    room["relation"] = self._relation
                    room["description"] = self._desc
                    if len(state.wildcards) == 1:
                        exits = state.wildcards[0] or ""
                        exits = exits.strip()
                        exits = exits.replace('。','').replace(' ', '').replace('、', ';').replace('和', ';')  # 去除句号、空格；将顿号、和转换为;
                        exit_list = exits.split(';')
                        exit_list.sort()
                        room["exits"] = ';'.join(exit_list)
                    else:
                        room["exits"] = ""

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
