3 系统命令
=================

    | 系统命令是指在命令行键入的用于操作系统功能的命令，一般以#号开头。
    | 除 `#session`_ 命令外，其他命令均可以在代码中通过 `session.exec` 系列命令进行调用。
    | 在命令中可以使用大括号{}将一段代码括起来，形成代码块。代码块会被作为一条命令处理。

`#action`
----------------

    等同于 `#trigger`_

`#ali`
----------------

    为 `#alias`_ 命令的简写

`#alias`
----------------

    #alias命令用于操作别名。#ali是该命令的简写方式。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。

    - `#ali` : 无参数, 打印列出当前会话中所有的别名清单
    - `#ali my_ali` : 一个参数, 列出id为my_ali的Alias对象的详细信息
    - `#ali my_ali on` : 两个参数，启用id为my_ali的Alias对象（enabled = True）
    - `#ali my_ali off` : 两个参数， 禁用id为my_ali的Alias对象（enabled = False）
    - `#ali my_ali del` : 两个参数，删除id为my_ali的Alias对象
    - `#ali {^gp\s(.+)$} {get %1 from corpse}` : 两个参数，新增创建一个Alias对象。使用时， `gp gold = get gold from corpse`

`#all`
----------------

    #all命令可以同时向所有会话发送统一命令。用法与示例如下。
    - `#all #cls` : 所有会话统一执行#cls命令
    - `#all quit` : 所有会话的角色统一执行quit退出

`#clear`
----------------

    清屏命令，清除当前会话所有缓存显示内容。

`#cls`
----------------

    `#clear`_ 命令的简写

`#close`
----------------

    关闭当前会话，并将当前会话从pymud的会话列表中移除。

    *注：当前会话处于连接状态时，#close关闭会话会弹出对话框确认是否关闭*

`#command`
----------------

    #command命令用于操作命令。#cmd是该命令的简写方式。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。

    - `#cmd` : 无参数, 打印列出当前会话中所有的命令清单
    - `#cmd my_cmd` : 一个参数, 列出id为my_cmd的Command对象的详细信息
    - `#cmd my_cmd on` : 两个参数，启用id为my_cmd的Command对象（enabled = True）
    - `#cmd my_cmd off` : 两个参数， 禁用id为my_cmd的Command对象（enabled = False）
    - `#cmd my_cmd del` : 两个参数，删除id为my_cmd的Command对象

`#con`
----------------

    `#connect`_ 命令的简写

`#connect`
----------------

    连接到远程服务器（仅当远程服务器未连接时有效）。命令是通过调用 `Session.open()` 来实现连接。

`#cmd`
----------------

    `#command`_ 命令的简写

`#error`
----------------

    使用 `Session.error` 输出信息, 该信息默认带有红色的标记。

`#exit`
----------------

    退出PyMUD程序。

    *注：当应用中存在还处于连接状态的会话时，#exit退出应用会逐个弹出对话框确认这些会话是否关闭*

`#gag`
----------------

    在主窗口中不显示当前行内容，一般用于触发器中。

    *注意：一旦当前行被gag之后，无论如何都不会再显示此行内容，但对应的触发器仍会生效*

`#global`
----------------

    #global命令用于操作全局变量。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。

    - `#global` : 不带参数，列出程序当前所有全局变量清单
    - `#global hooked` : 带1个参数，列出程序当前名称为hooked的全局变量值
    - `#global hooked 1` : 带2个参数，设置名称为hooked的变量值为1（字符串格式）

`#gmcp`
----------------

    #gmcp命令用于操作GMCPTrigger。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。

    - `#gmcp` : 无参数, 打印列出当前会话中所有的 `GMCPTrigger` 清单
    - `#cmd GMCP.Move` : 一个参数, 列出id为GMCP.Move的 `GMCPTrigger` 对象的详细信息
    - `#cmd GMCP.Move on` :  两个参数，启用id为GMCP.Move的 `GMCPTrigger` 对象（enabled = True）
    - `#cmd GMCP.Move off` : 两个参数，禁用id为GMCP.Move的 `GMCPTrigger` 对象（enabled = False）
    - `#cmd GMCP.Move del` : 两个参数，删除id为GMCP.Move的 `GMCPTrigger` 对象

`#help`
----------------

    显示帮助。当不带参数时, #help会列出所有可用的帮助主题。带参数显示该系统命令的帮助。参数中不需要#号。用法与示例如下。

    - `#help` : 打印所有支持的系统命令清单。其中，绿色字体的为简称/别名，白色字体的为原始命令
    - `#help trigger` : 显示#trigger命令的使用帮助

`#ig`
----------------

    命令 `#ignore`_ 的简写

`#ignore`
----------------
    切换所有触发器是否被响应的状态。当触发器被全局禁用时，状态栏右下角处会显示“全局禁用”字符提示。

    *注意：在触发器中使用#ig可能导致无法预料的影响*

    *使用快捷键F3（可由pymud.cfg配置）相当于输入命令#ignore（0.19.1版新增）*

