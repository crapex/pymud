# PyMUD - Python原生MUD客户端
## 简介

### 北侠WIKI：  https://www.pkuxkx.net/wiki/tools/pymud
### 源代码地址: https://github.com/crapex/pymud
### 帮助文档地址： https://pymud.readthedocs.org
### PyPi项目地址： https://pypi.org/project/pymud
### 使用交流QQ群：554672580


### 北大侠客行Mud (www.pkuxkx.net)，最好的中文Mud游戏！
### PyMUD是我为了更好的玩北大侠客行，特意自行开发的MUD客户端。PyMUD具有以下特点：
+ 原生Python开发，除prompt-toolkit及其依赖库（wcwidth, pygment, pyperclip)外，不需要其他第三方库支持
+ 基于控制台的全屏UI界面设计，支持鼠标操作（Android上支持触摸屏操作）
+ 支持分屏显示，在数据快速滚动的时候，上半屏保持不动，以确保不错过信息
+ 解决了99%情况下，北大侠客行中文对不齐，也就是看不清字符画的问题（因为我没有走遍所有地方，不敢保证100%）
+ 真正的支持多session会话，支持命令或鼠标切换会话
+ 原生支持多种服务器端编码方式，不论是GBK、BIG5、还是UTF-8
+ 支持NWAS、MTTS协商，支持GMCP、MSDP、MSSP协议
+ 一次脚本开发，多平台运行。只要能在该平台上运行python，就可以运行PyMUD客户端
+ 脚本所有语法均采用Python原生语法，因此你只要会用Python，就可以自己写脚本，免去了再去学习lua、熟悉各类APP的使用的难处
+ Python拥有极为强大的文字处理能力，用于处理文本的MUD最为合适
+ Python拥有极为丰富的第三方库，能支持的第三方库，就能在PyMud中支持
+ 我自己还在玩，所以本客户端会持续进行更新:)

### 哪些人适合使用PyMUD
+ 比较熟悉Python语言，会使用Python写代码的 -> PyMUD是纯Python原生开发，不会有其他客户端对Python的支持能比得过PyMUD
+ 虽不太熟悉Python语言，但有想法想学习Python语言的 -> 正好使用PyMUD玩北侠写脚本的过程中学习Python语言
+ 觉得还有些功能现在所有客户端都没有的 -> 你有需求，我来增加，就是这么方便
+ 觉得也想自己整一个定制客户端玩玩的 -> PyMUD完全开源，且除ui框架外全部都是一行一行代码自己写的，可以直接参考PyMUD的设计

## 版本更新信息

### 0.21.0a1 (2025-05-15)
+ 功能新增: 增加了国际化(i18n)支持，支持中文简体和英文。目前完全支持的仅中文简体，英文只完成了界面翻译，运行时的#help帮助内容暂未翻译。
+ 功能新增: 新增了使用元类型及装饰器来管理Pymud对象，包括Alias, Trigger, Timer, GMCPTrigger四种可以使用对应的装饰器，@alias, @trigger, @timer, @gmcp来直接在标记函数上创建。可以参考本版本中的pkuxkx.py文件写法
+ 问题修复: 之前对Alias和Command未进行优先级判断，因此遇到能同时匹配的多个时，不一定优先级高的被触发。现在对Alias和Command进行了优先级判断，优先级高的先触发。
+ 问题修复: 之前的Alias中的keepEval参数和oneShot参数不起作用，已修复。keepEval参数支持多个匹配成功的别名同时生效，oneShot参数支持一个匹配成功的别名生效后，后续的匹配不再生效。

### 0.20.4 (2025-03-30)
+ 功能调整: 为插件功能新增了 PLUGIN_PYMUD_DESTROY 方法，用于在插件被卸载时，进行一些清理工作。
+ 功能调整: 将插件的 PLUGIN_PYMUD_START 方法的调用，从插件加载时刻移动到事件循环启动之后，这样在加载时，可以使用 asyncio.create_task或 asyncio.ensure_future 来执行一些异步操作

### 0.20.3 (2025-03-05)
+ 功能调整: 为适应MacOS下的快捷键，增加Shift+左右箭头同样作为切换会话的快捷键。
+ 功能调整: 会话关闭和APP退出时，偶尔受网络影响导致服务器掉线但本地未检测到时会无法退出。现增加最长10s等待，超时后会中断，强制退出。

