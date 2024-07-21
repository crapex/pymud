import traceback, re, asyncio
from pymud import Command, Trigger, SimpleCommand, GMCPTrigger

from ..misc import DIRECTIONS, REGX_ROOMNAME, MOVE_FAIL, MOVE_RETRY
#from ..map import Map

class cmdMove(Command):
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, "^({0})$".format("|".join(DIRECTIONS)), *args, **kwargs)
        #self.mapper = mapper
        self.timeout = 10
        self._executed_cmd = ""
        self._succ_tris = {}
        self._fail_tris = {}
        self._retry_tris = {}

        #self._gmcp_move = GMCPTrigger(self.session, "GMCP.Move")
        #self.session.addGMCP(self._gmcp_move)
        self._succ_tris["tri_move_succ"] = Trigger(self.session, REGX_ROOMNAME, id = "tri_move_succ", isRegExp = True, keepEval = True, enabled = False, onSuccess = self.tri_move_succ)

        idx = 1
        for s in MOVE_FAIL:
            tri = Trigger(self.session, id = f"tri_move_fail{idx}", patterns = s, isRegExp = True)
            self._fail_tris[tri.id] = tri
            idx += 1

        idx = 1
        for s in MOVE_RETRY:
            tri = Trigger(self.session, id = f"tri_move_retry{idx}", patterns = s, isRegExp = True)
            self._retry_tris[tri.id] = tri
            idx += 1

        self.session.addTriggers(self._succ_tris)
        self.session.addTriggers(self._fail_tris)
        self.session.addTriggers(self._retry_tris)

    def truepath(self, linkpath):
        steps = []
        if ';' in linkpath:
            paths = linkpath.split(';')
            for step in paths:
                m = re.match(r'(\S+)\((.+)\)', step)
                if m:
                    # walk_busy等情况下，只保留括号内部的作为link
                    if m[1] in ('walk_busy', 'walk_retry', 'walk_pause'):
                        steps.append(m[2])
                    
                    # cross_river，直接加全部
                    elif m[1] in ('cross_river', ):       
                        steps.append(step)

                    # 其他情况，如walk_wait时，舍弃
                    else:
                        pass
                else:
                    # 与自身匹配，则为正常行走命令，否则为非行走命令，应舍弃
                    if self.match(step, docallback = False).result == self.SUCCESS:
                        steps.append(step)
                    
                    # 不匹配则为open door之类的，舍弃
                    else:
                        pass

            return ';'.join(steps)
        else:
            # 单个命令情况下，处理walk_busy等括号。有括号为内部参数，其余为原值
            m = re.match(r'(\S+)\((.+)\)', linkpath)
            if m:
                # walk_busy等情况下，只保留括号内部的作为link
                if m[1] in ('walk_busy', 'walk_retry', 'walk_pause'):
                    linkpath = m[2]
            
            return linkpath

    def update_ins_location(self, linkpath, roomname):
        tm_locs = self.session.getVariable("tm_locs")
        old_ins_locs = self.session.getVariable("ins_loc")
        
        print_room_info = self.session.getVariable("roominfo", False)

        from_loc = None
        if old_ins_locs:
            from_loc = old_ins_locs
        elif tm_locs and len(tm_locs) == 1:
            from_loc = tm_locs[0]

        if from_loc and isinstance(from_loc, dict):
            if linkpath in from_loc.keys():
                rooms = self.mapper.FindRoomsById(from_loc[linkpath])
                if len(rooms) == 1:
                    to_room = rooms[0]
                    ins_loc = {}
                    ins_loc["id"] = to_room.id
                    ins_loc["name"] = to_room.name
                    ins_loc["city"] = to_room.city
                    ins_loc["type"] = to_room.type
                    ins_loc["multisteps"] = False
                    
                    if roomname == to_room.name:
                        links = self.mapper.FindRoomLinks(to_room.id)
                        if print_room_info:
                            self.info("成功从位置 {0} {1}(ID={2})向 {6} 移动到 {3} {4}(ID={5})".format(from_loc["city"], from_loc["name"], from_loc["id"], ins_loc["city"], ins_loc["name"], ins_loc["id"], linkpath), "惯性导航")                      
                            self.info(f'该房间共有{len(links)}条路径，分别为：', "惯性导航")
                        for link in links:
                            if print_room_info:
                                self.info(f'ID = {link.linkid}, {link.path:}，链接到：{link.city} {link.name} ({link.linkto})', "路径")
                            # 用于惯导路径path，要考虑以下几中情况
                            # 1. open door， say之类的非行走命令，这种命令要从path中排除
                            # 2. 带有walk_pause(s)\walk_retry(s)之类的命令，这种命令要取括号中的加到path中
                            # 3. s;s类似此类的多步命令（迷宫情况）
                            # 用truepath方法处理

                            path = self.truepath(link.path)
                            ins_loc[path] = link.linkto
                            if ';' in path:
                                ins_loc["multisteps"] = True

                        self.session.setVariable("ins_loc", ins_loc)        # 记录当前惯导位置（有惯导时，可能未经地形匹配，以惯导为准）
                        self.session.setVariable("city", ins_loc["city"])  # 记录地区（万一走丢了，不修改，以最后一次保存的为主）
                    else:                           
                        self.warning("警告! 应该到 {0} {1}(ID={2})位置，但实际房间名为{3}".format(to_room.city, to_room.name, to_room.id, roomname), '惯性导航')
                        
                        # 修改于 2024-01-02，解决有的房间编号问题，仅在此房间显示官道不匹配
                        # self.session.setVariable("ins_loc", None)               # 若名称不匹配，则清空当前惯导位置，待重新地形匹配（待手动更新）

                    self.session.setVariable("tm_locs", [])             # 清空当前地形匹配位置

            else:
                has_path = False
                if ("multisteps" in from_loc.keys()) and from_loc["multisteps"]:
                    # 处理path中有多步的情况
                    links = list(from_loc.keys())
                    if "id" in links: links.remove("id")
                    if "name" in links: links.remove("name")
                    if "city" in links: links.remove("city")
                    if "type" in links: links.remove("type")
                    if "multisteps" in links: links.remove("multisteps")

                    for path in links:
                        if isinstance(path, str) and path.startswith(f'{linkpath};'):
                            ins_loc = {}
                            ins_loc["id"] = 0
                            ins_loc["name"] = '行路中途点'
                            ins_loc["city"] = from_loc["city"]
                            ins_loc["type"] = ''
                            new_path = path[len(f'{linkpath};'):]
                            ins_loc[new_path] = from_loc[path]
                            if ';' in new_path:
                                ins_loc["multisteps"] = True

                            self.session.setVariable("ins_loc", ins_loc)        # 记录当前惯导位置为临时位置，仅保留继续走向的去向为止
                            self.session.setVariable("tm_locs", [])             # 清空当前地形匹配位置
                            has_path = True
                            if print_room_info:
                                self.info("成功从位置 {0} {1}(ID={2})向 {6} 移动到 {3} {4}(ID={5})".format(from_loc["city"], from_loc["name"], from_loc["id"], ins_loc["city"], ins_loc["name"], ins_loc["id"], linkpath), "惯性导航")
                            break
                
                if not has_path:
                    self.warning("警告! 原记录中不存在路径 {0} 方向，请确认地图是否已发生变化".format(linkpath), '惯性导航')
                    self.session.setVariable("ins_loc", None)               # 若移动地址异常，则清空当前惯导位置，待重新地形匹配
        else:
            self.session.setVariable("ins_loc", None)                   # 若无法确定起始地址，则清空当前惯导位置，待重新地形匹配
            if print_room_info:
                self.info(f'执行{linkpath}，成功移动至{roomname}', '移动')

        loc = self.session.getVariable("ins_loc")
        raw = self.session.getVariable("%raw")
        if loc:
            if loc["name"] == roomname:
                new_line = '{}\x1b[32m [{}][{}]'.format(raw, loc["city"], loc["id"])
            else:
                new_line = '{}\x1b[33m [{}][{}][{}]'.format(raw, loc["city"], loc["id"], loc["name"])
        else:
            new_line = '{}\x1b[33m [惯导信号已丢失]'.format(raw)
        self.session.replace(new_line)

    def tri_move_succ(self, name, line, wildcards):
        self.update_ins_location(self._executed_cmd, wildcards[0])

    async def execute(self, cmd, *args, **kwargs):
        self.reset()
        # 1. save the command, to use later.
        self._executed_cmd = cmd
        # 2. writer command
        retry_times = 0
        self._succ_tris["tri_move_succ"].enabled = True
        #self._succ_tris["tri_move_succ"].onSuccess = self.tri_move_succ

        while True:
            # 1. create awaitables
            tasklist = list()
            
            for tr in self._succ_tris.values():
                tr.reset()
                tasklist.append(self.create_task(tr.triggered()))
            for tr in self._fail_tris.values():
                tr.reset()
                tasklist.append(self.create_task(tr.triggered()))
            for tr in self._retry_tris.values():
                tr.reset()
                tasklist.append(self.create_task(tr.triggered()))

            #self._gmcp_move.reset()
            #tasklist.append(self.create_task(self._gmcp_move.triggered()))

            self.session.writeline(cmd)

            done, pending = await asyncio.wait(tasklist, timeout = self.timeout, return_when = "FIRST_COMPLETED")
            
            # 任务完成后增加0.1s等待（不应该等待)
            # await asyncio.sleep(0.1)

            tasks_done = list(done)
            
            tasks_pending = list(pending)
            for t in tasks_pending:
                t.cancel()

            result = self.NOTSET
            if len(tasks_done) > 0:
                task = tasks_done[0]
                _, name, line, wildcards = task.result()
                # success
                if name in self._succ_tris.keys():
                    # 成功的处理在同步Trigger处理函数中，此处不需要
                    result = self.SUCCESS
                    self._executed_cmd = ""
                    #self._succ_tris["tri_move_succ"].onSuccess = None
                    break
                    
                elif name in self._fail_tris.keys():
                    self.error(f'执行{cmd}，移动失败，错误信息为{line}', '移动')
                    result = self.FAILURE
                    break

                elif name in self._retry_tris.keys():
                    retry_times += 1
                    if retry_times > SimpleCommand.MAX_RETRY:
                        result = self.FAILURE
                        break

                    await asyncio.sleep(2)

                # elif name == self._gmcp_move.id:
                #     self.info("使用GMCP处理移动命令，归一化测试")
                #     if isinstance(wildcards, list):
                #         move_info = wildcards[0]
                #         move_result = move_info["result"]
                #         if move_result == "true":
                #             roomname = move_info["short"]
                #             self.info(f"GMCP确认移动到房间{roomname}")
                #             self.update_ins_location(self._executed_cmd, roomname)
                #             result = self.SUCCESS
                #             break

                #         elif move_result == "false":
                #             result = self.FAILURE
                #             break
                #     else:
                #         self.info(f"收到的GMCP.Move数据不是list，而是{type(wildcards)}")

            else:
                self.warning(f'执行{cmd}超时{self.timeout}秒', '移动')  
                result = self.TIMEOUT
                break

        self._succ_tris["tri_move_succ"].enabled = False
        return result

