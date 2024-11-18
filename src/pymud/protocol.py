import logging, asyncio, datetime, traceback
from asyncio import BaseTransport, Protocol
from .settings import Settings

IAC = b"\xff"           # TELNET 命令字 IAC
DONT = b"\xfe"
DO = b"\xfd"
WONT = b"\xfc"
WILL = b"\xfb"
SE = b"\xf0"
NOP = b"\xf1"
DM = b"\xf2"
BRK = b"\xf3"
IP = b"\xf4"
AO = b"\xf5"
AYT = b"\xf6"
EC = b"\xf7"
EL = b"\xf8"
GA = b"\xf9"
SB = b"\xfa"

LOGOUT = b"\x12"
ECHO = b"\x01"

CHARSET = b"*"
REQUEST = 1
ACCEPTED = 2
REJECTED = 3
TTABLE_IS = 4
TTABLE_REJECTED = 5
TTABLE_ACK = 6
TTABLE_NAK = 7

# TELNET & MUD PROTOCOLS OPTIONS
#IAC DO TTYPE        x18      https://tintin.mudhalla.net/protocols/mtts/
#IAC DO NAWS            x1F   Negotiate About Window Size  https://www.rfc-editor.org/rfc/rfc1073.html
#IAC DO NEW_ENVIRON    b"'"     https://tintin.mudhalla.net/protocols/mnes/
#IAC WILL b'\xc9'        GMCP 201   https://tintin.mudhalla.net/protocols/gmcp/
#IAC WILL b'F'        MSSP 70         https://tintin.mudhalla.net/protocols/mssp/
#IAC WILL CHARSET        b"*"      https://www.rfc-editor.org/rfc/rfc2066.html
#IAC WILL b'Z'        90, MUD Sound Protocol, MSP   http://www.zuggsoft.com/zmud/msp.htm

LINEMODE = b'"'         # LINEMODE, rfc1184 https://www.rfc-editor.org/rfc/rfc1184.html
SGA   = b"\x03"         # SUPPRESS GO AHEAD, rfc858 https://www.rfc-editor.org/rfc/rfc858.html

TTYPE = b"\x18"         # MUD终端类型标准，Mud Terminal Type Standard, https://tintin.mudhalla.net/protocols/mtts/
NAWS  = b"\x1f"         # 协商窗口尺寸， RFC1073， Negotiate About Window Size,  https://www.rfc-editor.org/rfc/rfc1073.html
MNES  = b"'"            # MUD环境标准，MUD NEW-ENVIRON Standard， https://tintin.mudhalla.net/protocols/mnes/

# 通用MUD通信协议, Generic Mud Communication Protocol, https://tintin.mudhalla.net/protocols/gmcp/
GMCP  = b"\xc9"         

# MUD服务器数据协议, Mud Server Data Protocol, https://tintin.mudhalla.net/protocols/msdp/
MSDP  = b"E"            
MSDP_VAR            = 1
MSDP_VAL            = 2
MSDP_TABLE_OPEN     = 3
MSDP_TABLE_CLOSE    = 4
MSDP_ARRAY_OPEN     = 5
MSDP_ARRAY_CLOSE    = 6

# MUD服务器状态协议， Mud Server Status Protocol, https://tintin.mudhalla.net/protocols/mssp/
MSSP  = b"F"   
MSSP_VAR = 1
MSSP_VAL = 2

# MUD客户端压缩协议，V1V2V3版， 参见 http://www.zuggsoft.com/zmud/mcp.htm, https://tintin.mudhalla.net/protocols/mccp/ 
# MCCP V1 使用选项85(U)作为协商选项，于1998年定义； 
# 2000年， 规定了MCCP V2，使用选项86（V）作为协商选项。
# 此后，MCCP1由于子协商内容非法， 2004年被弃用。当前所有MUD服务器端均切换到支持V2版协议。
# 2019年，V3协议被定义，但作为一个新协议使用，当前尚未支持。
MCCP1 = b"U"            # MUD客户端压缩协议V1，已被弃用
MCCP2 = b"V"            # MUD客户端压缩协议V2， Mud Client Compression Protocol， https://tintin.mudhalla.net/protocols/mccp/
MCCP3 = b"W"            # MUD客户端压缩协议V3, V2版同样可参见 http://www.zuggsoft.com/zmud/mcp.htm

# MUD声音协议, MUD Sound Protocol,  http://www.zuggsoft.com/zmud/msp.htm
MSP   = b"Z"      

# MUD扩展协议, MUD eXtension Protocol, http://www.zuggsoft.com/zmud/mxp.htm
MXP   = b"["            

_cmd_name_str = {
    IAC     : "IAC",
    WILL    : "WILL",
    WONT    : "WONT",
    DO      : "DO",
    DONT    : "DONT",
    SB      : "SB",
    SE      : "SE",
}

_option_name_str = {
    LINEMODE: "LINEMODE",
    SGA     : "SGA",

    ECHO    : "ECHO",
    CHARSET : "CHARSET",
    TTYPE   : "TTYPE",
    NAWS    : "NAWS",
    MNES    : "MNES",
    GMCP    : "GMCP",
    MSDP    : "MSDP",
    MSSP    : "MSSP",
    MCCP2   : "MCCP2",
    MCCP3   : "MCCP3",
    MSP     : "MSP",
    MXP     : "MXP"
}

def name_command(cmd):
    if cmd in _cmd_name_str.keys():
        return _cmd_name_str[cmd]
    else:
        return cmd

def name_option(opt):
    if opt in _option_name_str.keys():
        return _option_name_str[opt]
    return opt