### 0.20.2 (2024-11-26)
+ 功能调整: MTTS协商中，将256 Color明确写入协商回复。原先仅包含ANSI 和 TrueColor。推测武庙特殊颜色偶尔不正常与此有关（已测试无关）。
+ 功能调整: 修复了纯文本正则处理，目前理论上支持所有ANSI控制代码的处置，以正确响应纯文本触发器。
+ 功能调整: 修改了#var和#global的显示实现，提高了变量打印排列的整齐度和辨识度，以适应长值变量和复杂变量。
+ 问题修复: 修复了单行颜色代码跨行无法显示问题。现在星宿毒草可以正常辨认颜色了。
+ 功能调整: 调整了info/warning/error的显示处理，默认样式进行了修改。
+ 功能新增: 新增菜单选项：打开/关闭美化，以便于更好的在触发器时复制出正确的内容（以前计算可能不准确）。
+ 功能新增: 状态栏的分隔符可以通过本地设置取消了。在pymud.cfg的client中新增设置，将 status_divider 设置为 false 即可。
+ 功能调整: 在pymud.cfg的client中可以支持将buffer_lines设置为0了，表示不清除缓存。
+ 功能新增: 为状态栏显示函数增加了异常保护，再有status_maker出错的时候，状态栏会显示出错信息。

### 0.20.1 (2024-11-16)
+ 功能调整: 会话中触发器匹配实现进行部分调整，减少循环次数以提高响应速度
+ 功能调整: #test / #show 触发器测试功能调整，现在会对使能的和未使能的触发器均进行匹配测试。其中，#show 命令仅测试，而 #test 命令会导致触发器真正响应。
+ 功能新增: pymud对象新增了一个持续运行的1s的周期定时任务。该任务中会刷新页面显示。可以使用 session.application.addTimerTickCallback 和 session.application.removeTimerTickCallback 来注册和解除定时器回调。

### 0.20.0 (2024-08-25)
+ 功能调整: 将模块主入口函数从__main__.py中移动到main.py中，以使可以在当前目录下，可直接使用pymud，也可使用python -m pymud启动
+ 功能调整: 使用argsparser标准模块来配置命令行，可以使用 pymud -h 查看命令行具体参数及说明
+ 功能新增: 命令行参数增加指定启动目录的功能，参数为 -s, --startup_dir。即可以从任意目录通过指定脚本目录方式启动PyMUD了。
    - 例如， PS C:\> pymud -s d:\prog\pkuxkx 相当于 PS D:\prog\pkuxk> pymud
+ 问题修复: MacOS下 python -m pymud init 创建目录报错的问题。同时，将所有系统上的默认目录均使用 ~/pkuxkx （影响windows）
+ 功能调整: 恢复在__init__.py中增加PyMudApp的导出，可以恢复使用from pymud import PyMudApp了
+ 功能新增: 增加log功能，详见 #log 命令介绍、类参考中的 Logger 类，以及 Session 类的 handle_log 方法
+ 功能新增: 增加 #disconnect, #dis 命令，可以使当前会话从服务器断开。相当于操作菜单 会话->断开连接
+ 功能调整: 在没有session的时候，也可以执行#exit命令
+ 功能新增: #session 命令增加快捷创建会话功能，假如已有快捷菜单 世界->pkuxkx->newstart , 则可以通过 #session pkuxkx.newstart 直接创建该会话，效果等同于点击该菜单
+ 功能调整: 点击菜单创建会话时，若会话已存在，则将该会话切换为当前会话
+ 重大更新: 完全重写了模块的加载、卸载、重新加载方法，修复模块使用中的问题
+ 功能调整: 现在只要将一个类型继承 IConfig 接口，即被识别为配置类型。这种类型在模块加载时会自动创建其实例。当然，名称为Configuration的类型也同样被认为是配置类型，保持向前兼容性。唯一要求是，该类型的构造函数允许仅传递一个session对象。
+ 功能新增: 各类配置类型的卸载现在既可以定义在__unload__方法中，也可以定义在unload方法中。可以根据自己喜好选择一个即可。
+ 功能调整: 各配置类型加载和重新加载前，会自动调用模块的__unload__方法或unload方法（若有）
+ 功能新增: Command基类增加__unload__方法和unload方法，二者在从会话中移除该 Command 时均会自动调用。自定义的Command子类应覆盖这两种方法中的一种方法，并在其中增加清除类型自行创建的 Trigger, Alias 等会话对象。这样，模块卸载时只要移除命令本身，在命令中新建的其他关联对象将被一同移除。
+ 功能新增: 所有PyMUD基础对象类型及其子类型，包括 Alias, Trigger, Timer, Command, GMCPTrigger 及它们的子类型，在创建的时候会自动添加到会话中，无需再进行 addObject 等操作了
+ 问题修复: 修复部分正则表达式书写错误问题
+ 功能新增: Session类新增waitfor函数，用于执行一段代码后立即等待某个触发器的情况，简化原三行代码写法

