# 高级脚本
## 异步入门

PyMUD的高级脚本使用，必须要掌握基于asyncio库的async/await使用方法。PyMUD使用异步架构构建了整个程序的核心框架。当然，异步在脚本中不是必须的，它只是一种可选的实现方式而已，其他任何客户端都不像PyMUD一样原生完全支持异步操作，这也是PyMUD客户端与其他所有客户端的最核心差异所在。

可以先在以下帖子看看我和HellClient客户端大佬jarlyyn的讨论帖：
https://www.pkuxkx.net/forum/thread-47989-2-1.html

另以下有几篇参考文档可供学习。

python的asyncio库介绍：https://docs.python.org/zh-cn/3.10/library/asyncio.html

Python异步协程（asyncio详解）：https://www.cnblogs.com/Red-Sun/p/16934843.html

由于MUD是基于网咯IO的程序，在程序运行的过程中，大部分时间是空闲在等待服务器数据或客户端输入的。也正是如此，同步模式下的等待都会造成阻塞。

基于async/await的异步可以带来不少的好处，包括：

+ 可以使用同步编程的思维来构建异步程序，这也是其中最大的一个好处。
+ 复用异步Trigger，可以极大的增加代码的可读性。
+ 可以更便捷的实现程序代码的高内聚，低耦合。特别是降低耦合性。

试想以下场景：当我们在北侠中完成一次dazuo之后，正常的服务器回应消息是：你运功完毕，深深吸了口气，站了起来。
那么，我们有可能是想持续打坐修炼内力，也可能是只要执行一次dazuo max指令；也可能时tuna过程中yun regenerate之后的打坐；在持续打坐过程中，也考虑要每隔多少次补满食物饮水；
要在一个服务器回应消息下进行不同种类的处理，在以往同步模式下，可以有很多种实现，例如可以：

- 设置不同变量标识状态，在该触发器下根据变量确定状态再判断后续执行；
- 设置多个完全相同的Trigger，并分属不同的group，根据需要只使能所需的组

上述第1种方式下，多个模块功能的代码都集中在同一个触发器下，一个出错会影响其他，要新增功能则又要对其进行修改；
第2中方式下，同样模式匹配的触发过多，代码会显得臃肿。

如果使用异步，则可以仅使用一个触发器，我们在等待该触发器触发事件后再执行对应代码。此时，触发器的触发结果与执行的内容结果是解耦的，即触发器本身不包含触发器被触发后应该执行的代码，这部分代码由功能实现函数进行完成。这也是异步触发器的由来。

## 异步触发器

PyMUD的Trigger类同时支持同步和异步模式。当使用异步触发器时，有以下两个建议：

1. 不要使用SimpleTrigger。因为其code代码的执行是包含在触发器类的定义中。
1. 不要指定Trigger的onSuccess调用，因为该函数调用是同步的。

Trigger类的triggered方法是一个async定义的协程函数。在不指定code、不指定onSuccess时，其默认的触发函数仅设置Trigger的Event标识，该标识是一个asyncio.Event对象。可以使用下面代码来异步等待触发器的执行。

```
await tri.triggered()
```
以之前打坐的触发示例：
```Python
class Configuration:
    def __init__(self, session):
        self.session = session
        self.initTriggers()
    def initTriggers(self):
        self._triggers = {}
        self._triggers['tri_dazuo'] = Trigger(self.session, r"^[> ]*你运功完毕，深深吸了口气，站了起来。", id = "tri_dazuo")
        self.session.addTriggers(self._triggers)

    async def dazuo_always(self):
        # 此处仅为了说明异步触发器的使用，假设气是无限的，可以无限打坐
        # 每打坐100次，吃干粮，喝酒袋
        time = 0
        while True:                                       # 永久循环
            self.session.writeline("dazuo 10")            # 发送打坐命令
            await self._triggers["tri_dazuo"].triggered() # 等待dazuo触发
            times += 1
            if times > 100:
                self.session.writeline("eat liang")
                self.session.writeline("drink jiudai")
                times = 0

```
从上面的异步示例中可以看出，dazuo/eat/drink代码不是放在Trigger的触发中的，而且该代码逻辑一目了然（因为是以同步思维实现的异步）。当然，上面的代码仅是一个异步触发的使用示例，实际dazuo远比此复杂。

## 命令（Command）
### 命令入门

