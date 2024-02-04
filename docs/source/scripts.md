# 脚本

## 知识基础
PyMUD是一个基于控制台UI的MUD客户端，因此不能像zmud/mushclient/mudlet等客户端那样，在窗口中添加触发、别名等内容，所有上述实现都依赖脚本。又因为是Python语言实现，因此也支持Python语言实现。

##### 要能在PyMUD中实现初级脚本功能，首先要掌握以下知识和概念：

- Python基本语法与内置类型；
- 面向对象开发（OOP）的核心概念：封装、继承与多态；
- 函数式编程的基本概念；
- 位置参数与命名参数的基本概念；
- 基于Python的正则表达式；

##### 如要使用PyMUD的高级功能和实现脚本的高级功能，则还需要掌握以下内容：

+ Python asyncio包的熟练使用，包括async/await语法、coroutine、Task概念与运用、Event/Future的使用、事件循环等

##### 如对PyMUD有兴趣，请自行学习上述内容

## 创建脚本

PYMUD使用#load命令加载脚本文件，调用了importlib库的import_module方法。除此之外，为了满足会话的使用要求，加载的主脚本文件中，必须有一个命名为：Configuration的类，构造函数必须接受一个Session类型的参数（传递的是当前会话）。

一个可加载的基本的脚本文件内容参考如下：

```Python
class Configuration:
    def __init__(self, session):
        self.session = session
```

## 内置基本操作

### 内置命令（#开头的）
PyMUD接受在命令行使用命令进行交互。PyMUD内置命令均使用#开头。目前支持以下命令：

|命令|简介|示例|
|--|--|--|
|help|获取帮助|. #help, #help session|
|exit|退出app||
|close|关闭当前会话||
|session|创建新会话|. #session mysession mud.pkuxkx.net 8080 gbk|
|{session_name}|可以直接使用会话名加#，将该会话切换为当前会话|. #mysession|
|{num}|重复num次向mud服务器发送命令|. #3 get b1a from jin nang|
|all|向所有活动的会话发送同样的命令|. #all quit|
|connect, con|连接或重新连接一个断开状态的会话|. #con|
|info|在当前会话中输出一行蓝色的信息|. #info this is an information|
|warning|在当前会话中输出一行黄色的信息||
|error|在当前会话中输出一行红色的信息||
|clear, cls|清除当前会话中的所有文本缓存||
|load|加载制定脚本文件，省略.py扩展名|. #load myscript|
|reload|重新加载脚本文件，为了修改脚本后快速加载||
|alias, ali|别名命令，详见#help alias||
|trigger, tri|触发器命令，详见#help trigger||
|gmcp|gmcp命令，详见#help gmcp||
|command, cmd|命令命令，详见#help command||
|timer, ti|定时器命令，详见#help timer|
|variable, var|变量命令，详见#help variable||
|global|全局变量命令||
|test|测试触发器命令，后面的内容会发送到触发器测试环境，会执行触发|. #test %copy|
|wait, wa|延时命令，用于单行多命令输入，或者SimpleTrigger等其中，延时指定ms数|xixi;#wa 1000;haha|
|message, mess|消息命令，产生一个弹出窗口，显示指定消息|. #mess %line|
|gag|隐藏当前行，用于触发器中|. #gag|
|replace|替换当前行显示，用于触发器中|. #replace %line-[这是增加的内容]|
|repeat, #rep|重复输出上一次的命令||
|save|将当前会话变量保存到文件，即时生效||

### 内置变量（%开头的）
内置变量以%开头，可以在触发器命令中直接使用变量名进行访问，例如“#mess %line”。PyMUD的会话支持以下内置变量：

|变量|含义|
|--|--|
|%line|当前行内容（纯文本）|
|%raw|当前行信息（带有ANSI字符的原始格式）|
|%copy|当复制内容后，复制内容信息|
|%1~%9|别名、触发器的正则捕获内容|

### 内置对象
脚本中所需使用的有关基本对象已经内置在objects.py中，可以直接import使用。基本对象含义如下：

|类型|简介|用途|
|--|--|--|
|Alias|别名的基本类型|可以用来实现基本/复杂别名，必须全代码实现|
|Trigger|触发器的基本类型|可以用来实现基本/复杂触发器，必须全代码实现|
|Timer|定时器的基本类型|可以用来实现基本/复杂定时器，必须全代码实现|
|SimpleAlias|简单别名|可以使用mud命令和脚本而非代码的方法来实现的别名，类似zmud别名|
|SimpleTrigger|简单触发器|可以使用mud命令和脚本而非代码的方法来实现的触发器，类似zmud触发器|
|SimpleTimer|简单定时器|可以使用mud命令和脚本而非代码的方法来实现的定时器，类似zmud定时器|
|Command|命令的基本类型|命令是PyMUD的一大原创特色，在高级脚本中会详细讲到|
|SimpleCommand|简单命令|命令是PyMUD的一大原创特色，在高级脚本中会详细讲到|
|GMCPTrigger|GMCP触发器|专门用于处理MUD服务器GMCP数据，操作方法类似于触发器|
|CodeBlock|可以运行的代码块|用于SimpleTrigger、SimpleAlias、SimpleTimer以及命令行输入处理的模块|