``` Python
    # 原来为确保await triggered的任务在输入前等待，有时候需要这么写：
    task = self.create_task(self.tri1.triggered())
    await asyncio.sleep(0.05)
    self.session.writeline('dazuo')
    await task

    # 现在可以一句话简写：
    await self.session.waitfor('dazuo', self.create_task(self.tri1.triggered()))
```

+ 功能调整: Session类的addTriggers等方法接受的dict中，会将对象本身id作为会话处理id。当该id与key不一致时，会同时显示警告。
+ 功能新增: Session类新增addObject, addObjects, delObject, delObjects用于操作别名、定时器、触发器、GMCP触发器、命令等对象。
    - 使用示例:

    ```Python
        # 所有对象均可以使用 delObject 直接从会话中移除，会自动根据对象类型推断，无需通过函数名区分
        session.delObject(self.tri1)
        session.delObject(self.ali1)
        session.delObject(self.timer1)

        objs = [
            Trigger(session, xxx, xxx),
            Alias(session, xxx),
            SimpleCommand(session, xxx),
            Timer(session, xxx),
            GMCPTrigger(session, xxx)
        ]

        session.delObjects(objs)    # 可以直接从会话中移除一个数组中的所有对象，会自动判断对象类别
    ```

+ 功能新增: Session类型新增idletime属性，可以获取本会话发呆秒数（float类型）。当会话处于未连接状态时，返回 -1。可以利用定时器，在其中检测 idletime 值，以在机器人出错后处理恢复
+ 功能新增: Session的所有异步命令调用函数增加返回值，现在调用 session.exec_async, exec_command_async 等方法执行的内容若匹配为命令时，会返回最后最后一个 Command 对象的 execute 函数的返回值
    - 例如， result = await self.session.cmds.cmd_runto.execute('rt yz') 与 result = await self.session.exec_async('rt yz') 等价，返回值相同
    - 但     result = await self.session.exec_async('rt yz;dzt')，该返回的result 仅是 dzt 命令的 execute 的返回值。 rt yz 命令返回值被丢弃。
+ 功能新增: 增加临时变量概念，变量名以下划线开头的为临时变量，此类变量不会被保存到 .mud 文件中。
+ 功能新增: 为 BaseObject 基类的 self.session 增加了 Session 类型限定，现在自定义 Command 等时候，使用 self.session 时会有 IntelliSence 函数智能提示了，所有帮助说明已补全
+ 问题修复: 修复 #var 等命令中，若含有中文则等号位置不对齐的问题
+ 功能调整: 在 #tri 等命令中，当对象的 group 为空时，将不再显示 group 属性，减少无用信息

### 0.19.4 (2024-04-20)
+ 功能调整: info 现在 msg 恢复为可接受任何类型参数，不一定是 str
+ 功能调整: #var, #global 指令中，现在可以使用参数扩展了，例如 #var max_qi @qi
+ 功能调整: #var, #global 指令中，现在对字符串会先使用 eval 转换类型，转换失败时使用 str 类型。例如， #var myvar 1 时，myvar类型将为int
+ 功能调整: 变量替代时，会自动实现类型转化，当被替代变量值为非 str 类型时不会再报错
+ 问题修复: 修复之前从后向前选择时，无法复制的问题

### 0.19.3post2 （2024-04-05）
+ 问题修复: 一次发送多个命令时，发送顺序可能不正确的情况
+ 功能增加: 新增一个exec_async函数，是exec函数的异步形式。可以在其他会话中异步执行一段代码
+ 帮助完善: 帮助文档逻辑完善，已完成整个包的内置文档的编写和修改
+ 注: 由于我没弄太明白 readthedocs.io 网站对于读取github源代码的逻辑，目前只能通过新发布正式版本的形式来使 readthedocs.io 网站的文档中的类参考自动更新。
+ 问题修复: 修复退出程序时的小bug

