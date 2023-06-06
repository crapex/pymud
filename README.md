# PyMUD - Python原生MUD客户端
## 1. 简介
### 北大侠客行Mud (www.pkuxkx.net)，最好的中文Mud游戏！
### PyMUD是我为了更好的玩北大侠客行，特意自行开发的MUD客户端。PyMUD具有以下特点：
+ 原生Python开发，除aioconsole库外，不需要任何其他第三方库支持
+ 原生支持多种服务器端编码方式，不论是GBK、BIG5、还是UTF-8
+ 支持NWAS、MTTS协商，支持GMCP、MSDP、MSSP协议
+ 支持多Session会话
+ 一次脚本开发，多平台运行。只要能在该平台上运行python，就可以运行PyMUD客户端
+ 脚本所有语法均采用Python原生语法，因此你只要会用Python，就可以自己写脚本，免去了再去学习lua、熟悉各类APP的使用的难处
+ Python拥有极为强大的文字处理能力，用于处理文本的MUD最为合适
+ Python拥有极为丰富的第三方库，能支持的第三方库，就能在PyMud中支持
+ 我自己还在玩，所以本客户端会持续进行更新:)
## 2. 基本使用方法
### 打开PyMUD方法
在文件夹下，运行python pymud.py即可
### PyMUD命令
PyMUD目前使用纯命令行方式运行，因此使用各类命令来完成，PyMud命令使用#开头，记住以下几个命令就可以了
#### #help
+ 帮助命令，#help可以列举出所有支持的命令，其中绿色打印的命令为缩写；白色的为原生命令
+ 可以使用#help topic来详细打印help中的详细一点的主题，如#help session
#### #session
创建会话命令，1个会话就是1个角色的客户端，基本语法为：
+    #session {name} {host} {port} {encoding}
+    name为会话的名称
+    host，port为服务器的地址和端口
+    encoding为编码方式，不指定时为utf-8
+    例如：#session newstart mud.pkuxkx.net 8081
+    创建一个名为newstart的会话，连接到mud.pkuxkx.net的8081端口，使用UTF8编码方式
+ 当存在多个会话时，可以直接使用#sessionname切换当前会话
+ 例如，#newstart可以直接将newstart会话切换为当前会话
#### #load
+ 加载配置文件，在会话链接成功后，可以使用#load {config}加载配置文件
+ 本版本附送了一个pkuxkx.py的配置文件，请大家自行参考
+ 加载pkuxkx.py配置文件的方法为，在session登录成功之后，使用#load pkuxkx即可
#### #exit
+ 退出PyMUD程序
#### 其他命令，就请各位自行摸索啦
## 3. 更新记录（从这一次开始）
### 2023-06-06
+ 当前版本：V0.05b
+ 修复了多个session时的bug
+ 增加了GMCP在session中的应用

