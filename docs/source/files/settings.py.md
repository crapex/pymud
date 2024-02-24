# settings.py

## 概述

settings.py是PyMUD的设置文件，用于保存与App有关的各类配置、常量等。其实现了一个Settings类，并直接使用类属性设置各变量的值。
其中部分值可以被启动app的当前目录（即执行python -m pymud的目录）下的pymud.cfg文件中的配置所覆盖。当未被覆盖时，使用该文件中定义的默认值。

## 本应用常量定义

settings.py开头的部分为APP常量定义，如无必要，请勿修改其值。此类定义不会被其他设置所覆盖。

|变量名|含义|备注|
|-|-|-|
|\__appname__|程序名称，也是MTTS定义中的名称类型，在北侠登录时会显示|默认"PYMUD"，请勿修改|
|\__appdesc__|程序描述，该描述将在菜单 帮助->关于 中显示|默认"a MUD client written in Python"，请勿修改|
|\__version__|程序当前版本，该版本将在菜单 帮助->关于 对话框，以及状态栏右下角显示，也会在shell的窗口上显示的title中显示|有时pip上发布的版本带有beta、post标识，但不一定在此处显示。此处主要显示主版本号。请勿修改|
|\__release__|当前版本程序的发布日期|请勿修改|
|\__author__|程序作者，该值将在菜单 帮助->关于 中显示|请勿修改|
|\__email__|程序作者的联系邮箱，该值将在菜单 帮助->关于 中显示|请勿修改|
|\__website__|程序的帮助文档链接，该值将在菜单 帮助->关于 中显示，单击后会自动打开该网站|请勿修改|

## server字典

server字典，包含了对服务器的有关配置。***该配置可以被pymud.cfg文件中的配置所覆盖***，覆盖配置时，可以只给出需要覆盖的具体关键字配置，其余未给定的关键字，将使用该文件中定义的默认值。
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