### 0.19.2post2 （2024-03-24）
+ 错误修复：订正部分错别字、错误帮助、错别格式
+ 系统完善：完善帮助体系，按reST格式重写所有有关的docstring
+ 功能调整：session.exec_command / exec_command_async / exec 系列命令调整，现在可以在exec时带变量参数了。例如 session.exec("dazuo @dzpt")，直接调用 dzpt的变量值
+ 功能调整: settings.py中，client字典增加配置reconnect_wait，为自动重连的等待时间，默认15s，可本地覆盖
+ 功能调整: 变通解决了菜单栏右边单击 帮助 菜单会响应问题
+ 错误修复: 修复了会话关闭时插件卸载的代码错误
+ 功能调整: 在会话关闭、程序退出时增加等待，确保收到服务器断开命令之后才关闭和退出
+ 问题修复: 在退出程序时增加了插件卸载调用
+ 实现调整: 在清除task的列表推导过程中去掉了类型判断以减少任务时间占用
+ 其他调整: 从包中删除了拷贝过来作为参考的文件
+ 帮助完善: 帮助文档逻辑完善
+ 实现调整: 改用官方示例的task清除方式，每个任务结束后清除

### 0.19.1 （2024-03-06）
+ 功能新增: 新增鼠标启用禁用功能，以适用于ssh远程情况下的复制功能。F2快捷键可以切换状态。当鼠标禁用时，底部状态栏右侧会显示“鼠标已禁用状态”
+ 功能新增: 新增快捷键F1会直接通过浏览器打开帮助网址 https://pymud.readthedocs.io/
+ 功能新增: 新增默认快捷键F3=#ig, F4=#cls, F11=#close, F12=#exit。此几个快捷键通过配置文件进行配置，可以自行定义或修改。F1、F2为写死的系统功能。
+ 功能调整: 将除#session之外的所有其他#命令实现统一到Session类中实现，这些命令均支持通过Session.exec_command运行
+ 功能调整: python -m pymud init时，创建的pymud.cfg文件增加了keys字典

### 0.19.0 (2024-03-01)
+ 实现调整: session.info/warning/error处理多行时，会给每一行加上同样颜色
+ 功能新增: 初次运行时，可以使用python -m pymud init来初始化环境，自动创建目录并在该目录中建立配置文件和样例脚本文件
+ 实现调整: 将缓冲清除行数的实现调整到SessionBuffer中，减少代码耦合并进一步降低内存占用
+ 功能新增: 新增命令行命令#T+, #T-, 可以使能/禁用指定组，相当于session.enableGroup操作
+ 功能新增: 新增命令行命令#task，可以列出所有系统管理的Task清单，主要用于开发测试
+ 实现调整: 调整系统管理Task的清空和退出机制，减少处理时间占用和内存占用
+ 实现调整: 调整COPY-RAW模式复制，即使仅选中行中的部分内容，也自动识别整行（多行模式也是整个多行）
+ 功能新增: Settings中新增keys字典，用于定义快捷键。可定义快捷键参见prompt_toolkit中Keys的定义。其值为可在session.exec_command运行支持的所有内容。该字典内容可以被pymud.cfg所覆盖。

### 0.18.4post4 (2024-02-23)
+ 功能新增：新增Settings.client["buffer_lines"]，表示保留的缓冲行数（默认5000）。当Session内容缓冲行数达到该值2倍时（10000行），将截取一半（5000行），后一半内容进行保留，前一半丢弃。此功能是为了减少长时挂机的内存消耗和响应时间。
+ 功能修复：解决在显示美化（Settings.client["beautify"]）打开之后，复制部分文字不能正确判断起始终止的问题。
+ 功能调整：修改缓冲行数判断逻辑，加快客户端判断响应速度。
+ 问题调整：修改缓冲截取处理中的小BUG。
+ 功能调整：将帮助窗口中的链接改到帮助网址： https://pymud.readthedocs.org
+ 问题修复：修复了随包提供的pkuxkx.py样例脚本中的几处错误

