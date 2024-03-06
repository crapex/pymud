# 3 系统命令

- 系统命令是指在命令行键入的用于操作系统功能的命令，一般以#号开头。
- 除#session命令外，其他命令均可以在代码中通过session.exec系列命令进行调用。
- 在命令中可以使用大括号{}将一段代码括起来，形成代码块。代码块会被作为一条命令处理。

## #action

等同于#trigger，详见 [#trigger](#trigger)

## #ali

为#alias命令的简写，详见[#alias](#alias)

## #alias

#alias命令用于操作别名。#ali是该命令的简写方式。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。
- #ali: 无参数, 打印列出当前会话中所有的别名清单
- #ali my_ali: 一个参数, 列出id为my_ali的Alias对象的详细信息
- #ali my_ali on: 两个参数，启用id为my_ali的Alias对象（enabled = True）
- #ali my_ali off: 两个参数， 禁用id为my_ali的Alias对象（enabled = False）
- #ali my_ali del: 两个参数，删除id为my_ali的Alias对象
- #ali {^gp\s(.+)$} {get %1 from corpse}: 两个参数，新增创建一个Alias对象。使用时，gp gold = get gold from corpse

## #all

#all命令可以同时向所有会话发送统一命令。用法与示例如下。
- #all #cls: 所有会话统一执行#cls命令
- #all quit: 所有会话的角色统一执行quit退出

## #clear

清屏命令，清除当前会话所有缓存显示内容。

## #cls

#clear命令的简写，详见[#clear](#clear)

## #close

关闭当前会话，并将当前会话从pymud的会话列表中移除。

**当前会话处于连接状态时，#close关闭会话会弹出对话框确认是否关闭**

## #command

#command命令用于操作命令。#cmd是该命令的简写方式。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。
- #cmd: 无参数, 打印列出当前会话中所有的命令清单
- #cmd my_cmd: 一个参数, 列出id为my_cmd的Command对象的详细信息
- #cmd my_cmd on: 两个参数，启用id为my_cmd的Command对象（enabled = True）
- #cmd my_cmd off: 两个参数， 禁用id为my_cmd的Command对象（enabled = False）
- #cmd my_cmd del: 两个参数，删除id为my_cmd的Command对象

## #con

#connect命令的简写，详见[#connect](#connect)

## #connect

连接到远程服务器（仅当远程服务器未连接时有效）。命令是通过调用Session.open()来实现连接。

## #cmd

#command命令的简写，详见[#command](#command)

## #error

使用Session.error输出信息, 该信息默认带有红色的标记。

## #exit

退出PyMUD程序。

**当应用中存在还处于连接状态的会话时，#exit退出应用会逐个弹出对话框确认这些会话是否关闭**

## #gag

在主窗口中不显示当前行内容，一般用于触发器中。

**一旦当前行被gag之后，无论如何都不会再显示此行内容，但对应的触发器仍会生效**

## #global

#global命令用于操作全局变量。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。

- #global: 不带参数，列出程序当前所有全局变量清单
- #global hooked: 带1个参数，列出程序当前名称为hooked的全局变量值
- #global hooked 1: 带2个参数，设置名称为hooked的变量值为1

## #gmcp



## #help

显示帮助。当不带参数时, #help会列出所有可用的帮助主题。带参数显示该系统命令的帮助。参数中不需要#号。如

- #help: 打印所有支持的系统命令清单。其中，绿色字体的为简称/别名，白色字体的为原始命令
- #help trigger: 显示#trigger命令的使用帮助

## #ig

命令#ignore的简写，详见[#ignore](#ignore)

## #ignore

切换所有触发器是否被响应的状态。当触发器被全局禁用时，状态栏右下角处会显示“全局禁用”字符提示。

**请注意：在触发器中使用#ig可能导致无法预料的影响**

**使用快捷键F3（可由pymud.cfg配置）相当于输入命令#ignore（0.19.1版新增）**

## #load

为当前session加载指定的模块。当要加载多个模块时，使用空格或英文逗号隔开。
多个模块加载时，按指定名称的先后顺序逐个加载（当有依赖关系时，需岸依赖影响依次加载） 。

- #load myscript: 加载myscript模块，首先会从执行PyMUD应用的当前目录下查找myscript.py文件并进行加载
- #load pymud.pkuxkx: 加载pymud.pkuxkx模块。相当于脚本中的 import pymud.pkuxkx 命令
- #load myscript1 myscript2: 依次加载myscript1和myscript2模块
- #load myscript1,myscript2: 多个脚本之间也可以用逗号分隔

## #mess

#message的简写，详见[#message](#message)

## #message

#mess {msg} 使用弹出窗体显示消息msg。

- #mess 这是一行测试: 使用弹出窗口显示“这是一行测试”
- #mess %line: 使用弹出窗口显示系统变量%line的值

## #mods

#modules命令的简写，详见[#modules](#modules)

## #modules

模块命令，该命令不带参数。可列出本程序当前已加载的所有模块信息. 

## #num

重复执行num次后面的命令。命令也可以代码块进行嵌套使用。如：

- #3 get m1b from nang: 从锦囊中取出3次地*木灵
- #3 {#3 get m1b from nang;#wa 500;combine gem;#wa 4000};xixi: 执行三次合并地*木灵宝石的操作，中间留够延时等待时间。

## #plugins


## #py

## #reload

## #repeat, #rep

## #replace

## #reset

## #save

## #session

## #t+, #t-

## #task

## #test

## #timer, #ti

## #trigger, #tri

## #unload

## #variable, #var

## #wait, #wa

## #warning

## #info

