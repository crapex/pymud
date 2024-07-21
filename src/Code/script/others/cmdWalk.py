import traceback, re, asyncio
from pymud import Command

class CmdWalk(Command):
    "北侠节点处的Walk指令，丢弃惯导信息、控制指定步数"
    _help = """
    适用于北侠的基于惯导/地形匹配的自动行走模块，使用方法如下：
        正常指令      含义
        walk xxx:    标准walk指令
        walk -c xxx: 显示路径
        walk -p:     暂停行走
        walk:        继续行走
        特殊指令：
        walk xxx 3:  第二个参数的数字，控制行走的步数，用于张金敖任务
    """
    def __init__(self, session, triRoom, *args, **kwargs):
        self.tri_room = triRoom
        super().__init__(session, "^walk(?:\s(\S+))?(?:\s(\S+))?(?:\s(\S+))?", *args, **kwargs)

    async def execute(self, cmd, *args, **kwargs):
        try:
            m = re.match(self.patterns, cmd)
            if m:
                para = list()
                for i in range(1, 4):
                    if m[i] != None:
                        para.append(m[i])

                # 此时是步数设置，需要人工控制
                # walk yangzhou 8
                if (len(para) > 0) and para[-1].isnumeric():
                    cnt = int(para[-1])
                    step = "walk " + " ".join(para[:-1])
                    self.info(f"即将通过walk行走，目的地{para[-2]}，步数{para[-1]}步...", "walk")
                    #self.session.writeline("set walk_speed 2")      # 调节速度
                    
                    await asyncio.sleep(1)
                    self.session.writeline(step)
                    
                    while cnt > 0:
                        cnt = cnt - 1
                        await self.tri_room.triggered()

                    self.session.writeline("walk -p")
                    #self.session.writeline("unset walk_speed")      # 恢复速度
                    self.info(f"通过walk行走，目的地{para[-2]}，步数{para[-1]}步完毕", "walk")
                # 否则直接命令发送
                else:
                    self.session.writeline(cmd)

                # walk行走之后，定位会发生变化，因此重置定位信息
                self.session.setVariable("ins_loc", None)
                self.session.setVariable("tm_locs", None)

        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")