class MudClientProtocol(Protocol):
    """
    适用于MUD客户端的asyncio的协议实现
    基本协议： TELNET
    扩展协议： GMCP, MCDP, MSP, MXP等等
    """

    def __init__(self, session, *args, **kwargs) -> None:
        """
        MUD客户端协议实现, 参数包括：     
          + session: 管理protocol的会话   
        除此之外，还可以接受的命名参数包括：
          + onConnected:    当连接建立时的回调，包含2个参数： MudClientProtocol本身，以及生成的传输Transport对象 
          + onDisconnected: 当连接断开时的回调，包含1个参数： MudClientProtocol本身
        """

        self.log = logging.getLogger("pymud.MudClientProtocol")
        self.session = session                                              # 数据处理的会话
        self.connected = False                                              # 连接状态标识                              
        self._iac_handlers = dict()                                         # 支持选项协商处理函数
        self._iac_subneg_handlers = dict()                                  # 处理选项子协商处理函数

        for k, v in _option_name_str.items():
            func = getattr(self, f"handle_{v.lower()}", None)               # 选项协商处理函数，处理函数中使用小写字母
            self._iac_handlers[k] = func
            subfunc = getattr(self, f"handle_{v.lower()}_sb", None)         # 子协商处理函数
            self._iac_subneg_handlers[k] = subfunc

        self.encoding = Settings.server["default_encoding"]                 # 字节串基本编码
        self.encoding_errors = Settings.server["encoding_errors"]           # 编码解码错误时的处理
        self.mnes = Settings.mnes

        self._extra = dict()                    # 存储有关的额外信息的词典

        self.mssp = dict()                      # 存储MSSP协议传来的服务器有关参数
        self.msdp = dict()                      # 存储MSDP协议传来的服务器所有数据
        self.gmcp = dict()                      # 存储GMCP协议传来的服务器所有数据

        self._extra.update(kwargs=kwargs)

        self.on_connection_made = kwargs.get("onConnected", None)       # 连接时的回调
        self.on_connection_lost = kwargs.get("onDisconnected", None)    # 断开时的回调

    def get_extra_info(self, name, default=None):
        """获取传输信息或者额外的协议信息."""
        if self._transport:
            default = self._transport._extra.get(name, default)
        return self._extra.get(name, default)
        
    def connection_made(self, transport: BaseTransport) -> None:
        self._transport = transport                                         # 保存传输
        self._when_connected = datetime.datetime.now()                      # 连接建立时间
        self._last_received = datetime.datetime.now()                       # 最后收到数据时间

        #self.session.set_transport(self._transport)                         # 将传输赋值给session

        # self.reader = self._reader_factory(loop = self.loop, encoding = self.encoding, encoding_errors = self.encoding_errors)
        # self.writer = self._writer_factory(self._transport, self, self.reader, self.loop)

        self._state_machine = "normal"                                      # 状态机标识, normal,
        self._bytes_received_count = 0                                      # 收到的所有字节数（含命令）
        self._bytes_count = 0                                               # 收到的字节数（不含协商），即写入streamreader的字节数
        self.connected = True
        
        self.log.info(f'已建立连接到: {self}.')

        # 若设置了onConnected回调函数，则调用
        if self.on_connection_made and callable(self.on_connection_made):
            self.on_connection_made(self._transport)

        # 设置future
        #self._waiter_connected.set_result(True)

    def connection_lost(self, exc) -> None:
        if not self.connected:
            return

        self.connected = False

        if exc is None:
            self.log.info(f'连接已经断开: {self}.')
            self.session.feed_eof()
        else:
            self.log.warning(f'由于异常连接已经断开: {self}, {exc}.')
            self.session.set_exception(exc)

        self._transport.close()
        self._transport = None
        #self.session.set_transport(None)

        # 若设置了onConnected回调函数，则调用
        if self.on_connection_lost and callable(self.on_connection_lost):
            self.on_connection_lost(self)

        self._state_machine = "normal"          # 状态机标识恢复到 normal,

    def eof_received(self):
        self.log.debug("收到服务器发来的EOF, 连接关闭.")
        self.connection_lost(None)

    def data_received(self, data: bytes) -> None:
        self._last_received = datetime.datetime.now()

        for byte in data:
            byte = bytes([byte,])
            self._bytes_received_count += 1
            
            # 状态机为 正常，接下来可能接收到命令包括 IAC 或 正常字符
            if self._state_machine == "normal":  
                if byte == IAC:         # 若接收到IAC，状态机切换到等待命令
                    self._state_machine = "waitcommand"
                    self.session.go_ahead()
                else:                   # 否则收到为正常数据，传递给reader
                    self.session.feed_data(byte)
            
            # 状态机为 等待命令，接下来应该收到的字节仅可能包括： WILL/WONT/DO/DONT/SB
            elif self._state_machine == "waitcommand":
                if byte in (WILL, WONT, DO, DONT):              # 此时，后续选项仅1个字节
                    self._iac_command = byte
                    self._state_machine = "waitoption"   # 后续为选项
                elif byte == SB:
                    self._iac_command = byte
                    self._iac_sub_neg_data = IAC+SB              # 保存完整子协商命令
                    self._state_machine = "waitsubnegotiation"   # 后续为子协商，以 IAC SE终止
                elif byte == NOP:                                # 空操作 TODO 确认空操作是否为IAC NOP，没有其他
                    self.log.debug(f"收到服务器NOP指令: IAC NOP")
                    self._state_machine = "normal"
                    # 对NOP信号和GA信号处理相同
                    self.session.go_ahead()
                elif byte == GA:
                    self.log.debug(f"收到服务器GA指令: IAC GA")
                    self._state_machine = "normal"
                    # 对NOP信号和GA信号处理相同，让缓冲区全部发送出去
                    self.session.go_ahead()
                else:                                            # 错误数据，无法处置，记录错误，并恢复状态机到normal
                    self.log.error(f"与服务器协商过程中，收到未处理的非法命令: {byte}")
                    self._state_machine = "normal"

            elif self._state_machine == "waitoption":            # 后续可以接受选项
                if byte in _option_name_str.keys():
                    iac_handler = self._iac_handlers[byte]       # 根据选项选择对应的处理函数
                    if iac_handler and callable(iac_handler):
                        self.log.debug(f"收到IAC选项协商: IAC {name_command(self._iac_command)} {name_option(byte)}, 并传递至处理函数 {iac_handler.__name__}")
                        iac_handler(self._iac_command)           # 执行IAC协商
                    else:
                        self.log.debug(f"收到不支持(尚未定义处理函数)的IAC协商: IAC {name_command(self._iac_command)} {name_option(byte)}, 将使用默认处理（不接受）")
                        self._iac_default_handler(self._iac_command, byte)
                    self._state_machine = "normal"               # 状态机恢复到正常状态
                else:
                   self.log.warning(f"收到不识别(不在定义范围内)的IAC协商: IAC {name_command(self._iac_command)} {name_option(byte)}, 将使用默认处理（不接受）")
                   self._iac_default_handler(self._iac_command, byte)
                   self._state_machine = "normal"                # 状态机恢复到正常状态
            
            elif self._state_machine == "waitsubnegotiation":    # 当收到了IAC SB
                # 此时，下一个字节应为可选选项，至少不应为IAC
                if byte != IAC:
                    self._iac_sub_neg_option = byte              # 保存子协商选项
                    self._iac_sub_neg_data += byte               # 保存子协商全部内容
                    self._state_machine = "waitsbdata"           # 下一状态，等待子协商数据
                else:     
                    self.log.error('子协商中在等待选项码的字节中错误收到了IAC')                                       
                    self._state_machine = "normal"               # 此时丢弃所有前面的状态
            
            elif self._state_machine == "waitsbdata":           
                self._iac_sub_neg_data += byte                   # 保存子协商全部内容
                if byte == IAC:
                    # 在子协商过程中，如果收到IAC，则下一个字节可能是其他，或者SE。
                    #   当下一个字节为其他时，IAC是子协商中的一个字符
                    #   当下一个字节为SE时，表示子协商命令结束
                    # 基于上述理由，在子协商状态下，状态机的转换规则为：
                    #   1. 子协商中收到IAC后，状态切换为 waitse
                    #   2. 在waitse之后，如果收到SE，则子协商结束，回复到normal
                    #   3. 在waitse之后，如果收到的不是SE，则回复到waitsubnegotiation状态
                    self._state_machine = "waitse"
                else:
                    # 子协商过程中，收到的所有非IAC字节，都是子协商的具体内容
                    pass

            elif self._state_machine == "waitse":
                self._iac_sub_neg_data += byte                   # 保存子协商全部内容
                if byte == SE:                                   # IAC SE 表示子协商已接收完毕
                    self._state_machine = "normal"
                    if self._iac_sub_neg_option in _option_name_str.keys():
                        iac_subneg_handler = self._iac_subneg_handlers[self._iac_sub_neg_option]       # 根据选项子协商选择对应的处理函数
                        if iac_subneg_handler and callable(iac_subneg_handler):
                            self.log.debug(f"收到{name_option(self._iac_sub_neg_option)}选项子协商: {self._iac_sub_neg_data}, 并传递至处理函数 {iac_subneg_handler.__name__}")
                            iac_subneg_handler(self._iac_sub_neg_data)
                        else:
                            self.log.debug(f"收到不支持(尚未定义处理函数)的{name_option(self._iac_sub_neg_option)}选项子协商: {self._iac_sub_neg_data}, 将丢弃数据不处理.")
                else:
                    self._state_machine = "waitsbdata"

    # public properties
    @property
    def duration(self):
        """自客户端连接以来的总时间，以秒为单位，浮点数表示"""
        return (datetime.datetime.now() - self._when_connected).total_seconds()

    @property
    def idle(self):
        """自收到上一个服务器发送数据以来的总时间，以秒为单位，浮点数表示"""
        return (datetime.datetime.now() - self._last_received).total_seconds()

    # public protocol methods
    def __repr__(self):
        "%r下的表述"
        hostport = self.get_extra_info("peername", ["-", "closing"])[:2]
        return "<Peer {0} {1}>".format(*hostport)
    
    def _iac_default_handler(self, cmd, option):
        """
        默认IAC协商处理, 对于不识别的选项，直接回复不接受
        对于WILL,WONT回复DONT; 对于DO,DONT回复WONT
        """
        if cmd in (WILL, WONT):
            ack = DONT

        elif cmd in (DO, DONT):
            ack = WONT

        else:
            # 非正常情况，此由前述函数调用和处理确保为为不可能分支。为保留代码完整性而保留
            self.log.error(f'选项协商进入非正常分支，参考数据: , _iac_default_handler, {cmd}, {option}')
            return
        
        self.session.write(IAC + ack + option)
        self.log.debug(f'使用默认协商处理拒绝了服务器的请求的 IAC {name_command(cmd)} {name_option(option)}, 回复为 IAC {name_command(ack)} {name_option(option)}')

    # SGA done.
    def handle_sga(self, cmd):
        """
        SGA, supress go ahead, 抑制 GA 信号。在全双工环境中，不需要GA信号，因此默认同意抑制
        """
        if cmd == WILL:
            if Settings.server["SGA"]:
                self.session.write(IAC + DO + SGA)
                self.log.debug(f'发送选项协商, 同意抑制GA信号 IAC DO SGA.')
            else:
                self.session.write(IAC + DONT + SGA)
                self.log.debug(f'发送选项协商, 不同意抑制GA信号 IAC DONT SGA.')

        else:
            self.log.warning(f"收到服务器的未处理的SGA协商: IAC {name_command(cmd)} SGA")

    # ECHO done.
    def handle_echo(self, cmd):
        """
        ECHO, 回响。默认不同意
        """
        if cmd == WILL:
            if Settings.server["ECHO"]:
                self.session.write(IAC + DO + ECHO)
                self.log.debug(f'发送选项协商, 同意ECHO选项协商 IAC DO ECHO.')
            else:
                self.session.write(IAC + DONT + ECHO)
                self.log.debug(f'发送选项协商, 不同意ECHO选项协商 IAC DONT ECHO.')
            
        else:
            self.log.warning(f"收到服务器的未处理的ECHO协商: IAC {name_command(cmd)} ECHO")

    def handle_charset(self, cmd):
        """
        CHARSET, 字符集协商 https://www.rfc-editor.org/rfc/rfc2066.html
        """
        nohandle = False
        if cmd == WILL:
            # 1. 回复同意CHARSET协商
            self.session.write(IAC + DO + CHARSET)
            self.log.debug(f'发送选项协商, 同意CHARSET协商 IAC DO CHARSET.等待子协商')
        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的CHARSET协商: IAC {name_command(cmd)} TTYPE")

    def handle_charset_sb(self, data: bytes):
        '字符集子协商'
        # b'\xff\xfa*\x01;UTF-8\xff\xf0'
        # IAC SB CHARSET \x01 ; UTF-8 IAC SE
        unhandle = True
        self.log.debug('charset 子协商')
        if data[3] == REQUEST:
            charset_list = data[4:-2].decode(self.encoding).lower().split(';')
            # 若服务器存在UTF-8选项，默认选择UTF-8
            if 'utf-8' in charset_list:
                sbneg = bytearray()
                sbneg.extend(IAC + SB + CHARSET)
                sbneg.append(ACCEPTED)
                sbneg.extend(b"UTF-8")
                sbneg.extend(IAC + SE)
                self.session.write(sbneg)
                self.log.debug(f'发送CHARSET子协商，同意UTF-8编码 IAC SB ACCEPTED "UTF-8" IAC SE')
                unhandle = False

        if unhandle:
            self.log.warning(f'未处理CHARSET子协商: {data}')

    def handle_ttype(self, cmd):
        """
        处理MUD终端类型标准协议的协商 https://tintin.mudhalla.net/protocols/mtts/
        server - IAC DO TTYPE
        client - IAC WILL TTYPE
        等待子协商，子协商见下面的 handle_ttype_sb
        """
        nohandle = False
        if cmd == WILL:
            nohandle = True
        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            # 1. 回复同意MTTS协商
            self.session.write(IAC + WILL + TTYPE)
            self._mtts_index = 0
            self.log.debug(f'发送选项协商, 同意MTTS(TTYPE)协商 IAC WILL TTYPE.等待子协商')
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的TTYPE/MTTS协商: IAC {name_command(cmd)} TTYPE")

    def handle_ttype_sb(self, data):
        """
        处理TTYPE/MTTS的子协商, 详细信息参见 handle_ttype
        server - IAC   SB TTYPE SEND IAC SE
        client - IAC   SB TTYPE IS   "TINTIN++" IAC SE
        server - IAC   SB TTYPE SEND IAC SE
        client - IAC   SB TTYPE IS   "XTERM" IAC SE
        server - IAC   SB TTYPE SEND IAC SE
        client - IAC   SB TTYPE IS   "MTTS 137" IAC SE
        """
        IS, SEND = b"\x00", 1

        # 服务器子协商一定为6字节，内容为 IAC SB TTYPE SEND IAC SE
        # 由于子协商data的IAC SB TTYPE和后面的IAC SE都是固定写进去的，在之前判断过，因此此处不判断
        # 因此判断服务器子协商命令，仅判断长度为6和第4字节为SEND
        if (len(data) == 6) and (data[3] == SEND):  
            if self._mtts_index == 0:
                # 第一次收到，回复客户端全名，全大写
                self.session.write(IAC + SB + TTYPE + IS + Settings.__appname__.encode(self.encoding, self.encoding_errors) + IAC + SE)
                self._mtts_index += 1
                self.log.debug(f'回复第一次MTTS子协商: IAC SB TTYPE IS "{Settings.__appname__}" IAC SE')
            elif self._mtts_index == 1:
                # 第二次收到，回复客户端终端类型，此处默认设置为XTERM(使用系统控制台), ANSI（代码已支持），后续功能完善后再更改
                # VT100 https://tintin.mudhalla.net/info/vt100/
                # XTERM https://tintin.mudhalla.net/info/xterm/
                self.session.write(IAC + SB + TTYPE + IS + b"XTERM" + IAC + SE)
                self._mtts_index += 1
                self.log.debug('回复第二次MTTS子协商: IAC SB TTYPE IS "XTERM" IAC SE')
            elif self._mtts_index == 2:
                # 第三次收到，回复客户端终端支持的标准功能，此处默认设置783（支持ANSI, VT100, UTF-8, 256 COLORS, TRUECOLOR, MNES），后续功能完善后再更改
                # 根据完善的终端模拟功能，修改终端标准
                #       1 "ANSI"              Client supports all common ANSI color codes.
                #       2 "VT100"             Client supports all common VT100 codes.
                #       4 "UTF-8"             Client is using UTF-8 character encoding.
                #       8 "256 COLORS"        Client supports all 256 color codes.
                #      16 "MOUSE TRACKING"    Client supports xterm mouse tracking.
                #      32 "OSC COLOR PALETTE" Client supports OSC and the OSC color palette.
                #      64 "SCREEN READER"     Client is using a screen reader.
                #     128 "PROXY"             Client is a proxy allowing different users to connect from the same IP address.
                #     256 "TRUECOLOR"         Client supports truecolor codes using semicolon notation.
                #     512 "MNES"              Client supports the Mud New Environment Standard for information exchange.
                #    1024 "MSLP"              Client supports the Mud Server Link Protocol for clickable link handling.
                #    2048 "SSL"               Client supports SSL for data encryption, preferably TLS 1.3 or higher.
                self.session.write(IAC + SB + TTYPE + IS + b"MTTS 783" + IAC + SE)
                self._mtts_index += 1
                self.log.debug('回复第三次MTTS子协商: IAC SB TTYPE IS "MTTS 783" IAC SE')
            else:
                self.log.warning(f'收到第{self._mtts_index + 1}次(正常为3次)的MTTS子协商, 将不予应答')
        else:
            self.log.warning(f'收到不正确的MTTS子协商: {data}，将不予应答')

    def handle_naws(self, cmd):
        """
        处理屏幕尺寸的协商 https://www.rfc-editor.org/rfc/rfc1073.html
        服务器发送请求协商尺寸时，逻辑为：
        (server sends)  IAC DO NAWS
        (client sends)  IAC WILL NAWS
        (client sends)  IAC SB NAWS 0(WIDTH1) 80(WIDTH0) 0(HEIGHT1) 24(HEIGHT0) IAC SE
        本客户端不主动协商需要NAWS，只有当服务器协商需要NAWS时，才进行协商。
        协商给定的默认尺寸为: self._extra["naws_width"]和self._extra["naws_height"]
        """
        nohandle = False
        if cmd == WILL:
            nohandle = True
        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:         # 正常情况下，仅处理服务器的 IAC DO NAWS
            # 1. 回复同意NAWS
            self.session.write(IAC + WILL + NAWS)
            self.log.debug(f'发送选项协商, 同意NAWS协商 IAC WILL NAWS.')
            # 2. 发送子协商确认尺寸
            width_bytes = Settings.client["naws_width"].to_bytes(2, "big")
            height_bytes = Settings.client["naws_height"].to_bytes(2, "big")
            sb_cmd = IAC + SB + NAWS + width_bytes + height_bytes + IAC + SE
            self.session.write(sb_cmd)
            self.log.debug(
                '发送NAWS选项子协商, 明确窗体尺寸。IAC SB NAWS (width = %d, height = %d) IAC SE' %
                (Settings.client["naws_width"], Settings.client["naws_height"])
            )
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的NAWS协商: IAC {name_command(cmd)} NAWS")
    
    def handle_mnes(self, cmd):
        """
        处理MUD新环境标准, Mud New-Env Standard的协商 https://tintin.mudhalla.net/protocols/mnes/
        MNES作为MTTS的扩展。MTTS设计为只能响应特定的客户端特性，MNES可以提供更多的扩展
        """
        nohandle = False
        if cmd == WILL:
            nohandle = True
        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            # 1. 回复同意MNES
            self.session.write(IAC + WILL + MNES)
            self.log.debug(f'发送选项协商, 同意MNES协商 IAC WILL MNES. 等待服务器子协商')
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的MNES协商: IAC {name_command(cmd)} MNES")

    def handle_mnes_sb(self, data: bytes):
        """
        处理MNES的子协商 https://tintin.mudhalla.net/protocols/mnes/

        """
        # server - IAC   SB MNES SEND VAR "CLIENT_NAME" SEND VAR "CLIENT_VERSION" IAC SE
        # client - IAC   SB MNES IS   VAR "CLIENT_NAME" VAL "TINTIN++" IAC SE
        # client - IAC   SB MNES IS   VAR "CLIENT_VERSION" VAL "2.01.7" IAC SE
        # server - IAC   SB MNES SEND VAR "CHARSET" IAC SE
        # client - IAC   SB MNES INFO VAR "CHARSET" VAL "ASCII" IAC SE
        def send_mnes_value(var: str, val: str):
            sbneg = bytearray()
            sbneg.extend(IAC + SB + MNES)
            sbneg.append(IS)
            sbneg.extend(var.encode(self.encoding))
            sbneg.append(VAL)
            sbneg.extend(val.encode(self.encoding))
            sbneg.extend(IAC + SE)
            self.session.write(sbneg)
            self.log.debug(f"回复MNES请求: {var} = {val}")

        IS, SEND, INFO = 0, 1, 2
        VAR, VAL = 0, 1
        
        request_var = list()
        var_name = bytearray()
        state_machine = "wait_cmd"
        for idx in range (3, len(data) - 1):
            byte = data[idx]
            if state_machine == "wait_cmd":              # 下一个字节为命令, 应该是 SEND
                if byte == SEND:
                    state_machine = "wait_var"

            elif state_machine == "wait_var":
                if byte == VAR:
                    state_machine = "wait_var_content"
                    var_name.clear()
            
            elif state_machine == "wait_var_content":
                if byte not in (SEND, IAC):
                    var_name.append(byte)
                else:
                    if len(var_name) > 0:
                        request_var.append(var_name.decode(self.encoding))
                    state_machine = "wait_cmd"

        self.log.debug(f"收到{len(request_var)}个MNES子协商请求变量: {request_var}")
        for var_name in request_var:
            if var_name in self.mnes.keys():
                send_mnes_value(var_name, self.mnes[var_name])

    def handle_gmcp(self, cmd):
        """
        处理 通用MUD通信协议, GMCP的协商 https://tintin.mudhalla.net/protocols/gmcp/
        server - IAC WILL GMCP
        client - IAC   DO GMCP
        client - IAC   SB GMCP 'MSDP {"LIST" : "COMMANDS"}' IAC SE
        server - IAC   SB GMCP 'MSDP {"COMMANDS":["LIST","REPORT","RESET","SEND","UNREPORT"]}' IAC SE
        """
        nohandle = False
        if cmd == WILL:
            # 1. 回复同意GMCP与否
            if Settings.server["GMCP"]:
                self.session.write(IAC + DO + GMCP)
                self.log.debug(f'发送选项协商, 同意GMPC协商 IAC DO GMCP.')
            else:
                self.session.write(IAC + DONT + GMCP)
                self.log.debug(f'发送选项协商, 不同意GMPC协商 IAC DONT GMCP.')

            # 2. 发送GMCP子协商，获取MSDP的相关命令？待定后续处理
            # 支持了MSDP协议， 不使用GMCP获取MSDP的有关命令，即不使用 MDSP over GMCP
            # self.session.write(IAC + SB + GMCP + b'MSDP {"LIST" : "COMMANDS"}' + IAC + SE)
            # self.log.debug(f'发送GMPC子协商 IAC SB GMCP ''MSDP {"LIST" : "COMMANDS"}'' IAC SE.')
        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的GMCP协商: IAC {name_command(cmd)} GMCP")

    def handle_gmcp_sb(self, data: bytes):
        """
        处理GMCP的子协商 https://tintin.mudhalla.net/protocols/gmcp/
        """
        # Evennia GMCP 数据实例：
        # 在发送IAC DO GMCP之后，当发送MSDP子协商请求时，会同时收到MSDP数据和GMCP数据
        # b'\xff\xfa\xc9Core.Lists ["commands", "lists", "configurable_variables", "reportable_variables", "reported_variables", "sendable_variables"]\xff\xf0'
        # b'\xff\xfa\xc9Reportable.Variables ["name", "location", "desc"]\xff\xf0'
        # b'\xff\xfa\xc9GMCP.Move [{"result":"true","dir":["southeast","southwest","northup"],"short":"\xb9\xcf\xb2\xbd"}]\xff\xf0'
        # b'\xff\xfa\xc9GMCP.Status {"qi":1045,"name":"\xc4\xbd\xc8\xdd\xca\xc0\xbc\xd2\xbc\xd2\xd4\xf4","id":"xqtraveler\'s murong jiazei#7300006"}\xff\xf0',
        # 收到GMCP选项子协商: 
        # 服务器子协商长度不确定，中间使用字符串表示一系列内容，内容长度为总长度-5
        # 子协商总长度-5为子协商的状态内容，子协商前3个字节为IAC SB GMCP，后2个字节为IAC SE
        gmcp_data = data[3:-2].decode(self.encoding)
        
        space_split = gmcp_data.find(" ")
        name = gmcp_data[:space_split]
        value = gmcp_data[space_split+1:]
        
        # try:
        #     value = eval(value_str)
        # except:
        #     value = value_str

        self.log.debug(f'收到GMCP子协商数据: {name} = {value}')
        self.session.feed_gmcp(name, value)

    def handle_msdp(self, cmd):
        """
        处理 通用MUD服务器数据协议, MSDP的协商 https://tintin.mudhalla.net/protocols/msdp/
        """
        # server - IAC WILL MSDP
        # client - IAC   DO MSDP
        # client - IAC   SB MSDP MSDP_VAR "LIST" MSDP_VAL "COMMANDS" IAC SE
        # server - IAC   SB MSDP MSDP_VAR "COMMANDS" MSDP_VAL MSDP_ARRAY_OPEN MSDP_VAL "LIST" MSDP_VAL "REPORT" MSDP_VAL "SEND" MSDP_ARRAY_CLOSE IAC SE
        # client - IAC   SB MSDP MSDP_VAR "LIST" MSDP_VAL "REPORTABLE_VARIABLES" IAC SE
        # server - IAC   SB MSDP MSDP_VAR "REPORTABLE_VARIABLES" MSDP_VAL "HINT" IAC SE
        # client - IAC   SB MSDP MSDP_VAR "SEND" MSDP_VAL "HINT" IAC SE
        # server - IAC   SB MSDP MSDP_VAR "HINT" MSDP_VAL "THE GAME" IAC SE
        
        nohandle = False
        if cmd == WILL:
            # 1. 回复同意MSDP与否
            if Settings.server["MSDP"]:
                self.session.write(IAC + DO + MSDP)
                self.log.debug(f'发送选项协商, 同意MSDP协商 IAC DO MSDP.')
                self.send_msdp_sb(b"LIST", b"LISTS")
                self.send_msdp_sb(b"LIST", b"REPORTABLE_VARIABLES")

            else:
                self.session.write(IAC + DONT + MSDP)
                self.log.debug(f'发送选项协商, 不同意MSDP协商 IAC DONT MSDP.')
            
        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的MSDP协商: IAC {name_command(cmd)} MSDP")
    
    def send_msdp_sb(self, cmd: bytes, param: bytes):
        '''
        发送MSDP子协商，获取MSDP的相关数据
        '''
        sbneg = bytearray()
        sbneg.extend(IAC + SB + MSDP)
        sbneg.append(MSDP_VAR)
        sbneg.extend(cmd)
        sbneg.append(MSDP_VAL)
        sbneg.extend(param)
        sbneg.extend(IAC + SE)
        self.session.write(sbneg)
        self.log.debug(f'发送MSDP子协商查询支持的MSDP命令 IAC SB MSDP MSDP_VAR "{cmd.decode(self.encoding)}" MSDP_VAL "{param.decode(self.encoding)}" IAC SE.')

    def handle_msdp_sb(self, data):
        """
        处理MSDP的子协商 https://tintin.mudhalla.net/protocols/msdp/
        """
        # b'\xff\xfaE\x01commands\x02\x05\x02bot_data_in\x02client_gui\x02client_options\x02default\x02echo\x02external_discord_hello\x02get_client_options\x02get_inputfuncs\x02get_value\x02hello\x02login\x02monitor\x02monitored\x02list\x02report\x02send\x02unreport\x02repeat\x02supports_set\x02text\x02unmonitor\x02unrepeat\x02webclient_options\x06\xff\xf0'
        msdp_data = dict()      # 保存服务器可用msdp命令列表

        # 服务器子协商长度不确定，中间包含若干个VAR和表示变量值的对应若干个VAL（每个VAL可能以数组、表形式包含若干个）
        # 变量名和变量值都使用字符串表示
        # 子协商总长度-5为子协商的状态内容，子协商前3个字节为IAC SB MSDP，后2个字节为IAC SE
        var_name = bytearray()
        val_in_array = list()
        val_in_table = dict()
        val_in_text = bytearray()

        table_var_name, table_var_value = bytearray(), bytearray()

        state_machine = "wait_var"
        for idx in range (3, len(data) - 2):
            byte = data[idx]
            if state_machine == "wait_var":             # 下一个字节为类型 MSDP_VAR            
                if byte == MSDP_VAR:
                    # 接收变量名称, 
                    state_machine = "wait_var_name"
                    var_name.clear()                    # var_name等待接收变量名称
                else:
                    self.log.warning(f"MSDP状态机错误: 在状态wait_var时收到数据不是MSDP_VAR, 而是{str(byte)}")
            elif state_machine == "wait_var_name":
                if byte == MSDP_VAL:                    # MSDP_VAL表示变量名结束，下一个是value了
                    val_in_array.clear()
                    val_in_table.clear()
                    val_in_text.clear()
                    current_var = var_name.decode(self.encoding)
                    msdp_data[current_var] = None
                    state_machine = "wait_var_value"
                elif byte in (MSDP_ARRAY_OPEN, MSDP_ARRAY_CLOSE, MSDP_TABLE_OPEN, MSDP_TABLE_CLOSE):    # 理论上不会是这个
                    self.log.warning(f"MSDP状态机错误: 在状态wait_var_name时收到数据不是MSDP_VAL, 而是{byte}")
                    # 应该丢弃数据，直接返回 return
                else:
                    var_name.append(byte)
            elif state_machine == "wait_var_value":
                if byte == MSDP_ARRAY_OPEN:     # value是一个数组
                    state_machine = "wait_val_in_array"
                elif byte == MSDP_TABLE_OPEN:   # value是一个表，使用字典保存       
                    state_machine = "wait_val_in_table"
                elif byte in (IAC, MSDP_VAR, MSDP_VAL):     # 正常数据 value 结束
                    current_val = val_in_text.decode(self.encoding)
                    msdp_data[current_var] = current_val
                    state_machine = "wait_end"
                    self.log.debug(f"收到文本形式的MSDP子协商数据： {current_var} = '{current_val}'")
                else:                           # value是正常数据
                    val_in_text.append(byte)
            elif state_machine == "wait_val_in_array":
                if byte == MSDP_ARRAY_CLOSE:
                    # 最后一个val 已结束
                    val_in_array.append(val_in_text.decode(self.encoding))
                    val_in_text.clear()
                    msdp_data[current_var] = val_in_array
                    state_machine = "wait_end"
                    self.log.debug(f"收到数组形式的MSDP子协商数据： {current_var} = '{val_in_array}'")
                elif byte == MSDP_VAL:
                    if len(val_in_text) > 0:                # 一个VAL已完成，保存到array，后面还有val
                        val_in_array.append(val_in_text.decode(self.encoding))
                        val_in_text.clear()
                else:
                    val_in_text.append(byte)
            elif state_machine == "wait_val_in_table":
                if byte == MSDP_TABLE_CLOSE:
                    # 最后一组已结束
                    val_in_table[table_var_name.decode[self.encoding]] = table_var_value.decode[self.encoding]
                    msdp_data[current_var] = val_in_table
                    state_machine = "wait_end"
                    self.log.debug(f"收到表格形式的MSDP子协商数据： {current_var} = '{val_in_table}'")
                elif byte == MSDP_VAR:
                    if len(table_var_name) > 0:             # 上一个VAL已完成，保存到table，后面继续为VAR
                        val_in_table[table_var_name.decode[self.encoding]] = table_var_value.decode[self.encoding]
                        table_var_name.clear()
                        table_var_value.clear()
                    state_machine_table = "wait_table_var"
                elif byte == MSDP_VAL:
                    state_machine_table = "wait_table_val"
                else:
                    if state_machine_table == "wait_table_var":
                        table_var_name.append(byte)
                    elif state_machine_table == "wait_table_val":
                        table_var_value.append(byte)
                    else:
                        self.log.warning(f"MSDP状态机错误: 在状态wait_val_in_table时状态不正确，为{state_machine_table}，收到数据是{byte}")


        # 更新MSDP_支持的数据到服务器
        self.msdp.update(msdp_data)
        self.log.debug(f"MSDP服务器状态子协商处理完毕，共收到{len(msdp_data.keys())}组VAR/VAL数据.")

    def handle_mssp(self, cmd):
        """
        处理MUD服务器状态协议, MSSP的协商 https://tintin.mudhalla.net/protocols/mssp/
        server - IAC WILL MSSP
        client - IAC DO MSSP
        server - IAC SB MSSP MSSP_VAR "PLAYERS" MSSP_VAL "52" MSSP_VAR "UPTIME" MSSP_VAL "1234567890" IAC SE
        """
        nohandle = False
        if cmd == WILL:
            # 1. 回复同意MSSP协商
            if Settings.server["MSSP"]:
                self.session.write(IAC + DO + MSSP)
                self._mtts_index = 0
                self.log.debug(f'发送选项协商, 同意MSSP协商 IAC DO MSSP.等待子协商')
            else:
                self.session.write(IAC + DONT + MSSP)
                self.log.debug(f'发送选项协商, 不同意MSSP协商 IAC DONT MSSP.等待子协商')
        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的MSSP协商: IAC {name_command(cmd)} MSSP")
    
    def handle_mssp_sb(self, data):
        """
        处理MSSP的子协商
        server - IAC SB MSSP MSSP_VAR "PLAYERS" MSSP_VAL "52" MSSP_VAR "UPTIME" MSSP_VAL "1234567890" IAC SE
        # 以下为必须的状态信息
        NAME               Name of the MUD.
        PLAYERS            Current number of logged in players.
        UPTIME             Unix time value of the startup time of the MUD.  
        详细状态信息的定义，参见 https://tintin.mudhalla.net/protocols/mssp/
        """
        def add_svr_status(var: bytearray, val: bytearray):
            if len(var) > 0:     
                var_str = var.decode(self.encoding)
                val_str = val.decode(self.encoding)
                svrStatus[var_str] = val_str
                self.session.feed_mssp(var_str, val_str)
                self.log.debug(f"收到服务器状态(来自MSSP子协商): {var_str} = {val_str}")

        svrStatus = dict()      # 使用字典保存服务器发来的状态信息

        # 服务器子协商长度不确定，中间包含若干个VAR（VARIABLE，变量名）以及对应数目的VAL（VALUE，变量值）
        # 变量名和变量值都使用字符串表示
        # 子协商总长度-5为子协商的状态内容，子协商前3个字节为IAC SB MSSP，后2个字节为IAC SE
        var, val = bytearray(), bytearray()
        next_bytes = "type"
        for idx in range (3, len(data) - 2):
            byte = data[idx]
            if (byte == MSSP_VAR):
                # 表示前一组VAR, VAL已收到
                add_svr_status(var, val)
                # 重置var,val变量，以便收取后一个
                var.clear()                 
                val.clear()
                next_bytes = "var"
            elif (byte == MSSP_VAL):
                next_bytes = "val"
            else:
                if next_bytes == "var":
                    var.append(byte)
                elif next_bytes == "val":
                    val.append(byte)
                else:
                    self.log.warning("在MSSP子协商中收到非正常序列!!")

        # 数据处理完之后，结束的IAC SE之前，最后一组VAR/VAL还需添加进取
        add_svr_status(var, val)
        # 更新状态到服务器
        self.mssp.update(svrStatus)
        self.log.debug(f"MSSP服务器状态子协商处理完毕，共收到{len(svrStatus.keys())}组VAR/VAL数据.")

    def handle_mccp2(self, cmd):
        """
        处理MUD客户端压缩协议的协商V2 https://mudhalla.net/tintin/protocols/mccp/
        server - IAC WILL MCCP2
        client - IAC DONT MCCP2
        当前不接收客户端压缩(未实现）
        """
        nohandle = False
        if cmd == WILL:
            # 1. 回复不同意MCCP2协商
            if Settings.server["MCCP2"]:
                self.session.write(IAC + DO + MCCP2)
                self.log.debug(f'发送选项协商, 同意MCCP V2协商 IAC DO MCCP2')
            else:
                self.session.write(IAC + DONT + MCCP2)
                self.log.debug(f'发送选项协商, 不同意MCCP V2协商 IAC DONT MCCP2')

        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的MCCP V2协商: IAC {name_command(cmd)} MCCP2")

    def handle_mccp3(self, cmd):
        """
        处理MUD客户端压缩协议的协商V3 https://mudhalla.net/tintin/protocols/mccp/
        server - IAC WILL MCCP3
        client - IAC DONT MCCP3
        当前不接收客户端压缩(未实现）
        """
        nohandle = False
        if cmd == WILL:
            # 1. 回复不同意MCCP2协商
            if Settings.server["MCCP3"]:
                self.session.write(IAC + DO + MCCP3)
                self.log.debug(f'发送选项协商, 同意MCCP V3协商 IAC DO MCCP3')
            else:
                self.session.write(IAC + DONT + MCCP3)
                self.log.debug(f'发送选项协商, 不同意MCCP V3协商 IAC DONT MCCP3')

        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的MCCP V3协商: IAC {name_command(cmd)} MCCP3")

    def handle_msp(self, cmd):
        """
        处理MUD音频协议的协商 http://www.zuggsoft.com/zmud/msp.htm
        server - IAC WILL MSP
        client - IAC DONT MSP
        当前不接收MUD音频协议(未实现）
        """
        nohandle = False
        if cmd == WILL:
            # 1. 回复不同意MSP协商
            if Settings.server["MSP"]:
                self.session.write(IAC + DO + MSP)
                self.log.debug(f'发送选项协商, 同意MSP协商 IAC DO MSP')
            else:
                self.session.write(IAC + DONT + MSP)
                self.log.debug(f'发送选项协商, 不同意MSP协商 IAC DONT MSP')

        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的MSP协商: IAC {name_command(cmd)} MSP")

    def handle_mxp(self, cmd):
        """
        处理MUD扩展协议的协商 http://www.zuggsoft.com/zmud/mxp.htm
        server - IAC WILL MXP
        client - IAC DONT MXP
        当前不接收MUD扩展协议(未实现）
        """
        nohandle = False
        if cmd == WILL:
            if Settings.server["MXP"]:
                self.session.write(IAC + DO + MXP)
                self.log.debug(f'发送选项协商, 同意MXP协商 IAC DO MXP')
            else:
                self.session.write(IAC + DONT + MXP)
                self.log.debug(f'发送选项协商, 不同意MXP协商 IAC DONT MXP')

        elif cmd == WONT:
            nohandle = True
        elif cmd == DO:
            nohandle = True
        elif cmd == DONT:
            nohandle = True
        else:
            nohandle = True

        if nohandle:
            self.log.warning(f"收到服务器的未处理的MXP协商: IAC {name_command(cmd)} MXP")