# 2023-10-17 备注：为了将房间ID输出到房间行，将Move命令更改为同步触发处理的Move2命令，以下内容作废
# class CmdMove(SimpleCommand):
#     def __init__(self, session, mapper: Map, succ_tri, *args, **kwargs):
#         super().__init__(session, "^({0})$".format("|".join(Configuration.DIRECTIONS)), succ_tri, *args, **kwargs)
#         self.mapper  = mapper
#         # self.timeout = 5

#     def truepath(self, linkpath):
#         steps = []
#         if ';' in linkpath:
#             paths = linkpath.split(';')
#             for step in paths:
#                 m = re.match(r'(\S+)\((.+)\)', step)
#                 if m:
#                     # walk_busy等情况下，只保留括号内部的作为link
#                     if m[1] in ('walk_busy', 'walk_retry', 'walk_pause'):
#                         steps.append(m[2])
                    
#                     # cross_river，直接加全部
#                     elif m[1] in ('cross_river', ):       
#                         steps.append(step)

#                     # 其他情况，如walk_wait时，舍弃
#                     else:
#                         pass
#                 else:
#                     # 与自身匹配，则为正常行走命令，否则为非行走命令，应舍弃
#                     if self.match(step, docallback = False).result == self.SUCCESS:
#                         steps.append(step)
                    
