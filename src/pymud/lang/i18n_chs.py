TRANSLATION = {
    "text" : {
        "welcome"           : "欢迎使用PYMUD客户端 - 北大侠客行，最好的中文MUD游戏",         # the welcome text shown in the statusbar when pymud start
        "world"             : "世界",                                                        # the display text of menu "world"
        "new_session"       : "创建新会话",                                                  # the display text of sub-menu "new_session"
        "show_log"          : "显示记录信息",                                                # the display text of sub-menu "show_log"                          
        "exit"              : "退出",                                                        # the display text of sub-menu "exit"
        "session"           : "会话",                                                        # the display text of menu "session"
        "connect"           : "连接/重新连接",                                               # the display text of sub-menu "connect"
        "disconnect"        : "断开连接",                                                    # the display text of sub-menu "disconnect"
        "beautify"          : "打开/关闭美化显示",                                           # the display text of sub-menu "toggle beautify"
        "echoinput"         : "显示/隐藏输入指令",                                           # the display text of sub-menu "toggle echo input"
        "nosplit"           : "取消分屏",                                                    # the display text of sub-menu "no split"   
        "copy"              : "复制(纯文本)",                                                # the display text of sub-menu "copy (pure text)"
        "copyraw"           : "复制(ANSI)",                                                  # the display text of sub-menu "copy (raw infomation)"                      
        "clearsession"      : "清空会话内容",                                                # the display text of sub-menu "clear session buffer"
        "closesession"      : "关闭当前页面",                                                # the display text of sub-menu "close current session"
        "autoreconnect"     : "打开/关闭自动重连",                                           # the display text of sub-menu "toggle auto reconnect"
        "loadconfig"        : "加载脚本配置",                                                # the display text of sub-menu "load config"
        "reloadconfig"      : "重新加载脚本配置",                                            # the display text of sub-menu "reload config"
        "layout"            : "布局",                                                        # the display text of menu "layout" (not used now)
        "hide"              : "隐藏状态窗口",                                                # the display text of sub-menu "hide status window" (not used now)
        "horizon"           : "下方状态窗口",                                                # the display text of sub-menu "horizon layout" (not used now)
        "vertical"          : "右侧状态窗口",                                                # the display text of sub-menu "vertical layout" (not used now)
        "help"              : "帮助",                                                        # the display text of menu "help"
        "about"             : "关于",                                                        # the display text of menu "about"

        "session_changed"   : "已成功切换到会话: {0}",
        "input_prompt"      : '<prompt><b>命令:</b></prompt>', 

        # text display in dialogs.py
        "basic_dialog"      : "基础对话框",
        "ok"                : "确定",
        "cancel"            : "取消",
        "visit"             : "访问",
        "displayhelp"       : "以查看最新帮助文档",
        "appinfo"           : '<b fg="red">PYMUD {0}</b> - a MUD Client Written in Python',
        "author"            : '作者: <b>{0}</b> <b>E-mail</b>: <u>{1}</u>',
        "sysversion"        : '系统:{} {}   Python版本:{}',
        "sessionname"       : "会话名称",
        "host"              : "服务器地址",
        "port"              : "端口",
        "encoding"          : "编码",
        "nolog"             : "无记录",
        "chooselog"         : "选择查看的记录",

        # text display in modules.py
        "configuration_created"    : "配置对象 {}.{} 创建成功.",
        "configuration_recreated"  : "配置对象 {}.{} 重新创建成功.",
        "configuration_fail"       : "配置对象 {}.{} 创建失败. 错误信息为: {}",
        "entity_module"            : "主配置模块",
        "non_entity_module"        : "从配置模块",
        "load_ok"                  : "加载完成",
        "load_fail"                : "加载失败",
        "unload_ok"                : "卸载完成",
        "reload_ok"                : "重新加载完成",

        # text display in objects.py
        "excpetion_brace_not_matched"   : "错误的代码块，大括号数量不匹配",
        "exception_quote_not_matched"   : "引号的数量不匹配",
        "exception_forced_async"        : "该命令中同时存在强制同步命令和强制异步命令，将使用异步执行，同步命令将失效。",
        "exception_session_type_fail"   : "session 必须是 Session 类型对象的实例!",
        "exception_in_async"            : "异步执行中遇到异常, {}",

    }
}