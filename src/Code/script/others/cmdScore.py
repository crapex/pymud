import traceback
from pymud import Command, Trigger, Alias, SimpleTrigger

from ..misc import PerformInfo, AVAILABLE_PERFORMS, AUTO_GETS_MENPAI, GEMBOX_MENPAI
#from ..map import Map

class CmdScore(Command):
    def __init__(self, session, mapper, *args, **kwargs):
        super().__init__(session, "^(score|sc)$", *args, **kwargs)
        self.mapper = mapper
        self._triggers = {}
        self._aliases  = {}

        self.tri_start     = Trigger(session, id = 'score_start', patterns = r'^┌[─]+人物详情[─┬]+┐$', onSuccess = self.start, group = "score")
        self.tri_stop      = Trigger(session, id = 'score_end',   patterns = r'^└[─┴]+[^└─┴┘]+[─]+┘$', onSuccess = self.stop, group = "score", keepEval = True)
        self.tri_info      = Trigger(session, id = 'score_info',  patterns = r'^│\s+(?:(\S+)\s)+(\S+)\((\S+)\)\s+│.+│$', onSuccess = self.charinfo, group = "score")
        self.tri_info2     = Trigger(session, id = 'score_info2', patterns = r'^│国籍：\S+\s+上线：(\S+).+│门派：(\S+)(?:\s\S+)*\s+│$', onSuccess = self.menpaiinfo, group = "score")
        self.tri_info3     = Trigger(session, id = 'score_info3', patterns = r'^│杀生：\S+\s+│职业：.+│存款：(\S.+)\s+│$', onSuccess = self.bankinfo, group = "score")
        self._triggers[self.tri_start.id] = self.tri_start
        self._triggers[self.tri_stop.id]  = self.tri_stop
        self._triggers[self.tri_info.id]  = self.tri_info
        self._triggers[self.tri_info2.id]  = self.tri_info2
        self._triggers[self.tri_info3.id]  = self.tri_info3

        self.tri_start.enabled = True
        self.tri_stop.enabled = False
        self.tri_info.enabled = False
        session.addTriggers(self._triggers)

        self._menpaiInfoLoaded = False
        self.session.setVariable("menpaiLoaded", False)

    def start(self, name, line, wildcards):
        self.tri_info.enabled = True
        self.tri_stop.enabled = True

    def stop(self, name, line, wildcards):
        self.tri_start.enabled = True
        self.tri_stop.enabled = False
        self.tri_info.enabled = False

    def charinfo(self, name, line, wildcards):
        # 更新为只从此行获取角色id和名称信息
        # title = wildcards[0]
        self.charname  = wildcards[1]
        self.charid = wildcards[2].lower()

    def getmenpai(self):
        menpai = self.session.getVariable("family/family_name")
        menpai_abbr = "NA"
        
        if menpai:
            if menpai.find('丐帮') >= 0:
                menpai_abbr = "GB"
            elif menpai.find('武当派') >= 0:
                menpai_abbr = "WD"
            elif menpai.find('桃花岛') >= 0:
                menpai_abbr = "TH"
            elif menpai.find('天龙寺') >= 0:
                menpai_abbr = "TL"
            elif menpai.find('灵鹫宫') >= 0:
                menpai_abbr = "LJ"
            elif menpai.find('朝廷') >= 0:
                menpai_abbr = "CT"
            elif menpai.find('明教') >= 0:
                menpai_abbr = "MJ"
            elif menpai.find('古墓') >= 0:
                menpai_abbr = "GM"
            elif menpai.find('星宿') >= 0:
                menpai_abbr = "XX"
            elif menpai.find('无门派') >= 0:
                menpai_abbr = "BX"

        return menpai_abbr

    def menpaiinfo(self, name, line, wildcards):
        loginroom = wildcards[0]
        menpai = wildcards[1]
        self.session.setVariable("loginroom", loginroom)
        self.session.setVariable("family/family_name", menpai)
        self.menpai = self.getmenpai()

    def bankinfo(self, name, line, wildcards):
        self.deposit = wildcards[0]

    def peform_action(self, pfm: PerformInfo, enemy = None, beforeAction: str = None, afterAction: str = None):
        # 先进行准备工作
        if beforeAction:
            self.session.writeline(beforeAction)
        # 1. 确认加力状态
        if not (pfm.enforce == 0):
            self.session.writeline("enforce {}".format(pfm.enforce))

        # 2. 确认武器状态，暂时有武器，所以装备时需要重新装备
        if pfm.needWeapon and hasattr(self, "_noweapon") and self._noweapon:
            #self.session.writeline("unwield right")
            self.session.writeline("wield {} at right".format(pfm.weapon))
            #self.session.writeline("wield {} 2 at right".format(pfm.weapon))
            pass
        else:
            #左单手空也可以发招
            #self.session.writeline("unwield right")
            pass
        

        # 暂时不确认特殊招式如果没激发是否能发出来，试试看
        if enemy:
            cmd = "perform {} {}".format(pfm.zhaoshi, enemy)
        else:
            cmd = "perform {}".format(pfm.zhaoshi)

        self.session.writeline(cmd)

        # 进行收尾工作(如果有加力，取消加力会不会导致招式失败？)
        if pfm.enforce != 0:
            self.session.writeline("enforce 0")

        if afterAction:
            self.session.writeline(afterAction)

    def new_perform(self, name, line, wildcards):
        pfm = wildcards[0]
        npc = wildcards[1]
        menpai = self.session.getVariable("menpai")

        pfms =  AVAILABLE_PERFORMS[menpai]
        if pfm in pfms.keys():
            pfm_info = pfms[pfm]
            self.peform_action(pfm_info, npc)

    def loadCharSpecialInfo(self):
        menpai = self.getmenpai()
        char   = self.session.getVariable("id")
        menpaiInfoLoaded = self.session.getVariable("menpaiLoaded", False)
        #menpaiInfoLoaded = "ali_npfm" in self.session.alis.keys()
        #if not menpaiInfoLoaded:
        if not self._menpaiInfoLoaded:
            # 更新门派自动捡东西设定
            if menpai in AUTO_GETS_MENPAI.keys():
                additional = AUTO_GETS_MENPAI[menpai]
                for id, match in additional.items():
                    tri_id = f"auto_{id}"
                    self._triggers[tri_id] = SimpleTrigger(self.session, patterns = match, code = f"get {id}", id = tri_id, enabled = False, group = "autoget")

                self.session.addTriggers(self._triggers)

            # 更新门派便捷路径设定
            self.mapper.UpdateLinksOfMenpai(menpai)
            self.mapper.UpdateLinksOfChar(char)

            # 更新门派perform设定
            if menpai in AVAILABLE_PERFORMS.keys():
                pfms = AVAILABLE_PERFORMS[menpai]
                ali_npfm = "^({})(?:\s+(\S.+))?$".format("|".join(pfms.keys()))
                self._aliases["ali_npfm"] = Alias(self.session, ali_npfm, id = "ali_npfm", onSuccess = self.new_perform, )
                self.session.addAlias(self._aliases["ali_npfm"])

            if menpai in GEMBOX_MENPAI.keys():
                self.session.setVariable("gembox", GEMBOX_MENPAI[menpai])
            else:
                self.session.setVariable("gembox", "jin nang")


            # 置标识位，确保只更新一次
            self.info("门派特定信息加载完成", "门派")
            self.session.setVariable("menpaiLoaded", True)
            self._menpaiInfoLoaded = True

    async def execute(self, cmd = "score", *args, **kwargs):
        try:
            self.reset()
            self.tri_start.enabled = True
            self.session.writeline(cmd)

            await self.tri_stop.triggered()
            self.session.setVariable("id", self.charid)
            self.session.setVariable("name", self.charname)
            self.session.setVariable("menpai", self.menpai)
            self.session.setVariable("deposit", self.deposit)

            self.loadCharSpecialInfo()

            self._onSuccess(self.id, cmd, None, None)
            external_on_success = kwargs.get("onSuccess", None)
            if external_on_success:
                external_on_success(self.id, cmd, None, None)
            
            return self.SUCCESS

        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")