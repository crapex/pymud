from pymud import Alias, Trigger, Command, SimpleCommand
import re, asyncio, random, math, traceback, json
from collections import namedtuple
import networkx as nx
from collections import deque

opposite_direction = {
    "east":"west",
    "south":"north",
    "west":"east",
    "north":"south",
    "southeast":"northwest",
    "southwest":"northeast",
    "northeast":"southwest",
    "northwest":"southeast",
    "up":"down",
    "down":"up",
    "enter":"out",
    "out":"enter"
}

def reverse_dir(direction):
    return opposite_direction.get(direction,'invalid_dir')

class cmdBuildMap(Command):
        "执行PKUXKX中的Look命令"

        VisitedState = namedtuple("State", ("visited", "room"))

        def __init__(self, session, cmdLook, *args, **kwargs):
            super().__init__(session, patterns = "^(?:buildMap)$", **kwargs)

            self._cmdLook = cmdLook
            self.mapper = self._cmdLook.mapper

            self.reset()

        def reset(self):
            pass

        async def execute(self, cmd = None, *args, **kwargs):
            try:
                self.reset()

                # 1. 输入命令
                result, start_room = await self._cmdLook.execute("look")
                if not (result == self.SUCCESS):
                    self.warning('查找起始房间失败')
                    return

                G = nx.DiGraph()
                # 从当前room开始进行深度为n的广度遍历(其实是已建数据库深度+n)
                depth_limit = 12
                # 使用一个队列来存储待访问的节点和它们的深度
                queue = deque([(start_room, 0)])

                room = None
                while queue:
                    lastroom = room
                    room, depth = queue.popleft()
                    if depth > depth_limit:
                        self.info('遍历成功结束','MapInfo')
                        break


                    room_in_DB = self.mapper.isRoomInDB(room)
                    #DB里没有当前room，添加room到DB
                    if not room_in_DB:    
                        self.mapper.addRoom(room)
                        AddRoomStr = f'加{room["name"]}到DB'
                        self.info(AddRoomStr,'MapInfo')                        

                    room_node = self.mapper.getRoomNode(room)
                    G.add_node(room_node)
                    if lastroom:
                        lastroom_node = self.mapper.getRoomNode(lastroom)
                        minPath = nx.dijkstra_path(G, source=lastroom_node, target=room_node)
                        walkpath = []
                        for i in range(len(minPath)-1):
                            edge = G[minPath[i]][minPath[i+1]]
                            walkpath.append(edge['direction'])

                        traverseInfo = f'结束遍历{lastroom["name"]}，准备开始遍历{room["name"]}四周，当前深度为{depth}'          
                        self.info(traverseInfo,'MapInfo')
                        resetPath = ';'.join(walkpath)
                        walkpathStr = f'去目标地点{room["name"]},走路'+resetPath
                        self.info(walkpathStr,'MapInfo')
                        self.session.writeline(resetPath)
                        await asyncio.sleep(5)

                    room_isTraversed = False
                    if room_in_DB:                        
                        room_TraversedInfo = self.mapper.isTraversed(room_node)
                        if room_TraversedInfo[0]:
                            room_isTraversed = True
                        else:
                            room_isTraversed = False

                        traverseInfo = f'{room["name"]}状态为{room_isTraversed}'
                        self.info(traverseInfo,'MapInfo')
                    else:
                        room_isTraversed = False
                    
                    if  not room_isTraversed:  #本房间还没有把所有出口遍历过
                        traverseInfo = f'正式开始遍历{room["name"]}四周区域'
                        self.info(traverseInfo,'MapInfo')

                        self.mapper.SetTraversed(room_node,1)

                        exits = room["exits"].split(';')
                        #遍历room出口
                        for exit in exits:
                            PathStr = f'尝试走{room["name"]}的{exit}方向'
                            self.info(PathStr,'MapInfo')
                            await asyncio.sleep(3)
                            self.session.writeline(exit)
                            self.session.writeline('look')
                            result, neighbor = await self._cmdLook.execute("look")
                            await asyncio.sleep(3)
                           
                            if self.session.getVariable('gmcp_result'):
                                self.mapper.addRoom(neighbor)
                                neighbor_node = self.mapper.getRoomNode(neighbor)
                                G.add_node(neighbor_node)
                                G.add_edge(room_node,neighbor_node,direction=exit)

                                reversed_exit = reverse_dir(exit)
                                self.session.writeline(reversed_exit)   #返回当前要遍历的room
                                await asyncio.sleep(5)
                                G.add_edge(neighbor_node,room_node,direction=reversed_exit)

                                PathStr = f'成功尝试了{room["name"]}的{exit}方向'
                                self.info(PathStr,'MapInfo')
                                #room的邻接点neighbor没有在数据库中
                                if not self.mapper.isTraversed(neighbor_node):                                    
                                    #存储从room到neighbor的有向边（exit）
                                    self.mapper.setupRoomLink(room_node,neighbor_node,exit)
                                    self.mapper.setupRoomLink(neighbor_node,room_node,reversed_exit)
                                    await asyncio.sleep(1)
                                    PathStr = f'添加边{room["name"]}<->{neighbor["name"]}'
                                    self.info(PathStr,'MapInfo')
                                else:
                                    PathStr = f'{neighbor["name"]}已经遍历过了，不用加边'
                                    self.info(PathStr,'MapInfo')
                                                                        
                                queue.append((neighbor, depth + 1))
                            else:
                                PathStr = f'无法走到{room["name"]}的{exit}方向'
                                self.info(PathStr,'MapInfo')
            
            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")