`#load`
----------------

    为当前session加载指定的模块。当要加载多个模块时，使用空格或英文逗号隔开。

    多个模块加载时，按指定名称的先后顺序逐个加载（当有依赖关系时，需指定顺序按依赖影响依次加载） 。

    - `#load myscript` : 加载myscript模块，首先会从执行PyMUD应用的当前目录下查找myscript.py文件并进行加载
    - `#load pymud.pkuxkx` : 加载pymud.pkuxkx模块。相当于脚本中的 import pymud.pkuxkx 命令
    - `#load myscript1 myscript2` : 依次加载myscript1和myscript2模块
    - `#load myscript1,myscript2` : 多个脚本之间也可以用逗号分隔

`#mess`
----------------

    `#message`_ 的简写

`#message`
----------------

    使用弹出窗体显示消息。

    - `#mess 这是一行测试` : 使用弹出窗口显示“这是一行测试”
    - `#mess %line` : 使用弹出窗口显示系统变量%line的值

`#mods`
----------------

    `#modules`_ 命令的简写

`#modules`
----------------
    
    模块命令，该命令不带参数。可列出本程序当前已加载的所有模块信息. 

`#num`
----------------

    重复执行num次后面的命令。命令也可以代码块进行嵌套使用。如：

    - `#3 get m1b from nang` : 从锦囊中取出3次地*木灵
    - `#3 {#3 get m1b from nang;#wa 500;combine gem;#wa 4000};xixi` : 执行三次合并地*木灵宝石的操作，中间留够延时等待时间，全部结束后发出xixi。

`#plugins`
----------------

    插件命令。当不带参数时，列出本程序当前已加载的所有插件信息 

    当带参数时，列出指定名称插件的具体信息 。使用示例如下。

    - `#plugins` : 显示当前所有已加载插件
    - `#plugins chathook` : 显示插件chathook的具体信息

`#py`
----------------

    直接执行后面跟着的python语句。执行语句时，环境为当前上下文环境，此时self代表当前会话。

    - `#py self.info("hello")` : 相当于在当前会话中调用 `session.info("hello")`
    - `#py self.enableGroup("group1", False)` : 相当于调用 `session.enableGroup("group1", False)`

`#reload`
----------------

    对已加载脚本进行重新加载。

    不带参数时，为当前session重新加载所有配置模块（不是重新加载插件）。

    带参数时, 若指定名称为模块，则重新加载模块；若指定名称为插件，则重新加载插件。若指定名称既有模块也有插件，则仅重新加载模块（建议不要重名）。

    若要重新加载多个模块，可以在参数中使用空格或英文逗号隔开多个模块名称 。

    - `#reload` : 重新加载所有已加载模块
    - `#reload mymodule` : 重新加载名为mymodule的模块
    - `#reload myplugins` : 重新加载名为myplugins的插件
    - `#reload mymodule myplugins` : 重新加载名为mymodule的模块和名为myplugins的插件。

    **注意事项**

    1. #reload只能重新加载#load方式加载的模块（包括在pymud.cfg中指定的），但不能重新加载import xxx导入的模块。
    2. 若加载的模块脚本中有语法错误，#reload貌似无法生效。此时需要退出PyMUD重新打开
    3. 若加载时依次加载了不同模块，且模块之间存在依赖关系，那么重新加载时，应按原依赖关系顺序逐个重新加载，否则容易找不到依赖或依赖出错

`#replace`
----------------

    修改显示内容，将当前行原本显示内容替换为msg显示。不需要增加换行符。

    *注意：应在触发器的同步处理中中使用。多行触发器时，替代只替代最后一行。*

    - `#replace %raw - 捕获到此行` : 将捕获的当前行信息后面增加标注

`#reset`
----------------
    复位全部脚本。将复位所有的触发器、命令、未完成的任务，并清空所有触发器、命令、别名、变量。

`#save`
----------------

    将当前会话中的变量保存到文件，系统变量（%line, %raw, %copy）除外 

    文件保存在当前目录下，文件名为 {会话名}.mud 。

    *注意：变量保存使用了python的pickle模块，因此所有变量都应是自省的。
    虽然PyMUD的变量支持所有的Python类型，但是仍然建议仅在变量中使用可以序列化的类型。
    另外，namedtuple不建议使用，因为加载后在类型匹配比较时会失败，不认为两个相同定义的namedtuple是同一种类型。*