### 0.18.3 (2024-02-07)
+ 功能调整：原#unload时通过调用__del__来实现卸载的时间不可控，现将模块卸载改为调用unload函数。若需卸载时人工清除有关定时器、触发器等，请在Configuration类下新增unload函数（参数仅self），并在其中进行实现
+ 功能新增：新增会话Variable和全局Global的删除接口。可以通过session.delVariable(name)删除一个变量，可以通过session.delGlobal(name)来删除一个全局Global变量

### 0.18.2 (2024-02-06)
+ 问题修复：修改了定时器实现，以避免出现递归调用超限异常
+ 问题修复：修改了参数替代时的默认值，从None改为字符串"None"，以避免替代时报None异常

### 0.18.1 (2024-02-05)
+ 问题修复：统一处置了task.cancel的参数和create_task的name属性，以适应更低版本的python环境（低至3.7）
+ 实现调整：为解决同步/异步执行问题，在CodeLine和CodeBlock的实现中，会通过调用命令来判断是否使用同步模式（默认为异步）。#gag、#replace为强制同步，#wa为强制异步。当同时存在时，同步失效，异步执行。
+ 实现调整：将%line、%raw的访问传递到触发器内部的执行中，避免同步异步问题。
+ 新增文档：将帮助文档添加到本项目，帮助文档自动同步到 pymud.readthedocs.org （文档内容暂未更新）

### 0.18.0 (2024-01-24) 
+ 问题修复：修复了delTrigger/delAlias等等无法删除对象的问题
+ 功能调整：delTrigger等函数，修改为既可以接受Trigger对象本身，也可以接受其id。其他类似
+ 功能增加：增加了delTriggers（注意，带s）等函数，可以删除多个指定对象。可接受列表、元组等可迭代对象，并且其内容既可以为对象本身，也可以为id。
+ 功能增加：增加了session.reset()功能，可清除会话所有有关脚本信息。也可以在命令行使用#reset调用，另外，#unload不带参数调用时，有同样效果
+ 功能增加：增加了#ignore/#ig参数，类似于zmud的#ignore功能，可以切换全局触发器禁用状态。当全局被禁用时，底部状态栏右侧会显示此状态。（未全局禁用时不显示）
+ 功能调整：移除了会话切换时，状态栏显示的内容
+ 功能调整：会话命令的执行整体进行了实现调整，将参数替代延迟到特定命令执行时刻。（此实现影响面较大，请大家使用中发现BUG时都报告下，我及时修改）
+ 功能调整：代码块现在可以使用{}括起来了。这种情况下，命令和命令可以嵌套了。例如，#3 {#3 get g1b from bo yu;combine gem;pack gem;#wa 3000}，该代码可以执行三次合并g1b宝石
+ 功能新增：增加了#ali,#tri,#ti的三参数使用，可以在命令行直接代码创建SimpleAlias, SimpleTrigger和SimpleTimer。
+ 使用示例：#ali {gp\s(\S+)} {get %1 from corpse}, #tri {^[> ]*【\S+】.+} {#mess %line}, #ti 10 {xixi;haha}
+ 功能新增：新增#session_name cmd命令，可以直接使名为session_name的会话执行cmd命令
+ 功能新增：session类型新增exec方法，使用方法为：session.exec(cmd, session_name)。可以使名为session_name的会话执行cmd命令。当不指定session_name时，在当前会话执行。
+ 功能调整：定时器创建时若不指定id，其自动生成的id前缀由tmr调整为ti
+ 实现调整：将#all、#session_name cmd等命令的实现从pymud.py中移动到了session.py中，这样可以在脚本中使用session.exec_command("#all xixi")。
+ 问题修复：修复了点击菜单"重新加载脚本配置"报错的问题
+ 功能调整：从菜单里点击创建会话时，会自动以登录名为本会话创建id变量
+ 当前已知问题：由于同步/异步执行问题，在SimpleTrigger中，#gag和#replace的执行结果会很奇怪，可能会隐藏和替换掉非触发行。可行的办法为在onSuccess里，调用session.replace进行处理。

### 0.17.4 (2024-01-08)
+ 问题修复：修复了DotDict在dump时出现错误的问题
+ 问题修复：修改了reconnect的实现方式，修复了断开重连时报错的问题
+ 功能增加：为Session增加两个事件属性，分别为event_connected和event_disconnected，接受一个带有session参数的函数，在连接和连接断开时触发。
+ 功能调整：调整了时间显示格式，只显示到秒，不显示毫秒数。