#                     # 不匹配则为open door之类的，舍弃
#                     else:
#                         pass

#             return ';'.join(steps)
#         else:
#             # 单个命令情况下，处理walk_busy等括号。有括号为内部参数，其余为原值
#             m = re.match(r'(\S+)\((.+)\)', linkpath)
#             if m:
#                 # walk_busy等情况下，只保留括号内部的作为link
#                 if m[1] in ('walk_busy', 'walk_retry', 'walk_pause'):
#                     linkpath = m[2]
            
#             return linkpath

#     def onSuccess(self, name, cmd, line, wildcards):
#         tm_locs = self.session.getVariable("tm_locs")
#         old_ins_locs = self.session.getVariable("ins_loc")
        
#         print_room_info = self.session.getVariable("roominfo", False)

#         from_loc = None
#         if old_ins_locs:
#             from_loc = old_ins_locs
#         elif tm_locs and len(tm_locs) == 1:
#             from_loc = tm_locs[0]

#         if from_loc and isinstance(from_loc, dict):
#             if cmd in from_loc.keys():
#                 rooms = self.mapper.FindRoomsById(from_loc[cmd])
#                 if len(rooms) == 1:
#                     to_room = rooms[0]
#                     ins_loc = {}
#                     ins_loc["id"] = to_room.id
#                     ins_loc["name"] = to_room.name
#                     ins_loc["city"] = to_room.city
#                     ins_loc["type"] = to_room.type
#                     ins_loc["multisteps"] = False
                    
