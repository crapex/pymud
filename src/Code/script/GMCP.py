import json
import threading
from datetime import datetime
from pymud import GMCPTrigger,DotDict
import os
from .misc.formatMudStr import remove_ansi_color

#将GMCP字符串转为字典，方便提取信息，根据最开始的{符号，和结束的}符号，提取中间的字符串，然后用json.loads转为字典
def GMCP2Dict(gmcp_str):
    # 提取出JSON部分
    json_str = gmcp_str[gmcp_str.index('{'):gmcp_str.rindex('}')+1]
    # 使用json.loads将JSON字符串转换为字典
    return json.loads(json_str,strict=False)

class GMCP:
    def __init__(self, session, *args, **kwargs):
        self._gmcps = {}
        self.session = session
        self._gmcps['GMCP.Status'] = GMCPTrigger(self.session, r"GMCP.Status", onSuccess=self.GMCP_Handler)
        self._gmcps['GMCP.Move'] = GMCPTrigger(self.session, r"GMCP.Move", onSuccess=self.GMCP_Move)
        self._gmcps['GMCP.Combat'] = GMCPTrigger(self.session, r"GMCP.Combat", onSuccess=self.GMCP_Handler)

        self.char_status = DotDict()
        self.char_pos = DotDict()
        self.combat_time = None

    def GMCP_Move(self, name, line, wildcards):
        threading.Thread(target=self.handle_gmcp_move, args=(name, line, wildcards)).start()

    def handle_gmcp_move(self, name, line, wildcards):
        self.char_pos.update(GMCP2Dict(line))
        for k,v in self.char_pos.items():
            self.session.setVariable('gmcp_'+k, v)

    def GMCP_Handler(self, name, line, wildcards):
        self.char_status.update(GMCP2Dict(line))
        for k,v in self.char_status.items():
            vv = remove_ansi_color(v)
            self.session.setVariable(k, vv)
