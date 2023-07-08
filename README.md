# PyMUD - Python原生MUD客户端
## 重大更新V0.10b
## 1. 简介
### 北大侠客行Mud (www.pkuxkx.net)，最好的中文Mud游戏！
### PyMUD是我为了更好的玩北大侠客行，特意自行开发的MUD客户端。PyMUD具有以下特点：
+ 原生Python开发，除prompt-toolkit及其依赖库（wcwidth, pygment, pyperclip)外，不需要其他第三方库支持
+ 基于控制台的全屏UI界面设计，支持鼠标操作（Android上支持触摸屏操作）
+ 支持分屏显示，在数据快速滚动的时候，上半屏保持不动，以确保不错过信息
+ 解决了99%情况下，北大侠客行中文对不齐，也就是看不清字符画的问题（因为我没有走遍所有地方，不敢保证100%）
+ 真正的支持多session会话（也支持鼠标切换会话）
+ 原生支持多种服务器端编码方式，不论是GBK、BIG5、还是UTF-8
+ 支持NWAS、MTTS协商，支持GMCP、MSDP、MSSP协议
+ 一次脚本开发，多平台运行。只要能在该平台上运行python，就可以运行PyMUD客户端
+ 脚本所有语法均采用Python原生语法，因此你只要会用Python，就可以自己写脚本，免去了再去学习lua、熟悉各类APP的使用的难处
+ Python拥有极为强大的文字处理能力，用于处理文本的MUD最为合适
+ Python拥有极为丰富的第三方库，能支持的第三方库，就能在PyMud中支持
+ 我自己还在玩，所以本客户端会持续进行更新:)
## 2. 基本使用方法
### 打开PyMUD方法
在文件夹下，运行python pymud.py即可
现在支持鼠标和对话框操作了，当然，原有命令仍然基本支持
### 配置PyMUD参数
所有的配置都写在settings.py文件中，里面有注释，可以自行研究
Settings.session下面，可以自己把自己的角色信息加进去，会自动生成菜单，单击后可以自动登录，并且自动加载脚本
### PyMUD命令
PyMUD目前使用纯命令行方式运行（现在支持鼠标、菜单、快捷键操作了），因此使用各类命令来完成，PyMud命令使用#开头，记住以下几个命令就可以了
#### #session
创建会话命令，1个会话就是1个角色的客户端，基本语法为（现在支持鼠标点击对话框创建了）：
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
#### 其他命令，就请各位自行摸索啦
## 3. 更新记录（从这一次开始）
### 2023-06-06
+ 当前版本：V0.05b
+ 修复了多个session时的bug
+ 增加了GMCP在session中的应用
### 2023-07-08
+ 当前版本：V0.10b
+ 重写整个界面
+ 增加了类zmud的操作命令习惯，如#wait, #message之类的，用法相同
+ 原0.05b脚本99%可以兼容，仅需将info\warning\error的调用由原来的app移动到session即可完美兼容