### 0.17.3 (2024-01-02)
+ 问题修复：修复了原有的#repeat功能。命令行#repeat/#rep可以重复输入上一次命令（这个基本没用，主要是我在远程连接时，手机上没有方向键...）
+ 问题修复：修改定时器的实现方式，真正修复了定时器每reload后会新增一个的bug。
+ 功能增加：命令行使用#tri, #ali, #cmd, #ti时，除了接受on/off参数外，增加了del参数，可以删除对应的触发器、别名、命令、定时器。例如：#ti tm_test del 可以删除id为“tm_test”的定时器。
+ 功能调整：调整了#help {cmd}的显示格式，最后一行也增加了换行符，确保后续数据在下一行出现。
+ 功能调整：调整了Timer和SimpleTimer在#timer时的显示格式。
+ 实现调整：调整了Session.clean实现中各对象清理的顺序，将任务清除移到了最后。

### 0.17.2post4 (2023-12-29)
+ 功能修改：会话菜单 "显示/隐藏命令" 和 "打开/关闭自动重连" 操作后，增加在当前会话中提示状态信息。
+ 功能修改：Timer实现进行修改，以确保一个定时器仅创建一个任务。
+ 功能调整：Timer对象在复位Session对象时，也同时复位。目的是确保reload时不重新创建定时器任务。
+ 功能调整：在会话连接时，不再复位Session有关对象信息。该复位活动仅在连接断开时和脚本重新加载时进行。
+ 功能调整：启动PYMUD时，会将控制台标题设置为PYMUD+版本号。
+ 问题修复：修复会话特定脚本模块会被其他会话加载的bug。
+ 问题修复：修复定时器Timer中的bug。

### 0.17.1post1 (2023-12-27)
本版对模块功能进行了整体调整，支持加载/卸载/重载/预加载多个模块，具体内容如下：
+ 当模块中存在名为Configuration类时，以主模块形式加载，即：自动创建该Configuration类的实例（与原脚本相同）
+ 当模块中不存在名为Configuration类时，以子模块形式加载，即：仅加载该模块，但不会创建Configuration的实例
+ #load命令支持同时加载多个模块，模块名以半角逗号（,）隔开即可。此时按给定的名称顺序逐一加载。如：#load mod1,mod2
+ 增加#unload命令，卸载卸载名称模块，同时卸载多个模块时，模块名以半角逗号（,）隔开即可。卸载时，如果该模块有Configuration类，会自动调用其__del__方法
+ 修改reload命令功能，当不带参数时，重新加载所有已加载模块，带参数时，首先尝试重新加载指定名称模块，若模块中不存在该名称模块，则重新加载指定名称的插件。若存在同名模块和插件，则仅重新加载插件（建议不要让插件和模块同名）
+ 增加#modules（简写为#mods）命令，可以列出所有已经加载的模块清单
+ Session类新增load_module方法，可以在脚本中调用以加载给定名称的模块。该方法接受1个参数，可以使用元组/列表形式指定多个模块，也可以使用字符串指定单个模块
+ Session类新增unload_module方法，可以在脚本中调用以卸载给定名称的模块。参数与load_module类似。
+ Session类新增reload_module方法，可以在脚本中调用以重新加载给定名称的模块。当不指定参数时，重新加载所有模块。当指定1个参数时，与load_module和unload_module方法类似
+ 修改Settings.py和本地pymud.cfg文件中sessions块脚本的定义的可接受值。默认加载脚本default_script现可接受字符串和列表以支持多个模块加载。多个模块加载有两种形式，既可以用列表形式指定多个，如["script1","script2"]，也可以用字符串以逗号隔开指定多个，如"script1,script2"
+ 修改Settings.py和本地pymud.cfg文件中sessions块脚本中chars指定的会话菜单参数。当前，菜单后面的列表参数可以支持额外增加第3个对象，其中第3个为该会话特定需要加载的模块。该参数也可以使用逗号分隔或者列表形式。
+ 当创建会话时，自动加载的模块会首先加载default_script中指定的模块名称，然后再加载chars中指定的模块名称。
+ 上述所有修改均向下兼容，不影响原脚本使用。
+ 一个新的修改后的pymud.cfg示例如下
```
{
    "sessions": {
        "pkuxkx" : {
            "host" : "mud.pkuxkx.net",
            "port" : "8081",
            "encoding" : "utf8",
            "autologin" : "{0};{1}",
            "default_script": ["pkuxkx.common", "pkuxkx.commands", "pkuxkx.main"],
            "chars" : {
                "char1": ["yourid1", "yourpassword1"],
                "char2": ["yourid2", "yourpassword2", "pkuxkx.wudang"],
                "char3": ["yourid3", "yourpassword3", "pkuxkx.wudang,pkuxkx.lingwu"],
                "char4": ["yourid4", "yourpassword4", ["pkuxkx.shaolin","pkuxkx.lingwu"]]
            }
        }
    }
 }
```