有了异步Trigger之后，命令就有了实现的基础。命令是什么？可以这么理解，PyMUD的命令，就是将MUD的命令输入、返回响应等封装在一起的一种对象，基于Command可以实现从最基本的MUD命令响应，到最复杂的完整的任务辅助脚本。

要在会话中使用触发器，要做的事是：

+ 构建一个Command的子类(或直接构建一个SimpleCommand类，后面会讲到），实现并覆盖基类的execute方法
+ 创建该Command子类的实例。一个子类应该只构建一个实例。
+ 将该实例通过session.addCommand方法增加到会话的命令清单中

此时，调用该Command，只需在命令行与输入该Command匹配模式匹配的命令即可

### 类型定义与构造函数
Command与Trigger、Alias一样，也是继承自MathObject，也是通过模式匹配进行调用。因此，Command的构造函数与Trigger、Alias相同：

```Python
class Command:
    def __init__(self, session, patterns, *args, **kwargs):
        pass
```

与Alias、Trigger的差异是，Command包含几个新的会经常被使用的方法调用，见下表。

|方法|参数|返回值|含义|
|--|--|--|--|
|create_task|coro, args, name|asyncio.Task|实际是asyncio.create_task的包装，在创建任务的同时，将其加入了session的task清单和本Command的Task清单，可以保证执行，也可以供后续操作使用|
|reset|无|无|复位该任务。复位除了清除标识位之外，还会清除所有未完成的task。在Command的多次调用时，要手动调用reset方法，以防止同一个命令被多次触发。|
|execute|cmd, *args, **kwargs|无|async定义的异步方法，在Command被执行时会自动调用该方法|

### 使用示例
#### Command示例之一：walk命令
先用一个简单的示例来说明Command的应用。在张金敖任务（机关人起源）中，当到达对应节点时，需要使用walk命令行走指定步数然后等待线索。现在想在行走指定步数之后自动使用walk -p停止下来，可以使用以下一个Command类来实现。此处所有逻辑在CmdWalk类override的execute方法中实现，对已经行走步数的技术是通过while循环实现。这种实现方式代码可读性好，其逻辑思维符合正常同步思维模式。

```Python
    class CmdWalk(Command):
        "北侠节点处的Walk指令，控制指定步数"
        _help = """
            定制walk命令使用参考，可接受正常walk命令，也可以使用诸如walk yangzhou 8来控制从节点向yangzhou节点行走，8步之后停下来
            正常指令      含义
            walk xxx:    标准walk指令
            walk -c xxx: 显示路径
            walk -p:     暂停行走
            walk:        继续行走
            特殊指令：
            walk xxx 3:  第二个参数的数字，控制行走的步数，用于张金敖任务
        """
        def __init__(self, session, *args, **kwargs):
            self.tri_room = Trigger(self.session, id = 'tri_room', patterns = r'^[>]*(?:\s)?(\S.+)\s-\s*[★|☆|∞]?$', isRegExp = True)
            self.session.addTrigger(self.tri_room)
            super().__init__(session, "^walk(?:\s(\S+))?(?:\s(\S+))?(?:\s(\S+))?", *args, **kwargs)

        async def execute(self, cmd, *args, **kwargs):
            try:
                m = re.match(self.patterns, cmd)
                if m:
                    para = list()
                    for i in range(1, 4):
                        if m[i] != None:
                            para.append(m[i])

                    # 如果是步数设置，需要人工控制
                    # 例如walk yangzhou 8
                    if (len(para) > 0) and para[-1].isnumeric():
                        cnt = int(para[-1])
                        step = "walk " + " ".join(para[:-1])
                        self.info(f"即将通过walk行走，目的地{para[-2]}，步数{para[-1]}步...", "walk")
                        self.session.writeline("set walk_speed 2")      # 调节速度
                        await asyncio.sleep(1)
                        self.session.writeline(step)

                        # 使用循环控制步数
                        while cnt > 0:                                                                     
                            cnt = cnt - 1
                            await self.tri_room.triggered()                            # 等待房间名被触发cnt次

                        self.session.writeline("walk -p")
                        self.session.writeline("unset walk_speed")      # 恢复速度
                        self.info(f"通过walk行走，目的地{para[-2]}，步数{para[-1]}步完毕", "walk")
                    # 否则直接命令发送
                    else:
                        self.session.writeline(cmd)

            except Exception as e:
                self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                self.error(f"异常追踪为： {traceback.format_exc()}")
```

#### Command示例之二：dzt命令
Command类也可以支持复杂逻辑带不同参数的指令，直至可以实现一个完整的任务辅助机器人。此处再举一个dazuo的例子。在北侠中，打坐是最长使用的命令之一。我们可能需要打坐到双倍内力即停止以进行后续任务，或者专门打坐修炼内力，或者使用dz命令进行打坐以打通任督二脉。在专门修炼内力时，还需要定期补充食物饮水。打坐的时候，也要统筹考虑气不足、精不足等各种可能遇到的情况。以下是一个完整实现的打坐命令，可以使用dzt xxx来执行上述所有操作。详细代码如下：
注：此Command调用了支持jifa/enable命令的CmdEnable，支持hpbrief的命令CmdHpbrief，以及支持食物饮水等生活的命令CmdLifMisc，具体代码未列出，但在阅读dazuoto命令代码时不影响可读性。

```Python
class CmdDazuoto(Command):
    """
    各种打坐的统一命令, 使用方法：
    dzt 0 或 dzt always: 一直打坐
    dzt 1 或 dzt once: 执行一次dazuo max
    dzt 或 dzt max: 持续执行dazuo max，直到内力到达接近2*maxneili后停止
    dzt dz: 使用dz命令一直dz
    dzt stop: 安全终止一直打坐命令
    """
    def __init__(self, session, cmdEnable, cmdHpbrief, cmdLifeMisc, *args, **kwargs):
        super().__init__(session, "^(dzt)(?:\s+(\S+))?$", *args, **kwargs)
        self._cmdEnable = cmdEnable
        self._cmdHpbrief = cmdHpbrief
        self._cmdLifeMisc = cmdLifeMisc
        self._triggers = {}

        self._initTriggers()

        self._force_level = 0
        self._dazuo_point = 10

        self._halted = False

    def _initTriggers(self):
        self._triggers["tri_dz_done"]   = self.tri_dz_done      = Trigger(self.session, r'^[> ]*你运功完毕，深深吸了口气，站了起来。$', id = "tri_dz_done", keepEval = True, group = "dazuoto")
        self._triggers["tri_dz_noqi"]   = self.tri_dz_noqi      = Trigger(self.session, r'^[> ]*你现在的气太少了，无法产生内息运行全身经脉。|^[> ]*你现在气血严重不足，无法满足打坐最小要求。|^[> ]*你现在的气太少了，无法产生内息运行小周天。$', id = "tri_dz_noqi", group = "dazuoto")
        self._triggers["tri_dz_nojing"] = self.tri_dz_nojing    = Trigger(self.session, r'^[> ]*你现在精不够，无法控制内息的流动！$', id = "tri_dz_nojing", group = "dazuoto")
        self._triggers["tri_dz_wait"]   = self.tri_dz_wait      = Trigger(self.session, r'^[> ]*你正在运行内功加速全身气血恢复，无法静下心来搬运真气。$', id = "tri_dz_wait", group = "dazuoto")
        self._triggers["tri_dz_halt"]   = self.tri_dz_halt      = Trigger(self.session, r'^[> ]*你把正在运行的真气强行压回丹田，站了起来。', id = "tri_dz_halt", group = "dazuoto")
        self._triggers["tri_dz_finish"] = self.tri_dz_finish    = Trigger(self.session, r'^[> ]*你现在内力接近圆满状态。', id = "tri_dz_finish", group = "dazuoto")
        self._triggers["tri_dz_dz"]     = self.tri_dz_dz        = Trigger(self.session, r'^[> ]*你将运转于全身经脉间的内息收回丹田，深深吸了口气，站了起来。|^[> ]*你的内力增加了！！', id = "tri_dz_dz", group = "dazuoto")

        self.session.addTriggers(self._triggers)  

    def stop(self):
        self.tri_dz_done.enabled = False
        self._halted = True
        self._always = False

    async def dazuo_to(self, to):
        # 开始打坐
        dazuo_times = 0
        self.tri_dz_done.enabled = True
        if not self._force_level:
            await self._cmdEnable.execute("enable")
            force_info = self.session.getVariable("eff-force", ("none", 0))
            self._force_level = force_info[1]

        self._dazuo_point = (self._force_level - 5) // 10
        if self._dazuo_point < 10:  self._dazuo_point = 10
      
        await self._cmdHpbrief.execute("hpbrief")

        neili = int(self.session.getVariable("neili", 0))
        maxneili = int(self.session.getVariable("maxneili", 0))
        force_info = self.session.getVariable("eff-force", ("none", 0))

        if to == "dz":
            cmd_dazuo = "dz"
            self.tri_dz_dz.enabled = True
            self.info('即将开始进行dz，以实现小周天循环', '打坐')

        elif to == "max":
            cmd_dazuo = "dazuo max"
            need = math.floor(1.90 * maxneili)
            self.info('当前内力：{}，需打坐到：{}，还需{}, 打坐命令{}'.format(neili, need, need - neili, cmd_dazuo), '打坐')
        elif to == "once":
            cmd_dazuo = "dazuo max"
            self.info('将打坐1次 {dazuo max}.', '打坐')
        else:
            cmd_dazuo = f"dazuo {self._dazuo_point}"
            self.info('开始持续打坐, 打坐命令 {}'.format(cmd_dazuo), '打坐')

        while (to == "dz") or (to == "always") or (neili / maxneili < 1.90):
            if self._halted:
                self.info("打坐任务已被手动中止。", '打坐')
                break
  
            waited_tris = []
            waited_tris.append(self.create_task(self.tri_dz_done.triggered()))
            waited_tris.append(self.create_task(self.tri_dz_noqi.triggered()))
            waited_tris.append(self.create_task(self.tri_dz_nojing.triggered()))
            waited_tris.append(self.create_task(self.tri_dz_wait.triggered()))
            waited_tris.append(self.create_task(self.tri_dz_halt.triggered()))
            if to != "dz":
                waited_tris.append(self.create_task(self.tri_dz_finish.triggered()))
            else:
                waited_tris.append(self.create_task(self.tri_dz_dz.triggered()))

            self.session.writeline(cmd_dazuo)

            done, pending = await asyncio.wait(waited_tris, timeout =100, return_when = "FIRST_COMPLETED")
            tasks_done = list(done)
            tasks_pending = list(pending)
            for t in tasks_pending:
                t.cancel()

            if len(tasks_done) == 1:
                task = tasks_done[0]
                _, name, _, _ = task.result()
              
                if name in (self.tri_dz_done.id, self.tri_dz_dz.id):
                    if (to == "always"):
                        dazuo_times += 1
                        if dazuo_times > 100:
                            # 此处，每打坐200次，补满水食物
                            self.info('该吃东西了', '打坐')
                            await self._cmdLifeMisc.execute("feed")
                            dazuo_times = 0

                    elif (to == "dz"):
                        dazuo_times += 1
                        if dazuo_times > 50:
                            # 此处，每打坐50次，补满水食物
                            self.info('该吃东西了', '打坐')
                            await self._cmdLifeMisc.execute("feed")
                            dazuo_times = 0

                    elif (to == "max"):
                        await self._cmdHpbrief.execute("hpbrief")
                        neili = int(self.session.getVariable("neili", 0))

                        if self._force_level >= 161:
                            self.session.writeline("exert recover")
                            await asyncio.sleep(0.2)

                    elif (to == "once"):
                        self.info('打坐1次任务已成功完成.', '打坐')
                        break

                elif name == self.tri_dz_noqi.id:
                    if self._force_level >= 161:
                        await asyncio.sleep(0.1)
                        self.session.writeline("exert recover")
                        await asyncio.sleep(0.1)
                    else:
                        await asyncio.sleep(15)

                elif name == self.tri_dz_nojing.id:
                    await asyncio.sleep(1)
                    self.session.writeline("exert regenerate")
                    await asyncio.sleep(1)

                elif name == self.tri_dz_wait.id:
                    await asyncio.sleep(5)

                elif name == self.tri_dz_halt.id:
                    self.info("打坐已被手动halt中止。", '打坐')
                    break

                elif name == self.tri_dz_finish.id:
                    self.info("内力已最大，将停止打坐。", '打坐')
                    break

            else:
                self.info("命令执行中发生错误，请人工检查", '打坐')
                return self.FAILURE

        self.info('已成功完成', '打坐')
        self.tri_dz_done.enabled = False
        self.tri_dz_dz.enabled = False
        self._onSuccess()
        return self.SUCCESS

    async def execute(self, cmd, *args, **kwargs):
        try:
            self.reset()
            if cmd:
                m = re.match(self.patterns, cmd)
                if m:
                    cmd_type = m[1]
                    param = m[2]
                    self._halted = False

                    if param == "stop":
                        self._halted = True
                        self.info('已被人工终止，即将在本次打坐完成后结束。', '打坐')
                        return self.SUCCESS

                    elif param in ("dz",):
                        return await self.dazuo_to("dz")

                    elif param in ("0", "always"):
                        return await self.dazuo_to("always")

                    elif param in ("1", "once"):
                        return await self.dazuo_to("once")

                    elif not param or param == "max":
                        return await self.dazuo_to("max")
                  

        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")
```

## GMCP触发器（GMCPTrigger）
### GMCP入门
GMCP（Generic Mud Communication Protocol）是一种用于传递非显示字符的MUD通信协议，在标准telnet协议的基础上定义了特定的选项协商和子协商（命令为0xC9）。有关GMCP协议的详细信息参见 https://tintin.mudhalla.net/protocols/gmcp/

北侠是支持GMCP进行数据通信的，详细可以在游戏中使用tune gmcp进行查看可以支持的具体GMCP种类。

PyMUD使用GMCPTrigger类来进行GMCP消息的处理。其使用方法与标准Trigger基本相同，也同样支持同步与异步两种方式。与Trigger的最大差异在于，GMCPTrigger使用name参数作为触发条件，该name必须与MUD服务器发送的GMCP消息的名称完全一致（区分大小写，因此大小写也必须一致）。

要在会话中使用GMCP触发器，要做的两件事是：
+ 构建一个GMCPTrigger类（或其子类）的实例。
+ 将该实例通过session.addGMCPTrigger方法增加到会话的清单中。

### 类型定义与构造函数

GMCPTrigger的构造函数如下：
```Python
class GMCPTrigger(BaseObject):
    """
    支持GMCP收到数据的处理，可以类似于Trigger的使用用法
    GMCP必定以指定name为触发，触发时，其值直接传递给对象本身
    """
    def __init__(self, session, name, *args, **kwargs):
                pass
```
GMCPTrigger也使用了统一的函数语法，必须指定的位置参数包括session（指定会话）、name（为GMCPTrigger服务器发送的消息名称），其余的参数都通过命名参数在kwargs中指定，与Trigger基本相同。具体如下：
+ id: 唯一标识符。不指定时，默认生成session中此类的唯一标识。
+ group: GMCP触发器所属的组名，默认未空。支持使用session.enableGroup来进行整组对象的使能/禁用
+ enabled: 使能状态，默认为True。标识是否使能该触发器。
+ onSuccess: 函数的引用，默认为空。当触发器被触发时自动调用的函数，函数类型应为func(name, line, wildcards)形式。其中Name为GMCP名称，line为收到的值原始文本，wildcards为尝试用json.load解析后的值内容。

### 使用示例

（由于GMCPTrigger在0.16.2版本发生变更，此处待更新）(by newstart, 2023-12-19)


## 状态窗口定制

可以通过脚本定制状态窗口内容。要定制状态窗口的显示内容，将session.status_maker属性赋值为一个返回支持显示结果的函数即可。可以支持标准字符串或者prompt_toolkit所支持的格式化显示内容。
有关prompt_toolkit的格式化字符串显示，可以参见该库的官方帮助页面： https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html

以下是一个实现状态窗口的示例：

```Python
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from settings import Settings

class Configuration:
    def __init__(self, session) -> None:
        session.status_maker = self.status_window

    def status_window(self):

        formatted_list = list()

        (jing, effjing, maxjing, jingli, maxjingli, qi, effqi, maxqi, neili, maxneili) = self.session.getVariables(("jing", "effjing", "maxjing", "jingli", "maxjingli", "qi", "effqi", "maxqi", "neili", "maxneili"))
        ins_loc = self.session.getVariable("ins_loc", None)
        tm_locs = self.session.getVariable("tm_locs", None)
        ins = False
        if isinstance(ins_loc, dict) and (len(ins_loc) >= 1):
            ins = True
            loc = ins_loc

        elif isinstance(tm_locs, list) and (len(tm_locs) == 1):
            ins = True
            loc = tm_locs[0]

        # line 1. char, menpai, deposit, food, water, exp, pot
        formatted_list.append((Settings.styles["title"], "【角色】"))
        formatted_list.append((Settings.styles["value"], "{0}({1})".format(self.session.getVariable('charname'), self.session.getVariable('char'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【门派】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('menpai'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【存款】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('deposit'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【食物】"))
      
        food = int(self.session.getVariable('food', '0'))
        if food < 100:
            style = Settings.styles["red"]
        elif food < 200:
            style = Settings.styles["yellow"]
        elif food < 350:
            style = Settings.styles["green"]
        else:
            style = Settings.styles["skyblue"]

        formatted_list.append((style, "{}".format(food)))
        formatted_list.append(("", " "))

        formatted_list.append((Settings.styles["title"], "【饮水】"))
        water = int(self.session.getVariable('water', '0'))
        if water < 100:
            style = Settings.styles["red"]
        elif water < 200:
            style = Settings.styles["yellow"]
        elif water < 350:
            style = Settings.styles["green"]
        else:
            style = Settings.styles["skyblue"]
        formatted_list.append((style, "{}".format(water)))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【经验】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('exp'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【潜能】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('pot'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【惯导】"))
        if ins:
            formatted_list.append((Settings.styles["skyblue"], "正常"))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【位置】"))
            formatted_list.append((Settings.styles["green"], f"{loc['city']} {loc['name']}({loc['id']})"))
        else:
            formatted_list.append((Settings.styles["red"], "丢失"))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【位置】"))
            formatted_list.append((Settings.styles["value"], f"{self.session.getVariable('%room')}"))

        # a new-line
        formatted_list.append(("", "\n"))

        # line 2. hp
        if jing != None:
            formatted_list.append((Settings.styles["title"], "【精神】"))
            if int(effjing) < int(maxjing):
                style = Settings.styles["red"]
            elif int(jing) < 0.8 * int(effjing):
                style = Settings.styles["yellow"]
            else:
                style = Settings.styles["green"]
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(jing, 100.0*float(jing)/float(maxjing), effjing, 100.0*float(effjing)/float(maxjing),)))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【气血】"))
            if int(effqi) < int(maxqi):
                style = Settings.styles["red"]
            elif int(qi) < 0.8 * int(effqi):
                style = Settings.styles["yellow"]
            else:
                style = Settings.styles["green"]
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(qi, 100.0*float(qi)/float(maxqi), effqi, 100.0*float(effqi)/float(maxqi),)))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【精力】"))
            if int(jingli) < 0.6 * int(maxjingli):
                style = Settings.styles["red"]
            elif int(jingli) < 0.8 * int(maxjingli):
                style = Settings.styles["yellow"]
            elif int(jingli) < 1.2 * int(maxjingli):
                style = Settings.styles["green"] 
            else:
                style = Settings.styles["skyblue"]
            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(jingli, maxjingli, 100.0*float(jingli)/float(maxjingli))))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【内力】"))
            if int(neili) < 0.6 * int(maxneili):
                style = Settings.styles["red"]
            elif int(neili) < 0.8 * int(maxneili):
                style = Settings.styles["yellow"]
            elif int(neili) < 1.2 * int(maxneili):
                style = Settings.styles["green"] 
            else:
                style = Settings.styles["skyblue"]
            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(neili, maxneili, 100.0*float(neili)/float(maxneili))))
            formatted_list.append(("", " "))

            # a new-line
            formatted_list.append(("", "\n"))

        # line 3. GPS info
        def go_direction(dir, mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.session.exec_command(dir)
        if ins:
            formatted_list.append((Settings.styles["title"], "【路径】"))
            # formatted_list.append(("", "  "))
            links = self.mapper.FindRoomLinks(loc['id'])
            for link in links:
                dir = link.path
                dir_cmd = dir
                if dir in Configuration.DIRS_ABBR.keys():
                    dir = Configuration.DIRS_ABBR[dir]
                else:
                    m = re.match(r'(\S+)\((.+)\)', dir)
                    if m:
                        dir_cmd = m[2]

                formatted_list.append((Settings.styles["link"], f"{dir}: {link.city} {link.name}({link.linkto})", functools.partial(go_direction, dir_cmd)))
                formatted_list.append(("", " "))
      
        return formatted_list
```