#                     if wildcards[0] == to_room.name:
#                         links = self.mapper.FindRoomLinks(to_room.id)
#                         if print_room_info:
#                             self.info("成功从位置 {0} {1}(ID={2})向 {6} 移动到 {3} {4}(ID={5})".format(from_loc["city"], from_loc["name"], from_loc["id"], ins_loc["city"], ins_loc["name"], ins_loc["id"], cmd), "惯性导航")                      
#                             self.info(f'该房间共有{len(links)}条路径，分别为：', "惯性导航")
#                         for link in links:
#                             if print_room_info:
#                                 self.info(f'ID = {link.linkid}, {link.path:}，链接到：{link.city} {link.name} ({link.linkto})', "路径")
#                             # 用于惯导路径path，要考虑以下几中情况
#                             # 1. open door， say之类的非行走命令，这种命令要从path中排除
#                             # 2. 带有walk_pause(s)\walk_retry(s)之类的命令，这种命令要取括号中的加到path中
#                             # 3. s;s类似此类的多步命令（迷宫情况）
#                             # 用truepath方法处理

#                             path = self.truepath(link.path)
#                             ins_loc[path] = link.linkto
#                             if ';' in path:
#                                 ins_loc["multisteps"] = True

#                         self.session.setVariable("ins_loc", ins_loc)        # 记录当前惯导位置（有惯导时，可能未经地形匹配，以惯导为准）
#                         self.session.setVariable("city", ins_loc["city"])  # 记录地区（万一走丢了，不修改，以最后一次保存的为主）
#                     else:                           
#                         self.warning("警告! 应该到 {0} {1}(ID={2})位置，但实际房间名为{3}".format(to_room.city, to_room.name, to_room.id, wildcards[0]), '惯性导航')
#                         self.session.setVariable("ins_loc", None)               # 若名称不匹配，则清空当前惯导位置，待重新地形匹配（待手动更新）

#                     self.session.setVariable("tm_locs", [])             # 清空当前地形匹配位置

#             else:
#                 has_path = False
#                 if ("multisteps" in from_loc.keys()) and from_loc["multisteps"]:
#                     # 处理path中有多步的情况
#                     links = list(from_loc.keys())
#                     if "id" in links: links.remove("id")
#                     if "name" in links: links.remove("name")
#                     if "city" in links: links.remove("city")
#                     if "type" in links: links.remove("type")
#                     if "multisteps" in links: links.remove("multisteps")

#                     for path in links:
#                         if isinstance(path, str) and path.startswith(f'{cmd};'):
#                             ins_loc = {}
#                             ins_loc["id"] = 0
#                             ins_loc["name"] = '行路中途点'
#                             ins_loc["city"] = from_loc["city"]
#                             ins_loc["type"] = ''
#                             new_path = path[len(f'{cmd};'):]
#                             ins_loc[new_path] = from_loc[path]
#                             if ';' in new_path:
#                                 ins_loc["multisteps"] = True

#                             self.session.setVariable("ins_loc", ins_loc)        # 记录当前惯导位置为临时位置，仅保留继续走向的去向为止
#                             self.session.setVariable("tm_locs", [])             # 清空当前地形匹配位置
#                             has_path = True
#                             if print_room_info:
#                                 self.info("成功从位置 {0} {1}(ID={2})向 {6} 移动到 {3} {4}(ID={5})".format(from_loc["city"], from_loc["name"], from_loc["id"], ins_loc["city"], ins_loc["name"], ins_loc["id"], cmd), "惯性导航")
#                             break
                
#                 if not has_path:
#                     self.warning("警告! 原记录中不存在路径 {0} 方向，请确认地图是否已发生变化".format(cmd), '惯性导航')
#                     self.session.setVariable("ins_loc", None)               # 若移动地址异常，则清空当前惯导位置，待重新地形匹配
#         else:
#             self.session.setVariable("ins_loc", None)                   # 若无法确定起始地址，则清空当前惯导位置，待重新地形匹配
#             if print_room_info:
#                 self.info(f'{name}执行{cmd}，成功移动至{wildcards[0]}', '移动')

#         # loc = self.session.getVariable("ins_loc")
#         # raw = self.session.getVariable("%raw")
#         # if loc:
#         #     new_line = '{}\x1b[32m[{}][ID={}]'.format(raw, loc["city"], loc["id"])
#         # else:
#         #     new_line = '{}\x1b[33m[惯导信号已丢失]'.format(raw)
#         # self.session.replace(new_line)

#     def onFailure(self, name, cmd, line, wildcards):
#         # 未移动成功时，惯导保持原位置信息
#         self.error(f'{name}执行{cmd}，移动失败，错误信息为{line}', '移动')
    
#     def onTimeout(self, name, cmd, timeout):
#         # 移动超时时，惯导保持原位置信息
#         self.warning(f'{name}执行{cmd}超时{timeout}秒', '移动')  