+ 问题修复：修复enableGroup中定时器处的bug
+ 功能修改：会话连接和重新连接时，取消原定时器停止的设定，目前保留为只清除所有task、复位Command
+ 功能修改：auto_reconnect设定目前对正常/异常断开均有效。若设置为True，当连接断开后15s后自动重连
+ 功能修改：会话菜单下增加“打开/关闭自动重连”子菜单，可以动态切换自动重连是否打开。

### 0.17.0 (2023-12-24)
+ 功能修改：调整修改GMCP数据的wildcards处理方式，恢复为eval，其余不变。（回滚0.16.2版更改）
+ 功能修改：将本地pymud.cfg文件的读取默认编码调整为utf8，以避免加载出现问题
+ 问题修复：sessions.py中，修复系统command与会话command重名的问题（这次才发现）
+ 功能修改：将自动脚本加载调整到session创建初始，而不论是否连接服务器
+ 功能修改：脚本load和reload时，不再清空任何对象，保留内容包括：中止并清空所有task，关闭所有定时器，将所有异步对象复位
+ 功能修改：去掉了左右边框
+ 问题修复：修复了当使用session.addCommand/addTrigger/addAlias等添加对象，而对象是Command/Trigger/Alias等的子类时，由于类型检查失败导致无法成功的问题
+ 功能修改：增加自动重连配置，Settings.client["auto_reconnect"]配置，当为True时，若连接过程中出现异常断开，则10秒后自动重连。该配置默认为False。
+ 功能修改：当连接过程中出现异常时，异常提示中增加异常时刻。
+ 功能修改：#reload指令增加可以重新加载插件功能。例如，#reload chathook会重新加载名为chathook的插件。
+ 功能增加：增加#py指令，可以直接在命令行中写代码并执行。执行的上下文环境为当前环境，即self代表当前session。例如，#py self.writeline("xixi")相当于直接在脚本会话中调用发送xixi指令
+ 功能新增：新增插件（Plugins）功能。将自动读取pymud模块目录的plugins子目录以及当前脚本目录的plugins子目录下的.py文件，若发现遵照插件规范脚本，将自动加载该模块到pymud。可以使用#plugins查看所有被加载的插件，可以直接带参数插件名（如#plugins myplugin）查看插件的详细信息（自动打印插件的__doc__属性，即写在文件最前面的字符串常量）插件文件中必须有以下定义：

|名称|类型|状态|含义|
|-|-|-|-|
|PLUGIN_NAME|str|必须有|插件唯一名称|
|PLUGIN_DESC|dict|必须有|插件描述信息的详情，必要关键字包含VERSION（版本）、AUTHOR（作者）、RELEASE_DATE（发布日期）、DESCRIPTION（简要描述）|
|PLUGIN_PYMUD_START|func(app)|函数定义必须有，函数体可以为空|PYMUD自动读取并加载插件时自动调用的函数， app为PyMudApp（pymud管理类）。该函数仅会在程序运行时，自动加载一次|
|PLUGIN_SESSION_CREATE|func(session)|函数定义必须有，函数体可以为空|在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次|
|PLUGIN_SESSION_DESTROY|func(session)|函数定义必须有，函数体可以为空|在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。|

+ 功能修改：对session自动加载mud文件中变量失败时的异常进行管理，此时将不加载变量，自动继续进行
+ 功能修改：所有匹配类对象的匹配模式patterns支持动态修改，涉及Alias，Trigger，Command。修改方式为直接对其patterns属性赋值。如tri.patterns = aNewPattern
+ 功能修改：连接/断开连接时刻都会在提示中增加时刻信息，而不论是否异常。

