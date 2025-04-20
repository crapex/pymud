TRANSLATION = {
    "text" : {
        "welcome"           : "欢迎使用PYMUD客户端 - 北大侠客行，最好的中文MUD游戏",         # the welcome text shown in the statusbar when pymud start

        # text in pymud.py
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
        "msg_copy"          : "已复制：{0}",
        "msg_copylines"     : "已复制：行数{0}",
        "msg_no_selection"  : "未选中任何内容...",
        "msg_session_exists" : "错误！已存在一个名为 {0} 的会话，请更换名称再试.",

        "logfile_name"      : "记录文件名",
        "logfile_size"      : "文件大小",
        "logfile_modified"  : "最后修改时间",

        "warning"           : "警告",
        "warning_exit"      : "程序退出警告",
        "session_close_prompt" : "当前会话 {0} 还处于连接状态，确认要关闭？",
        "app_exit_prompt"   : "尚有 {0} 个会话 {1} 还处于连接状态，确认要关闭？",

        "msg_beautify"      : "显示美化已",
        "msg_echoinput"     : "回显输入命令被设置为：",
        "msg_autoreconnect" : "自动重连被设置为：",
        "msg_open"          : "打开",
        "msg_close"         : "关闭",

        "msg_cmd_session_error" : '通过单一参数快速创建会话时，要使用 group.name 形式，如 #session pkuxkx.newstart',
        "msg_cmdline_input" : "命令行键入:",
        "msg_no_session"    : "当前没有正在运行的session.",
        "msg_invalid_plugins"   : "文件: {0} 不是一个合法的插件文件，加载错误，信息为: {1}",

        "status_nobeautify" : "美化已关闭",
        "status_mouseinh"   : "鼠标已禁用",
        "status_ignore"     : "全局禁用",
        "status_notconnect" : "未连接",
        "status_connected"  : "已连接",

        # text in dialogs.py
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

        # text in modules.py
        "configuration_created"    : "配置对象 {0}.{1} 创建成功.",
        "configuration_recreated"  : "配置对象 {0}.{1} 重新创建成功.",
        "configuration_fail"       : "配置对象 {0}.{1} 创建失败. 错误信息为: {}",
        "entity_module"            : "主配置模块",
        "non_entity_module"        : "从配置模块",
        "load_ok"                  : "加载完成",
        "load_fail"                : "加载失败",
        "unload_ok"                : "卸载完成",
        "reload_ok"                : "重新加载完成",

        # text in objects.py
        "excpetion_brace_not_matched"   : "错误的代码块，大括号数量不匹配",
        "exception_quote_not_matched"   : "引号的数量不匹配",
        "exception_forced_async"        : "该命令中同时存在强制同步命令和强制异步命令，将使用异步执行，同步命令将失效。",
        "exception_session_type_fail"   : "session 必须是 Session 类型对象的实例!",
        "exception_in_async"            : "异步执行中遇到异常, {}",


        # text display in session.py
        "msg_var_autoload_success"      : "自动从 {0} 中加载保存变量成功。",
        "msg_var_autoload_fail"         : "自动从 {0} 中加载变量失败，错误消息为： {1}。",
        "msg_auto_script"               : "即将自动加载以下模块: {0}",
        "msg_connection_fail"           : "创建连接过程中发生错误, 错误发生时刻 {0}, 错误信息为 {1}。",
        "msg_auto_reconnect"            : "{0} 秒之后将自动重新连接...",
        "msg_connected"                 : "{0}: 已成功连接到服务器。",
        "msg_disconnected"              : "{0}: 与服务器连接已断开。",
        "msg_duplicate_logname"         : "其它会话中已存在一个名为 {0} 的记录器，将直接返回该记录器。",
        "msg_default_statuswindow"      : "这是一个默认的状态窗口信息\n会话: {0} 连接状态: {1}",
        "msg_mxp_not_support"           : "MXP支持尚未开发，请暂时不要打开MXP支持设置!",
        "msg_no_session"                : "不存在名称为{0}的会话。",
        "msg_num_positive"              : "#{num} {cmd}只能支持正整数!",
        "msg_cmd_not_recognized"        : "未识别的命令: {0}",
        "msg_id_not_consistent"         : "对象 {0} 字典键值 {1} 与其id {2} 不一致，将丢弃键值，以其id添加到会话中...",
        "msg_shall_be_string"           : "{0}必须为字符串类型",
        "msg_shall_be_list_or_tuple"    : "{0}命名应为元组或列表，不接受其他类型",
        "msg_names_and_values"           : "names与values应不为空，且长度相等",
        "msg_not_null"                  : "{0}不能为空",
        "msg_topic_not_found"           : "未找到主题{0}, 请确认输入是否正确。",
        "Day"                           : "天",
        "Hour"                          : "小时",
        "Minute"                        : "分",
        "Second"                        : "秒",
        "msg_connection_duration"       : "已经与服务器连接了: {0}",
        "msg_no_object"                 : "当前会话中不存在名称为 {0} 的{1}。",
        "msg_no_global_object"          : "全局空间中不存在名称为 {0} 的{1}。",
        "msg_object_value_setted"       : "成功设置{0} {1} 值为 {2}。",
        "variable"                      : "变量",
        "globalvar"                     : "全局变量",
        "msg_object_not_exists"         : "当前会话中不存在key为 {0} 的 {1}, 请确认后重试。",
        "msg_object_enabled"            : "对象 {0} 的使能状态已打开。",
        "msg_object_disabled"           : "对象 {0} 的使能状态已关闭。",
        "msg_object_deleted"            : "对象 {0} 已从会话中被删除。",
        "msg_object_param_invalid"      : "#{0}命令的第二个参数仅能接受on/off/del",
        "msg_ignore_on"                 : "所有触发器使能已全局禁用。",
        "msg_ignore_off"                : "不再全局禁用所有触发器使能。",
        "msg_T_plus_incorrect"          : "#T+使能组使用不正确，正确使用示例: #t+ mygroup \n请使用#help ignore进行查询。",
        "msg_T_minus_incorrect"         : "#T-禁用组使用不正确，正确使用示例: #t- mygroup \n请使用#help ignore进行查询。",
        "msg_group_enabled"             : "组 {0} 中的 {1} 个别名，{2} 个触发器，{3} 个命令，{4} 个定时器，{5} 个GMCP触发器均已使能。",
        "msg_group_disabled"            : "组 {0} 中的 {1} 个别名，{2} 个触发器，{3} 个命令，{4} 个定时器，{5} 个GMCP触发器均已禁用。",
        "msg_repeat_invalid"            : "当前会话没有连接或没有键入过指令, repeat无效",
        "msg_window_title"              : "来自会话 {0} 的消息",
        "msg_module_load_fail"          : "模块 {0} 加载失败，异常为 {1}, 类型为 {2}。",
        "msg_exception_traceback"       : "异常追踪为: {0}",
        "msg_module_not_loaded"         : "指定模块名称 {0} 并未加载。",
        "msg_all_module_reloaded"       : "所有配置模块全部重新加载完成。",
        "msg_plugins_reloaded"          : "插件 {0} 重新加载完成。",
        "msg_name_not_found"            : "指定名称 {0} 既未找到模块，也未找到插件，重新加载失败...",
        "msg_no_module"                 : "当前会话并未加载任何模块。",
        "msg_module_list"               : "当前会话已加载 {0} 个模块，包括（按加载顺序排列）: {1}。",
        "msg_module_configurations"     : "模块 {0} 中包含的配置包括: {1}。",
        "msg_submodule_no_config"       : "模块 {0} 为子模块，不包含配置。",
        "msg_module_not_loaded"         : "本会话中不存在指定名称 {0} 的模块，可能是尚未加载到本会话中。",
        "msg_variables_saved"           : "会话变量信息已保存到 {0}。",
        "msg_alias_created"             : "创建Alias {0} 成功: {1}",
        "msg_trigger_created"           : "创建Trigger {0} 成功: {1}",
        "msg_timer_created"             : "创建Timer {0} 成功: {1}",
        
        "msg_tri_triggered"             : "    {0} 正常触发。",
        "msg_tri_wildcards"             : "      捕获：{0}",
        "msg_tri_prevent"               : "      {0}该触发器未开启keepEval, 会阻止后续触发器。{1}",
        "msg_tri_ignore"                : "    {1}{0} 可以触发，但由于优先级与keepEval设定，触发器不会触发。{2}",
        "msg_tri_matched"               : "    {0} 可以匹配触发。",
        "msg_enabled_summary_0"         : "{0}  使能的触发器中，没有可以触发的。",
        "msg_enabled_summary_1"         : "{0}  使能的触发器中，共有 {1} 个可以触发，实际触发 {2} 个，另有 {3} 个由于 keepEval 原因实际不会触发。",
        "msg_enabled_summary_2"         : "{0}  使能的触发器中，共有 {1} 个全部可以被正常触发。",
        "msg_disabled_summary_0"        : "{0}  未使能的触发器中，共有 {1} 个可以匹配。",
        "msg_disabled_summary_1"        : "{0}  未使能触发器，没有可以匹配的。",
        "msg_test_summary_0"            : "  测试内容: {0}",
        "msg_test_summary_1"            : "  测试结果: 没有可以匹配的触发器。",
        "msg_test_summary_2"            : "  测试结果: 有{0}个触发器可以被正常触发，一共有{1}个满足匹配触发要求。",
        "msg_test_title"                : "触发器测试 - {0}",
        "msg_triggered_mode"            : "'响应模式'",
        "msg_matched_mode"              : "'测试模式'",

        "msg_no_plugins"                : "PYMUD当前并未加载任何插件。",
        "msg_plugins_list"              : "PYMUD当前已加载 {0} 个插件，分别为：",
        "msg_plugins_info"              : "{0}, 版本 {1} 作者 {2} 发布日期 {3}",

        "msg_py_exception"              : "Python执行错误：{0}",

        "title_msg"                     : "消息",
        "title_warning"                 : "警告",
        "title_error"                   : "错误",
        "title_info"                    : "提示",

        "msg_log_title"                 : "本会话中的记录器情况:",
        "msg_log_title2"                : "本应用其他会话中的记录器情况:",
        "logger"                        : "记录器",
        "enabled"                       : "开启",
        "disabled"                      : "关闭",
        "logger_status"                 : "当前状态",
        "file_mode"                     : "文件模式",
        "logger_mode"                   : "记录模式",
        "ANSI"                          : "ANSI",
        "plain_text"                    : "纯文本",

        "filemode_new"                  : "新建",
        "filemode_append"               : "追加",
        "filemode_overwrite"            : "覆写",

        "msg_logger_enabled"            : "{0}: 记录器{1}以{2}文件模式以及{3}记录模式开启。",
        "msg_logger_disabled"           : "{0}: 记录器{1}记录已关闭。",
        "msg_logfile_not_exists"        : "指定的记录文件 {0} 不存在。",

    }
}