`#session`
----------------

    会话操作命令。#session命令可以创建会话，直接#sessionname可以切换会话和操作会话命令。使用示例如下。

    - `#session {名称} {宿主机} {端口} {编码}` :  创建一个远程连接会话，使用指定编码格式连接到远程宿主机的指定端口并保存为 {名称} 。其中，编码可以省略，此时使用Settings.server["default_encoding"]的值，默认为utf8
    - `#session newstart mud.pkuxkx.net 8080 GBK` : 使用GBK编码连接到mud.pkuxkx.net的8080端口，并将该会话命名为newstart
    - `#session newstart mud.pkuxkx.net 8081` : 使用UTF8编码连接到mud.pkuxkx.net的8081端口，并将该会话命名为newstart
    - `#newstart` : 将名称为newstart的会话切换为当前会话
    - `#newstart give miui gold` : 使名称为newstart的会话执行give miui gold指令，但不切换到该会话

    *注意: 一个PyMUD应用中，不能存在重名的会话。*

`#t+`
----------------

    组使能命令。使能给定组名的所有对象，包括别名、触发器、命令、定时器、GMCPTrigger等。

    - `#t+ mygroup` : 将组名为mygroup的所有对象使能状态打开。

`#t-`
----------------

    组禁用命令。禁用给定组名的所有对象，包括别名、触发器、命令、定时器、GMCPTrigger等。

    - `#t- mygroup` : 将组名为mygroup的所有对象设置为禁用。

`#task`
----------------

    列出当前由本session管理的所有task清单。主要用于调试。

    使用session.create_task创建的任务默认会加入此清单。使用session.remove_task可以将任务从清单中移除。

    系统会定期/不定期从清单中清除已完成或已取消的任务。

`#test`
----------------

    触发器测试命令。类似于zmud的#show命令。

    - `#test 你深深吸了口气，站了起来。` ： 模拟服务器收到‘你深深吸了口气，站了起来。’时的情况进行触发测试
    - `#test %copy`: 复制一句话，模拟服务器再次收到复制的这句内容时的情况进行触发器测试

    *注意: #test命令测试触发器时，enabled为False的触发器不会响应。*

`#ti`
----------------

    定时器命令 `#timer`_ 的简写形式

`#timer`
----------------

    #timer命令用于操作定时器。#ti是该命令的简写方式。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。

    - `#ti`: 无参数, 打印列出当前会话中所有的定时器清单
    - `#ti my_timer`: 一个参数, 列出id为my_timer的Timer对象的详细信息
    - `#ti my_timer on`: 两个参数，启用id为my_timer的Timer对象（enabled = True）
    - `#ti my_timer off`: 两个参数， 禁用id为my_timer的Timer对象（enabled = False）
    - `#ti my_timer del`: 两个参数，删除id为my_timer的Timer对象
    - `#ti 100 {drink jiudai;#wa 200;eat liang}`: 两个参数，新增创建一个Timer对象。每隔100s，自动执行一次喝酒袋吃干粮。

    *注意： PyMUD支持同时任意多个定时器。*

`#tri`
----------------

    触发器命令 `#trigger`_ 的简写形式

`#trigger`
----------------

    #trigger命令用于操作触发器。#tri是该命令的简写方式。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。

    - `#tri`: 无参数, 打印列出当前会话中所有的触发器清单
    - `#tri my_tri`: 一个参数, 列出id为my_tri的Trigger对象的详细信息
    - `#tri my_tri on`: 两个参数，启用id为my_tri的Trigger对象（enabled = True）
    - `#tri my_tri off`: 两个参数， 禁用id为my_tri的Trigger对象（enabled = False）
    - `#tri my_tri del`: 两个参数，删除id为my_tri的Trigger对象
    - `#tri {^[> ]*段誉脚下一个不稳.+} {get duan}`: 两个参数，新增创建一个Trigger对象。当段誉被打倒的时刻把他背起来。

`#unload`
----------------

    为当前session卸载指定的模块。当要卸载多个模块时，使用空格或英文逗号隔开。

    卸载模块时，将调用模块Configuration类的unload方法，请将模块清理工作代码显式放在此方法中 。

    - `#unload mymodule`: 卸载名为mymodule的模块（并调用其中Configuration类的unload方法【若有】）

`#var`
----------------

    变量操作命令 `#variable`_ 的简写

`#variable`
----------------

    变量操作命令。#var时该命令的简写形式。该命令可以不带参数、带一个参数、两个参数。

    - #var: 不带参数，列出当前会话中所有的变量清单
    - #var myvar: 带1个参数，列出当前会话中名称为myvar的变量值
    - #var myvar 2: 带2个参数，设置名称为myvar的变量值为2（字符串格式）

    *注意： #var设置的变量，其格式都是字符串形式，即#var myvar 2后，myvar = '2'，而不是myvar = 2*

`#wa`
----------------

    延时等待命令 `#wait`_ 的缩写形式

`#wait`
----------------

    异步延时等待指定时间，用于多个命令间的延时等待。

    - `drink jiudai;#wa 200;eat liang`: 喝酒袋之后，等待200ms再执行吃干粮命令

`#warning`
----------------

    使用 `Session.warning` 输出信息, 该信息默认带有黄色的标记。

`#info`
----------------
    使用 `Session.info` 输出信息, 该信息默认带有绿色的标记。