### 0.16.2 (2023-12-19)
+ 功能修改：归一化#命令和非#命令处理，使session.exec_command、exec_command_async、exec_command_after均可以处理#命令，例如session.exec_command("#save")。同时，也可以在命令行使用#all发送#命令，如"#all #save"此类
+ 功能修改：调整脚本加载与变量自动加载的顺序。当前为连接自动加载时，首先加载变量，然后再加载脚本。目的是使脚本的变化可以覆盖加载的变量内容，而不是反向覆盖。
+ 功能修改：会话变量保存和加载可以配置是否打开，默认为打开。见Settings.client["var_autosave] 和 Settings.client["var_autoload"]。同理，该配置可以被本地pymud.cfg所覆盖
+ 功能修改：将MatchObject的同步onSuccess和异步await的执行顺序进行调整，以确保一定是同步onSuccess先执行。涉及Trigger、Command等。
+ 功能修改：修改了GMCPTrigger的onSuccess处置和await triggered处置参数，以保持与Trigger同步。当前，onSuccess函数传递3个参数，name，line（GMCP收到的原始str数据）,wildcards（经eval处理的GMCP数据，大概率是dict，偶尔也可能eval失败，返回与line相同值）。await triggered返回与Triggerd的await triggered相同，均为BaseObject.State，包含4个参数的元组，result（永为True)，name（GMCP的id)，line（GMCP原始数据），wildcards（GMCP处理后数据）。其中，后3个参数与onSuccess函数调用时传递参数相同。
+ 功能修改：增加GMCP默认处理。当未使用GMCPTrigger对对应的GMCP消息进行处理时，默认使用[GMCP] name: value的形式输出GMCP收到的消息，以便于个人脚本调试。
+ 功能修改：修改GMCP数据的处理方式从eval修改为json.load，其余不变。

### 0.16.1.post2 (2023-12-12)
+ 问题修复：修复__init__.py中的__all__变量为字符串
+ 功能增加：可以加载自定义Settings。在执行python -m pymud时，会自动从当前目录读取pymud.cfg文件。使用json格式将配置信息写在该文件中即可。支持模块中settings.py里的sessions, client, server, styles, text字段内容。
+ 功能增加：增加全局变量集，可以使用session.setGlobal和session.getGlobal进行访问，以便于跨session通信。也可以使用#global在命令行访问
+ 功能增加：增加变量的持久化，持久化文件保存于当前目录，文件名为session名称.mud，该文件在会话初始化时自动读取，会话断开时自动保存，其他时候使用#save保存。
+ 功能增加：在extras.py中增加DotDict，用于支持字典的.访问方式
+ 功能增加：使用DotDict增加了session有关对象的点访问方式（.）的快捷访问，包括变量vars，全局变量globals，触发器tris，别名alis，命令cmds，定时器timers，gmcp。例如：session.vars.charname，相当于session.getVariable('charname')
+ 功能增加：增加#all命令，可以向当前所有活动会话发送同一消息，例如#all xixi，可以使所有连接的会话都发送emote
+ 功能增加：增加%copy系统变量，当复制后，会将复制内容赋值给%copy变量
+ 功能增加：增加Trigger测试功能，使用#test {msg}在命令行输入后，会如同接收到服务端数据一样引发触发反应，并且会使用[PYMUD TRIGGER TEST]进行信息显示。
+ 功能增加：匹配#test命令和%copy变量使用如下：窗体中复制有关行，然后命令行中输入#test %copy可使用复制的行来测试触发器
+ 功能修改：将原CodeBlock修改为CodeBlock和CodeLine组成，以适应新的#test命令
+ 功能修改：session对命令的输入异步处理函数handle_input_async进行微小调整，以适应#test命令使用
+ 功能修改：退出时未断开session时的提示窗口文字改为红色（原黄色对比度问题，看不清楚）
+ 功能修改：恢复了#help功能，可以在任意会话中使用#help列出所有帮助主题，#help {topic}可以查看主题详情
+ 功能修改：在#reload重新加载脚本时，保留变量数据
+ 问题修复：修复版本显示，更正为0.16.1（原0.16.0）
+ 问题修复：发布日期标志修改为当前时间
+ 功能修改：CodeLine的执行运行处理修改为不删除中间的多余空白
+ 问题修复：修改github项目地址为原pymud地址

### 0.15.8 (2023-12-05)
首次发布到pip。