在脚本中要使用上述类型的import：
```Python
from pymud import Alias, Trigger, Timer, SimpleTrigger, SimpleAlias, SimpleTimer, Command, SimpleCommand, GMCPTrigger
```

## Session类型

与MUD服务器的所有交互操作，均由Session类所实现，因此，其与服务器的交互方法是编写脚本所需要的必要内容。Session类的常用方法如下。

|方法名称|参数:类型|返回值|简介|
|-|-|-|-|
|writeline|line:str|None|向服务器中写入一行。如果参数使用;分隔（使用Settings.client.seperator指定），将分行后逐行写入|
|exec_command|line:str|None|执行一段命令，并将数据发送到服务器。本函数和writeline的区别在于，本函数会先进行Command和Alias解析，若不是再使用writeline发送。当line不包含Command和Alias时，等同于writeline|
|exec_command_after|wait:float, line:str|None|等待wait秒后，再执行line所代表的命令|
|exec_command_async|line:str|None|exec_command的异步(async)版本。在每个命令发送前会等待上一个执行完成。|
|getUniqueNumber|无|int|生成一个本会话的唯一序号|
|getUniqueID|prefix|str|生成一个类似{prefix}_{uniqueID}的唯一序号|
|enableGroup|group:str, enabled=True|None|使能/禁用指定组名为group的所有对象，包括Alias、Trigger、Timer、Command、GMCPTrigger|
|addAliases|alis:dict|None|向会话中添加一组Alias对象，对象由字典alis包含|
|addAlias|ali:Alias|None|向会话中添加一个Alias对象|
|delAlias|ali:str|None|删除会话中id为ali的Alias对象|
|addTriggers|tris:dict|None|添加一组Trigger对象|
|addTrigger|tri:Trigger|None|添加一个Trigger|
|delTrigger|tri:str|None|删除id为tri的Trigger|
|addCommands|cmds:dict|None|添加一组Command对象|
|addCommand|cmd:Command|None|添加一个Command|
|delCommand|cmd:str|None|删除id为cmd的Command|
|addTimers|tis:dict|None|添加一组Timer对象|
|addTimer|ti:Timer|None|添加一个Timer|
|delTimer|ti:str|None|删除id为ti的Timer|
|addGMCPs|gmcp:dict|None|添加一组GMCPTrigger对象|
|addGMCP|gmcp:GMCPTrigger|None|添加一个GMCPTrigger|
|delGMCP|gmcp:str|None|删除id为gmcp的GMCPTrigger|
|setVariable|name:str,value|None|设置（或新增）一个变量，变量名为name，值为value|
|setVariables|names,value|None|设置（或新增）一组变量，变量名为names(元组或列表），值为values（元组或列表）|
|updateVariables|kvdict:dict|None|更新一组变量，与setVariables的区别为，接受的参数为dict键值对|
|getVariable|name:str,default=None|任意类型|获取名为name的变量值，当name不存在时，返回default|
|getVariables|names|tuple|获取names列表中所有的变量值。对每一个，当name不存在时，获取内容为None值|
|setGlobal|name:str,value|None|设置（或新增）一个全局变量，变量名为name，值为value（全局变量是可以跨session进行访问的变量）|
|getGlobal|name:str,default=None|任意类型|获取名为name的全局变量值，当name不存在时，返回default|
|replace|newstr:str|None|在触发器中使用，将会话中当前行的显示内容修改为newstr。使用replace可以在触发器时将额外信息增加到当前行中|
|info|msg,title,style|None|向Session窗体中输出一串信息，会以[title] msg的形式输出，title默认PYMUD INFO，颜色(style指定)默认绿色|
|warning|msg,title,style|None|向Session窗体中输出一串信息，会以[title] msg的形式输出，title默认PYMUD WARNING，颜色(style指定)默认黄色|
|error|msg,title,style|None|向Session窗体中输出一串信息，会以[title] msg的形式输出，title默认PYMUD ERROR，颜色(style指定)默认红色|

Session类型有部分直接访问的属性，如下表

|属性名称|简介|
|-|-|
|connected|bool类型，指示会话连接状态|
|duration|float类型，返回服务器端连接的时间，以秒为单位|
|status_maker|引用类型，指向状态栏显示的函数或字符串|
|vars|variable变量的点访问器。即可以使用session.vars.neili直接访问名为neili的变量。下同|
|globals|全局变量的点访问器|
|tris|触发器的点访问器|
|alis|别名的点访问器|
|cmds|命令的点访问器|
|timers|定时器的点访问器|
|gmcp|gmcp的点访问器|


## 触发器（基础版）
### 触发器入门
进入MUD游戏，第一个要使用的必然是触发器（Trigger）。PyMUD支持多种特性的触发器，并内置实现了Trigger和SimpleTrigger两个基础类。
要在会话中使用触发器，要做的两件事是：
+ 构建一个Trigger类（或其子类）的实例。SimpleTrigger是Trigger的子类，你也可以构建自己定义的子类。
+ 将该实例通过session.addTrigger方法增加到会话的触发器清单中。

### 类型定义与构造函数
Trigger是触发器的基础类，继承自MatchObject类（可以不用理会）。SimpleTrigger继承自Trigger，可以直接用命令而非函数来实现触发器触发时的操作。
Trigger与SimpleTrigger的构造函数分别如下：
```Python
class Trigger:
    def __init__(self, session, patterns, *args, **kwargs):
        pass
class SimpleTrigger:
    def __init__(self, session, patterns, code, *args, **kwargs):
        pass
```
为了使用统一的函数语法，除重要的参数session（指定会话）、patterns（指定匹配模式）、code（SimpleTrigger）的执行代码之外，其余所有触发器的参数都通过命名参数在kwargs中指定。触发器支持和使用的命名参数、默认值及其含义如下：
+ id: 唯一标识符。不指定时，默认生成session中此类的唯一标识。
+ group: 触发器所属的组名，默认未空。支持使用session.enableGroup来进行整组对象的使能/禁用
+ priority: 优先级，默认100。在触发时会按优先级排序执行，越小优先级越高。
+ enabled: 使能状态，默认为True。标识是否使能该触发器。
+ oneShot: 单次触发，默认为False。当该值为True时，触发器被触发一次之后，会自动从会话中移除。
+ onSuccess: 函数的引用，默认为空。当触发器被触发时自动调用的函数，函数类型应为func(id, line, wildcards)形式。
+ ignoreCase: 忽略大小写，默认为False。触发器匹配时是否忽略大小写。
+ isRegExp：是否正则表达式，默认为True。即指定的触发匹配模式patterns是否为正则表达式。
+ keepEval: 匹配成功后持续进行后续匹配，默认为False。当有两个满足相同匹配模式的触发器时，要设置该属性为True，否则第一次匹配成功后，该行不会进行后续触发器匹配（意味着只有最高优先级的触发器会被匹配）
+ raw: 原始代码匹配，默认为False。当为True时，对MUD服务器的数据原始代码（含VT100控制指令）进行匹配。在进行颜色匹配的时候使用。

构造函数中的其他参数含义如下：
+ session: 指定的会话对象，必须有
+ patterns: 匹配模式。当为单行匹配时，传递字符串（正则表达式或原始数据）。当需要进行多行匹配时，使用元组或者列表传递多个匹配行即可。
+ code: SimpleTrigger独有，即匹配成功后，执行的代码串。该代码串类似于zmud的应用，可以用mud命令、别名以分号（；）隔开，也可以在命令之中插入PyMUD支持的#指令，如#wait（缩写为#wa）

### 使用示例
#### 简单触发器
例如，在新手任务（平一指配药）任务中，要在要到任务后，自动n一步，并在延时500ms后进行配药;配药完成后自动s，并提交配好的药，并再次接下一个任务，则可以如此建立触发器：
```Python
tri1 = SimpleTrigger(self.session, "^[> ]*你向平一指打听有关『工作』的消息。", "n;#wa 500;peiyao")
self.session.addTrigger(tri1)
tri2 = SimpleTrigger(self.session, "^[> ]*不知过了多久，你终于把药配完。", "s;#wa 500;give ping yao;#wa 500;ask ping about 工作")
self.session.addTrigger(tri2)
```
#### 标准触发器
例如，当收到有关fullme或者其他图片任务的链接信息时，自动调用浏览器打开该网址，则可以建立一个标准触发器（示例中同时指定了触发器id）：
```Python
def initTriggers(self):
    tri = Trigger(self.session, id = 'tri_webpage', patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', onSuccess = self.ontri_webpage)
    self.session.addTrigger(tri)
def ontri_webpage(self, name, line, wildcards):
    webbrowser.open(line)        # 在开头之前已经 import webbrowser
```
#### 多行触发器
例如，在set hpbrief long的情况下，hpbrief显示三行内容。此时进行多行触发（3行），并将触发中获取的参数值保存到variable变量中：
```Python
HP_KEYS = (
        "exp", "pot", "maxneili", "neili", "maxjingli", "jingli",
        "maxqi", "effqi", "qi", "maxjing", "effjing", "jing",
        "zhenqi", "zhenyuan", "food", "water", "fighting", "busy"
        )
def initTriggers(self):
    tri = Trigger(self.session, id = "tri_hpbrief", patterns = (r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$',), onSuccess = self.ontri_hpbrief)
    self.session.addTrigger(tri)
def ontri_hpbrief(self, name, line, wildcards):
    self.session.setVariables(self.HP_KEYS, wildcards)
```
#### ANSI触发器
如果要捕获文字中的颜色、闪烁等特性，则可以使用触发器的raw属性。例如，在长安爵位任务中，要同时判断路人身上的衣服和鞋子的颜色和类型时，可以使用如下触发：
```Python
def initTriggers(self):
    tri = Trigger(self.session, patterns = r"^.+□(?:\x1b\[[\d;]+m)?(身|脚)\S+一[双|个|件|把](?:\x1b\[([\d;]+)m)?([^\x1b\(\)]+)(?:\x1b\[[\d;]+m)?\(.+\)", onSuccess = self.judgewear, raw = True)
    self.session.addTrigger(tri)
def judgewear(self, name, line, wildcards):
    buwei = wildcards[0]        # 身体部位，身/脚
    color = wildcards[1]        # 颜色，30,31,34,35为深色，32,33,36,37为浅色
    wear  = wildcards[2]        # 着装是布衣/丝绸衣服、凉鞋/靴子等等
    # 对捕获结果的进一步判断，此处省略
```


## 别名
### 别名入门
当要简化一些输入的MUD命令，或者代入一些参数时，会使用到别名（Alias）。PyMUD支持多种特性的别名，并内置实现了Alias和SimpleAlias两个基础类。
要在会话中使用别名，要做的两件事是：
+ 构建一个Alias类（或其子类）的实例。SimpleAlias是Alias的子类，你也可以构建自己定义的子类。
+ 将该实例通过session.addAlias方法增加到会话的别名清单中。

### 类型定义与构造函数
Alias是别名的基础类，与触发器一样，也是继承自MatchObject类。事实上，在PyMUD设计时，我认为别名和触发器是完全相同的东西，只不过一个对输入的命令进行匹配处理（别名），而另一个对MUD服务器端的消息进行匹配处理（触发器），因而在代码上，这两个类除了名称不同之外，差异也是极小的。主要差异是在于触发器增加了异步触发功能（高级内容中会讲到）。SimpleAlias继承自Alias，可以直接用命令而非函数来实现别名触发时的操作。
Alias与SimpleAlias的构造函数与Trigger和SimpleTrigger完全相同，此处不再列举：
别名支持的命名参数、默认值及其含义与上一节触发器的完全相同，但以下命名参数在别名中虽然支持，但不使用：
+ oneShot: 别名不存在只用一次，因此设置这个无实际意义；
+ raw: 别名不存在ANSI版本和纯文本版本，因此设置这个也无实际意义。

### 使用示例
#### 简单别名
例如，要将从扬州中央广场到信阳小广场的路径设置为别名，可以如此建立别名：
```Python
ali = SimpleAlias(self.session, "yz_xy", "#4 w;nw;#5 w")
self.session.addAlias(ali)
```

#### 带有参数的别名
例如，每次慕容信件任务完成后都要从尸体中取出信件，另外还有可能有黄金、白银，每次都输入get letter fromc corpse等等命令太长，想进行缩写，则可以如此建立别名：
```Python
ali = SimpleAlias(self.session, "^gp\s(.+)$", "get %1 from corpse")
self.session.addAlias(ali)
```
建立别名之后，可以使用gp silver, gp gold, gp letter代替 get silver/gold/letter from corpse

#### 标准别名
例如，要将gan che to 方向建立成别名，并且在方向既可以使用缩写（e代表east之类），也可以使用全称，则可以建立一个标准别名：
```Python
DIRS_ABBR = {
        "e": "east",
        "w": "west",
        "s": "south",
        "n": "north",
        "u": "up",
        "d": "down",
        "se": "southeast",
        "sw": "southwest",
        "ne": "northeast",
        "nw": "northwest",
        "eu": "eastup",
        "wu": "westup",
        "su": "southup",
        "nu": "northup",
        "ed": "eastdown",
        "wd": "westdown",
        "sd": "southdown",
        "nd": "northdown",
    }

def initAliases(self):
    ali = Alias(self.session, "^gc\s(.+)$", onSuccess = self.ganche)
    self.addAlias(ali)

def ganche(self, name, line, wildcards):
    dir = wildcards[0]
    if dir in self.DIRS_ABBR.keys():
        cmd = "gan che to {}".format(self.DIRS_ABBR[dir]
    else:
        cmd = f"gan che to {dir}"
    self.session.writeline(cmd)
```


## 定时器
### 定时器入门
要周期性的执行某段代码，会使用到定时器（Timer）。PyMUD支持多种特性的定时器，并内置实现了Timer和SimpleTimer两个基础类。
要在会话中使用定时器，要做的两件事是：
+ 构建一个Timer类（或其子类）的实例。SimpleTimer是Timer的子类，你也可以构建自己定义的子类。
+ 将该实例通过session.addTimer方法增加到会话的定时器清单中。

### 类型定义与构造函数
Timer与SimpleTimer的构造函数分别如下：
```Python
class Timer:
    def __init__(self, session, *args, **kwargs):
        pass
class SimpleTimer:
    def __init__(self, session, code, *args, **kwargs):
        pass
```
定时器支持以下几个命名参数，其默认值及其含义为：
+ id: 唯一标识符。不指定时，默认生成session中此类的唯一标识。
+ group: 触发器所属的组名，默认未空。支持使用session.enableGroup来进行整组对象的使能/禁用
+ enabled: 使能状态，默认为True。标识是否使能该定时器。
+ timeout: 超时时间，即定时器延时多久后执行操作，默认为10s
+ oneShot: 单次执行，默认为False。当为True时，定时器仅响应一次，之后自动停止。否则，每隔timeout时间均会执行。
+ onSuccess: 函数的引用，默认为空。当定时器超时时自动调用的函数，函数类型应为func(id)形式。
+ code: SimpleTimer中的code，与之前的SimpleAlias、SimpleTrigger相同用法。

### 定时器示例
#### 简单定时器
例如，在莫高窟冥想时，每隔5s发送一次mingxiang命令，则可以这样实现定时器
```Python
tm = SimpleTimer(self.session, timeout = 5, id = "tm_mingxiang", code = "mingxiang")
self.session.addTimers(tm)
```
#### 标准定时器
上述定时器的标准实现版本如下
```Python
def initTimers(self):
    tm = Timer(self.session, timeout = 5, id = "tm_mingxiang", onSuccess = self.timer_mingxiang)
    self.session.addTimers(tm)
def timer_mingxiang(self, id, *args, **kwargs):
    self.session.writeline("mingxiang")
```

## 变量
### 变量简介
由于PyMUD需要完整的Python脚本进行实现，在许多情况下，如zmud/mushclient里面的变量是可以完全使用Python自己的变量来进行替代的。但PyMUD保留了变量这一功能，我设计脚本的思路为，只有单个模块使用的变量，多使用Python变量实现，而需要跨模块调用的变量，才使用PyMUD变量进行存储。
事实上，PyMUD变量本质上仍是Python的变量，只不过赋值给了对应的session会话所有。也基于此特点，PyMUD的变量支持任意值类型，不是一定为简单类型，也可以为列表、字典，也可以为复杂的对象类型。
在触发器、别名的使用过程中，存在以下系统变量：
%line：即触发的行本身。对于多行触发，%line会返回多行
%1 ~ %9: 触发器、别名使用时的正则匹配的匹配组
### 变量使用
变量可以直接在SimpleTrigger、SimpleAlias、SimpleTimer中调用。系统变量直接调用（如%line），自定义变量前面加@调用。
例如，在收到“xxx告诉你：”之类的消息时，使用#message弹窗显示可以：
```Python
tri = SimpleTrigger(self.session, r".+告诉你:.+", "#message %line")
self.session.addTrigger(tri)
```
例如，通过触发器捕获到身上的钱的数量，可以将数量与类型联合为字典，再添加到赋值给1个变量
```Python
money = {'cash': 0, 'gold': 1, 'silver': 50, 'coin': 77}
self.session.setVariable("money", money)
# 在使用时，则这样获取
money = self.session.getVariable("money")
```
也可以将上述变量分别存在不同的名称中，并一同读写：
```Python
money_key   = ('cash', 'gold', 'silver', 'coin')
money_count = (0, 1, 50, 77)
self.session.setVariables(money_key, money_count)
# 在使用时，则这样获取
silver = self.session.getVariable("silver")
```
