"""
PyMUD Settings 文件
用于保存与App有关的各类配置、常量等
"""

class Settings:
    "保存PyMUD配置的全局对象"

    # 下列内容为APP的常量定义，请勿修改
    __appname__   = "PYMUD"
    "APP 名称, 默认PYMUD"
    __appdesc__   = "a MUD client written in Python"
    "APP 简要描述"
    __version__   = "0.10b"
    "APP 当前版本"
    __release__   = "2023-07-08"
    "APP 当前版本发布日期"
    __author__    = "北侠玩家 本牛(newstart)"
    "APP 作者"
    __email__     = "crapex@crapex.cc"
    "APP 作者邮箱"
    __website__     = "https://github.com/crapex/pymud"
    "APP 发布网址"

    server = {
        "default_encoding"  : "utf-8",              # 服务器默认编码
        "encoding_errors"   : "ignore",             # 默认编码转换失效时错误处理
        "newline"           : "\n",                 # 服务器端换行符特性
        

        "SGA"               : True,                 # Supress Go Ahead
        "ECHO"              : False,                # Echo
        "GMCP"              : True,                 # Generic Mud Communication Protocol
        "MSDP"              : True,                 # Mud Server Data Protocol
        "MSSP"              : True,                 # Mud Server Status Protocol
        "MCCP2"             : False,                # Mud Compress Communication Protocol V2
        "MCCP3"             : False,                # Mud Compress Communication Protocol V3
        "MSP"               : False,                # Mud 音频协议
        "MXP"               : False,                # Mud 扩展协议
    } 
    "服务器的默认配置信息"

    mnes = {
        "CHARSET"           : server["default_encoding"],
        "CLIENT_NAME"       : __appname__,
        "CLIENT_VERSION"    : __version__,
        "AUTHOR"            : __author__,
    }
    "MUD协议所需的的默认MNES(Mud New-Environment Standard)配置信息"

    client = {
        "naws_width"        : 150,                  # 客户端NAWS宽度
        "naws_height"       : 40,                   # 客户端NAWS高度
        "newline"           : "\n",                 # 客户端换行符
        "tabstop"           : 4,                    # 制表符改成空格
        "interval"          : 10,                   # 在自动执行中，两次命令输入中的间隔时间（ms）
        "auto_connect"      : True,                 # 创建会话后，是否自动连接

        "seperator"         : ";",                  # 多个命令分隔符（默认;）
        "appcmdflag"        : "#",                  # app命令标记（默认#）
        "remain_last_input" : False,
        "echo_input"        : False,
        "beautify"          : True,                 # 专门为解决控制台下PKUXKX字符画对不齐的问题
        "auto_copy"         : False,                # 选中的内容自动复制到剪贴板
        
    }
    "客户端的默认配置信息"

    text = {
        "welcome"           : "欢迎使用PYMUD客户端 - 北大侠客行，最好的中文MUD游戏",
        "world"             : "世界",
        "new_session"       : "创建新会话...",
        "exit"              : "退出",
        "session"           : "会话",
        "connect"           : "连接/重新连接",
        "disconnect"        : "断开连接",
        "nosplit"           : "取消分屏",
        "copy"              : "复制(纯文本)",
        "copyraw"           : "复制(ANSI)",
        "closesession"      : "关闭当前会话",
        "loadconfig"        : "加载脚本配置",
        "reloadconfig"      : "重新加载脚本配置",
        "help"              : "帮助",
        "about"             : "关于",

        "session_changed"   : "已成功切换到会话: {0}",

        "input_prompt"      : '<prompt><b>命令:</b></prompt>',           # HTML格式，输入命令行的提示信息
    }
    "UI中显示的各处文本配置"

    styles = {
        "status"    : "reverse",
        "shadow"    : "bg:#440044",

        "prompt"    : "",

        "selected"  : "bg:#555555 fg:#eeeeee bold",
        "selected.connected"  : "bg:#555555 fg:#33ff33 bold",
        "normal"    : "fg:#aaaaaa",
        "normal.connected"    : "fg:#33aa33",
    }
    "UI中显示的各处style配置"

    sessions = {
        "pkuxkx" : {
            "host" : "mud.pkuxkx.net",
            "port" : "8081",
            "encoding" : "utf8",
            "autologin" : "{0};{1}",                        # 自动登录命令
            "default_script": "pkuxkx",                     # 默认加载的脚本文件（要省略.py扩展名)
            "chars" : {
                "char1"   : ("yourname1", "yourpassword1"),
                "char2"   : ("yourname2", "yourpassword2"),
            }
        },
        # 下面这个evennia时我自己用来调试的，可以删除
        "evennia" : {
            "host" : "192.168.220.128",
            "port" : "4000",
            "encoding" : "utf8",
            "autologin" : "connect {0} {1}",
            "default_script": None,
            "chars" : {
                "evennia"   : ("admin", "admin"),
            }
        }
    }
    "登录的会话有关配置"

    INFO_STYLE     = "\x1b[32m"     #"\x1b[38;2;0;128;255m"
    WARN_STYLE     = "\x1b[33m"
    ERR_STYLE      = "\x1b[31m"
    CLR_STYLE      = "\x1b[0m"

