# settings.py

## 概述

settings.py是PyMUD的设置文件，用于保存与App有关的各类配置、常量等。其实现了一个Settings类，并直接使用类属性设置各变量的值。
其中部分值可以被启动app的当前目录（即执行python -m pymud的目录）下的pymud.cfg文件中的配置所覆盖。当未被覆盖时，使用该文件中定义的默认值。

## 本应用常量定义

settings.py开头的部分为APP常量定义，如无必要，请勿修改其值。此类定义不会被其他设置所覆盖。

结尾的几个变量为APP使用的格式定义，主要指定了session.info、warning、error时的默认样式。

|变量名|含义|备注|
|-|-|-|
|\__appname__|程序名称，也是MTTS定义中的名称类型，在北侠登录时会显示|默认"PYMUD"，请勿修改|
|\__appdesc__|程序描述，该描述将在菜单 帮助->关于 中显示|默认"a MUD client written in Python"，请勿修改|
|\__version__|程序当前版本，该版本将在菜单 帮助->关于 对话框，以及状态栏右下角显示，也会在shell的窗口上显示的title中显示|有时pip上发布的版本带有beta、post标识，但不一定在此处显示。此处主要显示主版本号。请勿修改|
|\__release__|当前版本程序的发布日期|请勿修改|
|\__author__|程序作者，该值将在菜单 帮助->关于 中显示|请勿修改|
|\__email__|程序作者的联系邮箱，该值将在菜单 帮助->关于 中显示|请勿修改|
|\__website__|程序的帮助文档链接，该值将在菜单 帮助->关于 中显示，单击后会自动打开该网站|请勿修改|
|INFO_STYLE|session.info默认样式|ANSI绿色标识, \\x1b[32m|
|WARN_STYLE|session.warning默认样式|ANSI黄色标识, \\x1b[33m|
|ERR_STYLE|session.error默认样式|ANSI绿色标识,\\x1b[31m|
|CLR_STYLE|清除前面样式|ANSI清除格式标识, \\x1b[0m|

## server字典

server字典，包含了对服务器的有关配置。**该配置可以被pymud.cfg文件中的配置所覆盖**，覆盖配置时，可以只给出需要覆盖的具体关键字配置，其余未给定的关键字，将使用该文件中定义的默认值。
若是使用本客户端玩北大侠客行，所有此处的配置均无需覆盖修改，维持默认值即可。

|变量名|默认值|含义|备注|
|-|-|-|-|
|default_encoding|utf-8|服务器默认编码|当创建会话未指定编码时，会默认使用该编码。连接pkuxkx.net时，8081端口默认utf-8|
|encoding_errors|ignore|编解码错误时的默认操作，|ignore即编解码错误时不会抛出异常|
|newline|\n|服务器换行符特性|与服务器有关，在不同的系统中，换行符可能为\r、\n、\r\n，北侠是\n|
|SGA|True|Telnet协商选项SGA，在全双工环境中，不需要GA信号，因此默认同意抑制|参见 rfc858: <https://www.rfc-editor.org/rfc/rfc858.html>|
|ECHO|False|Telnet协商选项ECHO|参见 rfc857: <https://datatracker.ietf.org/doc/html/rfc857.html>|
|GMCP|True|MUD协议，通用MUD通信协议|北侠支持GMCP，具体参见： <https://tintin.mudhalla.net/protocols/gmcp/>|
|MSDP|True|MUD协议，服务器数据协议|北侠数据通过GMCP而非MSDP发送。具体参见： <https://tintin.mudhalla.net/protocols/msdp/>|
|MSSP|True|MUD协议，服务器状态协议|具体参见： <https://tintin.mudhalla.net/protocols/mssp/>|
|MCCP2|False|MUD协议，压缩通信协议V2版|本客户端暂不支持MCCP，请不要修改此设定。协议参见： <https://tintin.mudhalla.net/protocols/mccp/>|
|MCCP3|False|MUD协议，压缩通信协议V3版|本客户端暂不支持MCCP，请不要修改此设定。协议参见： <http://www.zuggsoft.com/zmud/mcp.htm>|
|MSP|False|MUD协议，音频协议|本客户端暂不支持MSP，请不要修改此设定。协议参见： <http://www.zuggsoft.com/zmud/msp.htm>|
|MXP|False|MUD协议，MXP扩展协议|本客户端暂不支持MXP，请不要修改此设定。协议参见： <http://www.zuggsoft.com/zmud/mxp.htm>|

## mnes字典

mnes字典，包含了MUD协议所需的的默认MNES(Mud New-Environment Standard)配置信息，该值均为发送到服务器所需的数据定义。该值不能被覆盖

|变量名|默认值|含义|
|-|-|-|
|CHARSET|server["default_encoding"]|字符集|
|CLIENT_NAME|\__appname__|客户端名称|
|CLIENT_VERSION|\__version__|客户端版本|
|AUTHOR|\__author__|客户端作者|

## client字典

client字典，包含了对PyMUD客户端有关的配置信息，对客户端定制主要修改该字典的内容。该值可以被pymud.cfg文件的定义所覆盖。

|变量名|默认值|含义|备注|
|-|-|-|-|
|buffer_lines|5000|保留的缓冲行数|0.18.4版新增配置。该值表示了会话在清除历史数据时保留的最大行数。|
|naws_width|150|客户端向服务器发送NAWS信息时的列数默认值|在实际使用过程中，程序会先通过库函数获取窗口显示的宽度和高度，无法获取时才使用该配置参数，因此无需修改。|
|naws_height|40|客户端向服务器发送NAWS信息时的行数默认值|在实际使用过程中，程序会先通过库函数获取窗口显示的宽度和高度，无法获取时才使用该配置参数，因此无需修改。|
|newline|\n|客户端换识别的换行符|由于系统不同，有的换行符是\r，有的是\n，有的是\r\n，用于本地写入窗体信息时换行使用。当前\n可以较好工作，因此无需修改|
|tabstop|4|制表符使用空格替换的数量|该参数仅在对远程\t符号进行本地显示时使用，因此无需修改|
|seperator|;|多个命令之间的分隔符|如无特殊必要，建议不要修改|
|appcmdflag|#|区分PyMUD应用命令的标记，#开头的识别为PyMUD命令，非#开头的识别为发送到服务器的命令|如无特殊必要，建议不要修改|
|interval|10|单位ms，指异步多个命令执行时，两条命令之间自动插入的间隔时间|例如一段路径：e;s;s;e;n，在执行时每个命令之间会自动插入10ms间隔|
|auto_connect|True|创建会话后是否自动连接，当为False时，创建会话后不会自动连接到服务器，需要手动或输入命令#connect连接。|特别备注，若在pymud.cfg中覆盖该配置，由于cfg文件是json格式原因，不能使用True来表示，建议改成1，或true（小写）|
|auto_reconnect|False|在已连接的会话由于种种原因导致断开后，是否会自动重新连接的配置|pymud.cfg覆盖时，注意json格式|
|var_autosave|True|是否自动保存会话变量的配置。当为True时，在会话断开时刻会自动将所有本会话的variables变量保存到会话名.mud文件中|注意，断开时刻才会保存。若直接#exit或菜单退出，会导致来不及读到服务器断开的消息，可能变量不会正确保存|
|var_autoload|True|是否自动加载会话变量的配置。当为True时，在会话创建时刻，会自动检查当前目录是否存在会话名.mud文件，若存在，会自动将其中的变量加载到session的variables中|
|remain_last_input|False|在命令行回车后，是否保留上一次输入的内容|此处有bug，当为True时，是可以保持上一次的内容，但回车、重新键入值等操作均会失效，因此暂时不要将该值改为True|
|echo_input|False|是否在session窗口中回显输入的命令|该设置可以临时通过会话菜单进行切换|
|beautify|True|解决中文字符环境下的对齐问题，打开后会自动修改收到的数据中不被正确识别宽度的字符，以解决对齐问题|玩中文MUD游戏时，特别是北大侠客行时，建议此设置打开。|
|status_display|1|状态窗口的显示设置。0不显示状态窗口，1显示在下方，2显示在右方|状态窗口通过session.status_maker属性接口进行显示设置|
|status_width|30|状态窗口显示宽度（字符数）|当status_display为2时生效，此时为右侧显示的状态窗口列数|
|status_height|6|状态窗口显示高度（行数）|当status_display为1时生效，此时为下侧显示状态窗口行数|


## text字典

text字典，包含了可配置的显示内容定义。菜单读取、显示的一些基本内容都可以在此修改。可被pymud.cfg所覆盖。
各菜单对应的操作含义，见 [2.2 菜单操作](../ui.html#id3)
部分未在本文件列出的其他text字典内容暂未被使用。

|变量名|默认值|含义
|-|-|
|welcome|欢迎使用PYMUD客户端 - 北大侠客行，最好的中文MUD游戏|打开PyMUD时，显示在底部状态栏的内容|
|world|世界|世界菜单显示字符|
|new_session|世界菜单下的第一个子菜单显示字符，操作时弹出对话框创建新会话|
|exit|退出|世界菜单下退出菜单显示字符，操作时退出PyMUD应用|
|session|会话|会话菜单显示字符|
|connect|连接/重新连接|会话菜单下子菜单，操作时相当于键入#connect命令|
|disconnect|断开连接|会话菜单下子菜单|
|echoinput|显示/隐藏输入指令|会话菜单下子菜单，临时改变client["echo_input"]的配置状态|
|nosplit|取消分屏|会话菜单下子菜单，在分屏模式下取消分屏，等同于快捷键Ctrl+Z|
|copy|复制(纯文本)|会话菜单下子菜单，以纯文本模式复制选中内容到剪贴板，等同于快捷键Ctrl+C。特别说明，Mac系统下，复制快捷键也是Ctrl+C，系统快捷键Command+C是不生效的|
|copyraw|复制(ANSI)|会话菜单下子菜单，以带ANSI码格式复制行（仅能用于行复制）|
|clearsession|清空会话内容|会话菜单下子菜单|
|closesession|关闭当前会话|会话菜单下子菜单|
|autoreconnect|打开/关闭自动重连|会话菜单下子菜单，临时改变client["auto_reconnect"]的配置状态|
|reloadconfig|重新加载脚本配置|会话菜单下子菜单|
|help|帮助|帮助一级菜单|
|about|关于|帮助菜单下子菜单|
|input_prompt|<prompt><b>命令:</b></prompt>|命令行的提示符内容，必须是可被prompt_toolkit所识别的HTML对象|

## styles字典

styles字典定义了PyMUD显示时的各种格式，该格式定义类似于HTML的css层叠样式表，具体格式要按prompt_toolkit中的定义。
此处具体内容不在详细展开叙述，若在status_maker中需要使用自定义格式，可以在styles增加自己的定义，并在status_maker的接口函数中自行使用这些样式。

## sessions字典

sessions字典是启动PyMUD应用时，自动创建会话菜单的关键，所有相关信息都填在此处。settings.py文件中给定的sessions字典可以作为写pymud.cfg文件的参考，但为解决应用本地化问题，每个人应该在自己运行pymud的目录下创建pymud.cfg文件，并覆盖sessions字典有关内容。

sessions字典支持多个key，其中每一个key对应的value都应该是一个字典，每一个key会在会话菜单下产生一个菜单，value的值则会在key产生的菜单下生成更下一级的子菜单。

每个key对应的value字典下，可以包含的关键字和含义如下：

|关键字|可接受对象类型|含义|备注|
|-|-|-|-|
|host|字符串|此字典角色对应的服务器地址，可接受IP或者域名|如北侠则设置为 mud.pkuxkx.net|
|port|字符串|此字典角色对应的服务器端口号|端口号和编码格式有关，如北侠默认采用UTF-8编码的端口为8081|
|encoding|字符串|服务器编码方式，如GBK、UTF8、BIG5等等|要python识别的编码方式才可以|
|autologin|字符串|当自动登录时，自动输入用户名密码的操作。可接受格式化参数，如{0}，{1}|参数由下面char关键字内容的列表所定义。北侠登录是先输入用户名，然后输入密码，因此可以{0};{1}表示。evennia类MUD的登录是使用connect user pass，因此使用connect {0} {1}表示|
|default_script|字符串|该组角色默认加载的脚本清单|写在此处的脚本会被下面chars所有角色连接时自动加载，可支持多个脚本，以列表['modulea','moduleb']形式隔开即可。所有脚本不要带.py扩展名，其名称应和python代码中import xxx所使用的名称相同|
|chars|字典|在该host下的所有角色，每一个角色会创建一个菜单项|chars字典中的key是菜单项上显示的名称，该key对应的value应该是一个列表，列表可包含三个对象，分别为登录的id、密码、以及仅该角色加载的脚本清单。脚本清单也可以不指定（此时使用2个对象即可，也可以指定多个，使用与default_script相同的列表样式表示|

