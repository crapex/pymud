6 脚本
===============

6.1 所需知识基础
------------------

    在PyMUD中，一切皆脚本。所有操作均可以通过脚本实现，且绝大多数情况下，仅能通过脚本实现。
    由于PyMUD是一个基于控制台UI的MUD客户端，因此不能像 zmud/mushclient/mudlet 等客户端那样，在窗口中添加触发、别名等内容。
    而PyMUD是基于Python语言的原生实现，因此其实现脚本也是使用 Python 语言。
    PyMUD使用异步架构构建了整个程序的核心框架。当然，异步在脚本中不是必须的，它只是一种可选的实现方式而已。
    其他客户端都不像PyMUD一样原生完全支持async/await语法下的异步操作，这也是本客户端与其他所有客户端的最核心差异所在。

    要能在PyMUD中实现基本的脚本功能，需要掌握以下知识和概念：

    - Python基本语法与内置类型
    - 面向对象开发（OOP）的核心概念：封装、继承与多态。 百度百科: `面向对象程序设计 <https://baike.baidu.com/item/%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E7%A8%8B%E5%BA%8F%E8%AE%BE%E8%AE%A1/24792>`_
    - 函数式编程的基本概念。百度百科: `函数式编程 <https://baike.baidu.com/item/%E5%87%BD%E6%95%B0%E5%BC%8F%E7%BC%96%E7%A8%8B>`_
    - 位置参数与关键字参数的基本概念
    - 基于Python的正则表达式。 Python文档: `正则表达式操作 <https://docs.python.org/zh-cn/3.10/library/re.html>`_

    要在PyMUD中使用脚本的高级功能，则还需要掌握以下内容：

    - asyncio 包的熟练使用，包括 async/await 语法、coroutine、Task概念与运用、Event/Future 的使用、事件循环等。 Python文档: `asyncio - 异步I/O <https://docs.python.org/zh-cn/3.10/library/asyncio.html>`_ 


6.2 一些概念与定义
------------------------

    PyMUD 支持的脚本，可以分布在模块、插件中。而模块按其特点，又可以分为主配置模块和子配置模块。
    模块的概念与 Python 中模块的概念基本相同。为有效区分PyMUD中的概念，在称谓前增加限定语标识。

    Python 模块:
        Python 模块(Module)，是一个 Python 文件，以 .py 结尾，包含了 Python 对象定义和Python语句。
        模块能够有逻辑地组织你的 Python 代码段。
        把相关的代码分配到一个模块里能让你的代码更好用，更易懂。
        模块能定义函数，类和变量，模块里也能包含可执行的代码。

    PyMUD模块:
        PyMUD模块本身是一个标准的Python模块。为了保证PyMUD应用的正常加载，模块文件应当放在当前目录下，可以以包的形式进行组织。PyMUD支持同时加载任意多个模块。

        根据PyMUD模块文件中是否包含名为 Configuration 的类型，将PyMUD模块区分为主配置模块和子配置模块两类。

        将PyMUD模块放在当前目录下之后，可以在命令行通过 ``#load xxx`` 指令加载名为xxx的模块(xxx为模块不包括扩展名.py的文件名，下同)，也可以将名称放在本地 pymud.cfg 中的 sessions_ 字典中以进行自动加载。

        当模块加载完毕之后，可以通过 ``session.modules['xxx']['module']`` 来访问该模块，可以通过 ``session.modules['xxx']['config']`` 来访问该模块中的 Configuration 类型实例。

        可以在命令行使用 `#mods`_ 命令列出本会话中已加载的所有模块清单。

        特别说明:
            区分PyMUD模块类型事实上并无绝对意义上的差异。也可以不通过 #load 加载子模块，而在主模块中直接通过 import xxx 加载该模块文件。

            但由于PyMUD实现限制， 在脚本修改之后， #reload 仅可以重新加载由 PyMUD 进行管理的模块，也即是通过 #load 命令 或者 Session.load_module 所加载的模块。
            因此可以使用PyMUD子配置模块来替代 import xxx 的使用。
            对子模块的#reload，需要在引用该子模块的主模块也执行#reload之后才生效。经测试，目前看来，模块的#reload是生效的

    PyMUD子配置模块:
        PyMUD模块中不包含名为 Configuration 的类型的PyMUD模块即属于PyMUD子配置模块。
        加载子配置模块时，相当于在 Python 中调用 import xxx 指令。
        加载子配置模块后， ``session.modules['xxx']['config']`` 为 None

    PyMUD主配置模块:    
        模块中包含一个名为 Configuration 的类型的PyMUD模块。该类型构造函数接受一个 `pymud.Session`_ 对象作为唯一参数。
        这种模块在加载时，除了如子配置模块执行相同操作之外，还将自动创建一个 Configuration 类型的实例。

        以下是一个基本的主配置模块的示例：

        .. code:: Python
            
            # filename: mymainmodule.py
            from pymud import Session

            class Configuration:
                def __init__(self, session: Session):
                    self.session = session

                # 注：0.20.0以后，__unload__或unload函数均可生效
                def __unload__(self):
                    pass
    
    PyMUD插件:
        PyMUD插件本身也是一个标准的 Python模块。插件应放在 pymud包目录的plugins子目录下，或者当前脚本目录的plugins子目录下，在PyMUD启动时自动加载。

        插件有相应的插件规范，详细参见 `插件`_

    模块的unload与reload:
        下面给出了测试生效的子模块与主模块的reload与unload的一个示例

        .. code:: Python

            # filename: submodule.py
            # 一个子模块的示例，定义了一个自定义的触发器

            from pymud import Trigger, Session

            class MyTestTrigger(Trigger):
                def __init__(self, session, *args, **kwargs):
                    super().__init__(session, r'^[>\s]*你嘻嘻地笑了起来.+', onSuccess = self._ontri)

                def _ontri(self, name, line, wildcards):
                    self.session.exec('haha')

        .. code:: Python

            # filename: mainmodule.py
            # 一个主模块的示例，调用了子模块中的触发器

            from pymud import SimpleAlias, SimpleTimer, Session
            from submodule import MyTestTrigger

            class Configuration:
                def __init__(self, session: Session):
                    self.session = session

                self.objs = [
                    SimpleAlias(session, r'^gta$', 'get all;xixi'),
                    SimpleTimer(session, 'xixi', timeout = 10),
                    TestTrigger(session)
                ]

                self.session.addObjects(self.objs)
                
            def __unload__(self):
                self.session.delObjects(self.objs)

        以下是测试步骤：
            模块的加载与卸载:

            - 在游戏中，通过 ``#load mainmodule`` 加载该主模块之后，别名、定时器、自定义触发器均生效。此时，子模块是通过import而非load_module加载到当前会话的
            - 然后通过 ``#unload mainmodule`` 卸载该主模块之后，别名、定时器、自定义触发器全部被清除。

            模块的重新加载

            - 在游戏中，通过 ``#load mainmodule`` 加载该主模块之后，别名、定时器、自定义触发器均生效。此时，子模块是通过import而非load_module加载到当前会话的
            - 此时，修改 submodule.py 的内容，例如将触发后的命令 haha 改为 hehe，保存文件
            - 然后在游戏中，先使用 ``#load submodule`` 加载该子模块，然后 ``#reload submodule`` 重新加载该子模块，再 ``#reload mainmodule`` 重新加载主模块，此时，子模块的修改会生效。


6.3 变量
------------------------

6.3.1 变量概览
^^^^^^^^^^^^^^^^^^^^^

    从被管理的情况以及访问的范围划分，PyMUD可以使用的变量可以包括三大类：

        - Python 变量
            即在脚本中，自己定义的 Python 变量对象。此类对象不受 PyMUD 应用管理，当应用退出、会话关闭、脚本重新加载后，变量的结果由脚本代码自行设定，其定义、使用请按照 Python 的语法要求执行。
            Python 变量请参考 Python 语言有关文档，此处不再详细展开。

        - 单会话访问的变量
            即 Session 所属的 Variable 对象。此类对象包括了系统提供的部分变量，以及自行定义的变量。自行定义的变量在会话的所有脚本中都可以直接访问使用，并且可以通过 pymud.cfg 设置（默认已设置），在应用退出、会话关闭、脚本重新加载时，进行了持久化存储操作。
            Variable 对象，通过会话对象的属性字典实现和保存。PyMUD 规定，字典的键key作为变量名，必须为 str 类型，值 value 为变量的值，可以为任意 Python 类型，但仍建议采用可以持久化的类型。
        
        - 跨会话访问的变量
             即 PyMUD 所属的 Global 对象。此类对象与 Variable 对象区别为，这些对象可以在不同的会话之间进行访问，共享同一个变量对象。
             Global 对象通过 PyMudApp 对象的属性字典实现和保存。该对象不会被持久化，字典的键key作为变量名，必须为 str 类型。值可以为任何 Python 支持的类型。

    在设计自己脚本的时候，要根据上述不同类型变量的特点，选择合适的类型。
    个人建议，默认首选 Variable 类型，若有跨会话访问需求，请选择 Global 类型。对于某些函数或方法中的临时变量，再使用 Python 变量。

6.3.2 单会话访问的变量 (Variable) 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    PyMUD 应用系统本身提供了部分 Variable 变量，这些变量均用 % 开头。其中，部分为单个函数中使用的局部变量，部分为可全局访问使用的变量。 系统提供的 Variable 变量包括：

    - :%1 ~ %9: 在触发器、别名的同步响应函数中，使用正则匹配的匹配组。 类似于 mushclient 与 zmud 中的 %1 ~ 9%。
    - :%line: 在触发器、别名的同步响应函数中，匹配的行本身（经ANSI转义处置后的纯文本）。对于多行触发器， %line会返回多行。
    - :%raw: 在触发器的同步响应函数中，匹配的行本身的原始代码（未经ANSI转义处置）。
    - :%copy: 使用PyMUD复制功能（非系统复制功能）复制到当前剪贴板中的内容。

    变量可以使用 Session 对象提供的方法以及 Session 对象提供的快捷点访问器在脚本中进行操作。也可以使用 `#var <syscommand.html#var>`_ 命令来进行操作。
    
    创建变量/修改变量值的方法:
    
    - 可以使用 `setVariable <references.html#pymud.Session.setVariable>`_, `setVariables <references.html#pymud.Session.setVariables>`_, `vars <references.html#pymud.Session.vars>`_ 来创建变量（当变量不存在时）或修改变量值（当变量存在时）。
    - 可以使用 `getVariable <references.html#pymud.Session.getVariable>`_, `getVariables <references.html#pymud.Session.getVariables>`_, `vars <references.html#pymud.Session.vars>`_ 来读取变量值。
    - 可以使用 `delVariable <references.html#pymud.Session.delVariable>`_ 来移除一个变量。
    
    具体使用示例如下：

    .. code:: Python

        from pymud import Session, Trigger, SimpleAlias, SimpleTrigger
        
        class Configuration:
            def __init__(self, session: Session):
                self.session = session
                self._opVariables()
                
            def _opVariables(self):
                # 系统变量 %line 的使用，直接在 SimpleTrigger 中使用
                tri = SimpleTrigger(self.session, r".+告诉你:.+", "#message %line")
                self.session.addTrigger(tri)

                # Variable 使用，值类型为 dict 的 Variable
                money = {'cash': 0, 'gold': 1, 'silver': 50, 'coin': 77}
                # 将 money 变量值设置为上述字典
                self.session.setVariable("money", money)
                # 在使用时，则这样获取
                money = self.session.getVariable("money")

                # Variable 使用，同时设置多个变量，要求键，值数量相同
                money_key   = ('cash', 'gold', 'silver', 'coin')
                money_count = (0, 1, 50, 77)
                # 以下代码将同时设置4个变量，分别为 cash = 0, gold = 1, silver = 50, coin = 77
                self.session.setVariables(money_key, money_count)
                # 在使用时，则这样获取单个变量
                silver = self.session.getVariable("silver")
                # 也可以同时获取多个变量，并自动使用元组解包
                cash, gold = self.session.getVariables(("cash", "gold"))

                # 可以直接使用快捷点访问器.vars来访问变量，读写均可
                self.session.vars.gold = 2
                mygold = self.session.vars.gold

                # 当某个变量不再使用，也不希望保留在变量列表中时，可以用 delVariable 删除
                self.session.delVariable('gold')


6.3.3 跨会话访问的变量 (Global) 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    Global变量用在需要跨多个会话应用相互访问的情况，其使用与 Variable 变量基本相同。一点差异在于，#save 命令存储会话状态时，Global 变量状态不会被保存：

    Global变量可以使用 Session 对象提供的方法以及 Session 对象提供的快捷点访问器在脚本中进行操作。也可以使用 `#global <syscommand.html#global>`_ 命令来进行操作。
    
    创建Global变量/修改Global变量值，可以使用Session类对象的以下方法:
    
    - 可以使用 `session.setGlobal <references.html#pymud.Session.setGlobal>`_, `session.globals <references.html#pymud.Session.globals>`_ 来创建Global变量（当Global变量不存在时）或修改Global变量值（当Global变量存在时）。
    - 可以使用 `session.getGlobal <references.html#pymud.Session.getGlobal>`_, `session.globals <references.html#pymud.Session.globals>`_ 来读取Global变量值。
    - 可以使用 `session.delGlobal <references.html#pymud.Session.delGlobal>`_ 来移除一个变量。
    
    也可以使用PyMudApp对象的以下方法:
    
    - 可以使用 `app.set_globals <references.html#pymud.PyMudApp.set_globals>`_, `app.globals <references.html#pymud.PyMudApp.globals>`_ 来创建Global变量, 用法与 session.setGlobal 和 session.globals 相同。
    - 可以使用 `app.get_globals <references.html#pymud.PyMudApp.get_globals>`_, `app.globals <references.html#pymud.PyMudApp.globals>`_ 来读取Global变量值, 用法与 session.getGlobal 和 session.globals 相同。
    - 可以使用 `app.del_globals <references.html#pymud.PyMudApp.del_globals>`_, 来移除Global变量, 用法与 session.delGlobal 相同。

    具体使用示例如下：

    .. code:: Python

        # 文件名: chathook.py (非完整代码，仅用于展示 global 的应用)
        # 定义一个chathook插件，并供全局各Session使用

        from functools import partial
        from pymud import PyMudApp, Session, Trigger, SimpleAlias, SimpleTrigger
        
        class ChatHook:
            def __init__(self, app: PyMudApp) -> None:
                self.app = app
                # 使用 PyMudApp.set_globals 设置一个布尔型全局变量 hooked，指示是否已与chat服务器连接
                self.app.set_globals("hooked", False)
                # 使用 快捷点访问器 设置一个ChatHook类型的全局变量 hook，用于各会话中使用该对象并调用对象函数
                app.globals.hook = self
                self.site = None

            def start_webhook(self):
                try:
                    # 使用 PyMudApp.get_globals 获取全局变量 hooked判断是否已与服务器连接
                    hooked = self.app.get_globals("hooked")
                    if not hooked:
                        asyncio.ensure_future(self.start_webserver())
                    else:
                        if self.app.current_session:
                            self.app.current_session.info("WEBHOOK已监听!", "CHATHOOK")

                except Exception as e:
                    self.app.set_status(f"插件CHATHOOK在启动WEBHOOK时发生错误，错误信息：{e}")

            def stop_webhook(self):
                try:
                    hooked = self.app.get_globals("hooked")
                    if hooked:
                        asyncio.ensure_future(self.stop_webserver())

            async def start_webserver(self):
                try:
                    self.webapp = web.Application()
                    self.webapp.add_routes([web.post('/', self.handle_post), web.get('/', self.handle_get)])
                    self.runner = web.AppRunner(self.webapp)
                    await self.runner.setup()
                    self.site = web.TCPSite(self.runner, '0.0.0.0', 8000)
                    await self.site.start()
                    
                    # 使用 PyMudApp.set_globals 函数设置 hooked 变量的值
                    self.app.set_globals("hooked", True)
                    if self.app.current_session:
                        self.app.current_session.info("WEBHOOK已在端口8000进行监听.", "CHATHOOK")
                    self.app.set_status("插件CHATHOOK的WEBHOOK已在端口8000进行监听.")
                except OSError as e:
                    # 备注：WinError错误代码为10048，98应该为LINUX系统
                    if (e.errno == 98) or (e.errno == 10048):
                        self.app.set_status("端口8000使用中，插件CHATHOOK的WEBHOOK监听服务启动失败.")
                    else:
                        self.app.set_status(f"插件CHATHOOK的WEBHOOK监听服务启动出现OSError错误，错误代码: {e.errno}")

                except Exception as e2:
                    self.app.set_status(f"插件CHATHOOK的WEBHOOK监听服务启动出现错误: {e2}")

            async def stop_webserver(self):
                try:
                    if isinstance(self.site, web.TCPSite):
                        await self.site.stop()

                        # 使用 PyMudApp.set_globals 函数设置 hooked 变量的值
                        self.app.set_globals("hooked", False)
                        self.app.set_status("插件CHATHOOK的WEBHOOK已关闭8000端口的监听.")
                        if self.app.current_session:
                            self.app.current_session.info("插件CHATHOOK的WEBHOOK已关闭8000端口的监听.", "CHATHOOK")
                except Exception as e:
                    self.app.set_status(f"插件CHATHOOK的WEBHOOK监听服务关闭时出现错误: {e}")

            def sendFullme(self, session, link, extra_text = "FULLME", user = 5):
                pass


        def PLUGIN_PyMUD_START(app):
            "PyMUD自动读取并加载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动加载一次"
            chathook = ChatHook(app)
            app.set_status(f"插件{PLUGIN_NAME}已加载!")

        def PLUGIN_SESSION_CREATE(session: Session):
            "在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次"
            #session.info(f"插件{PLUGIN_NAME}已被本会话加载!!! 已成功向本会话中添加触发器 {TRIGGER_ID} !!!")
            session.addAlias(Alias(session, "^starthook$",  id = "ali_starthook", onSuccess = lambda name, line, wildcards: session.globals.hook.start_webhook()))
            session.addAlias(Alias(session, "^stophook$",   id = "ali_stophook",  onSuccess = lambda name, line, wildcards: session.globals.hook.stop_webhook()))
            session.addAlias(Alias(session, "^send\s(.+)$", id = "ali_sendmsg", onSuccess = partial(sendMessageToHook, session)))

        def PLUGIN_SESSION_DESTROY(session: Session):
            "在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。"
            #session.delTrigger(session.tris[TRIGGER_ID])


    .. code:: Python

        # 文件名: main.py (非完整代码，仅用于展示 global 的应用)
        # 主脚本函数，调用hook来向远程服务器发送信息

        import webbrowser
        from pymud import Session, Trigger

        class Configuration:
            def __init__(self, session: Session):
                self.session = session
                tri_webpage = Trigger(self.session, id = 'tri_webpage', patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', group = "sys", onSuccess = self.ontri_webpage)
                self.session.addTrigger(tri_webpage)

            def ontri_webpage(self, name, line, wildcards):
                # 使用 session.getGlobal 来获取全局变量 hooked 的值。当不存在该变量时，返回给定默认值False
                hooked = self.session.getGlobal("hooked", False)
                if not hooked:
                    webbrowser.open(line)
                else:
                    user = self.session.getVariable("chat_hook_user", 5)
                    # 使用 session.globals 点访问器来快捷访问全局变量 hook 对象，并直接调用其函数 sendFullme
                    self.session.globals.hook.sendFullme(self.session, line, user = user)

6.4 定时器
------------------------

6.4.1 定时器概览
^^^^^^^^^^^^^^^^^^^^^

    要周期性的执行某段代码，会使用到定时器（Timer）。PyMUD支持多种特性的定时器，并内置实现了 `Timer`_ 和 `SimpleTimer`_ 两个基础类。

    要在会话中使用定时器，要做的两件事是：

    - 构建一个Timer类（或其子类）的实例。SimpleTimer是Timer的子类，你也可以构建自己定义的子类。
    - 将该实例通过 `session.addTimer <references.html#pymud.Session.addTimer>`_ 方法或 `session.addObject <references.html#pymud.Session.addObject>`_ 增加到会话的定时器清单中。
    - 也可以通过 `session.addTimers <references.html#pymud.Session.addTimers>`_ 方法或 `session.addObjects <references.html#pymud.Session.addObjects>`_ 来同时添加多个定时器。

6.4.2 类型定义与构造函数
^^^^^^^^^^^^^^^^^^^^^^^^^^^^    

    `Timer`_ 是定时器的基础类，继承自 `BaseObject`_ 类。 `SimpleTimer`_ 继承自 `Timer`_ ，可以直接用命令而非函数来实现定时器超时的操作。

    二者的构造函数分别如下：

    .. code:: Python

        class Timer(BaseObject):
            def __init__(self, session, *args, **kwargs):
                pass

        class SimpleTimer(Timer):
            def __init__(self, session, code, *args, **kwargs):
                pass

    除重要的参数session（指定会话）、code（SimpleTimer指定执行代码之外），
    其余所有定时器的参数都通过命名参数在kwargs中指定。定时器支持和使用的命名参数、默认值及其含义如下：

    + id: 唯一标识符。不指定时，默认生成session中此类的唯一标识。
    + group: 触发器所属的组名，默认未空。支持使用session.enableGroup来进行整组对象的使能/禁用
    + enabled: 使能状态，默认为True。标识是否使能该定时器。
    + timeout: 超时时间，即定时器延时多久后执行操作，默认为10s
    + oneShot: 单次执行，默认为False。当为True时，定时器仅响应一次，之后自动停止。否则，每隔timeout时间均会执行。
    + onSuccess: 函数的引用，默认为空。当定时器超时时自动调用的函数，函数类型应为func(id)形式。
    + code: SimpleTimer独有，定时器到达超时时间后执行的代码串。该代码串类似于zmud的应用，可以用mud命令、别名以分号（；）隔开，也可以在命令之中插入PyMUD支持的#指令。

6.4.3 定时器使用示例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^        

    下列代码中实现了两个定时器，均用于在莫高窟冥想时，每隔5s发送一次mingxiang命令。
    其中一个使用SimpleTimer实现，另一个使用标准Timer实现，并增加了仅在会话连接状态下发送的判断。
    同时，该定时器在每一次执行之后，调整定时器时间为1-10s内的一个新随机值。

    .. code:: Python

        # examples for Timer and SimpleTimer
        from pymud import Timer, SimpleTimer, Session

        class Configuration:
            def __init__(self, session: Session):
                self.session = session
                
                # 使用SimpleTimer定义一个默认10s超时的定时器, id自动生成, 超时执行代码 mingxiang
                self.aTimer1 = SimpleTimer(session, code = 'mingxiang')
                # 使用Timer定义一个5秒超时的定时器, id为timer2, 并指定本类型的onTimerMX2方法为超时执行函数
                self.aTimer2 = Timer(session, timeout = 5, id = 'timer2', onSuccess = self.onTimer2)
                
                # 多个定时器可以使用list保存
                self._timersList = [self.aTimer1, self.aTimer2]

                # 多个定时器也可以使用dict保存 (向前兼容)
                self._timersDict = {'timer1': self.aTimer1, 'timer2': self.aTimer2}

                # 可以通过addTimer将定时器加入会话
                session.addTimer(self.aTimer1)

                # 也可以通过addObject将定时器加入会话
                session.addObject(self.aTimer2)

                # 也可以通过addObjects将所有定时器添加到会话
                session.addObjects(self._timersList)         # 支持list对象
                session.addObjects(self._timersDict)         # 也支持dict对象

                # 也可以通过addTimers将所有定时器添加到会话, 同样也支持list对象或dict对象
                session.addTimers(self._timersList)
                session.addTimers(self._timersDict)

            def __unload__(self):
                # 可以通过delTimer从会话中移除单个定时器
                self.session.delTimer(self.aTimer2)         # delTimer 支持 Timer 对象
                self.session.delTimer('timer2')             # delTimer 也支持 Timer id

                # 也可以通过delObject从会话中移除单个定时器
                self.session.delObject(self.aTimer1)        # delObject 仅支持对象形式, 不支持id形式

                # 也可以通过delTimers从会话中移除所有定时器
                self.session.delTimers(self._timersList)    # 支持 Timer 对象的列表
                self.session.delTimers(['timer2'])          # 也支持 Timer 对象的 id 列表

                # 还以通过delObjects从会话中移除所有定时器
                self.session.delObjects(self._timersList)   # delObjects 支持对象列表形式
                self.session.delObjects(self._timersDict)   # delObjects 也支持对象字典形式

            # timer2的超时回调函数，该函数由系统自动调用，并传递定时器的 id 作为参数
            def onTimer2(self, id, *args, **kwargs):
                # 定时器超时时若本会话处于连接状态, 则执行代码 mingxiang
                if self.session.connected:
                    self.session.exec('mingxiang')

                # 定时器还支持在运行中动态修改timeout的值
                import random
                timer = self.session.timers[id]
                timer.timeout = random.randint(1, 10)

6.5 别名
------------------------

6.5.1 别名概览
^^^^^^^^^^^^^^^^^^^^^

    当要简化一些输入的MUD命令，或者代入一些参数时，会使用到别名（Alias）。PyMUD支持多种特性的别名，并内置实现了 `Alias`_ 和 `SimpleAlias`_ 两个基础类。

    要在会话中使用别名，要做的两件事是：

    - 构建一个Alias类（或其子类）的实例。SimpleAlias是Alias的子类，你也可以构建自己定义的别名子类。
    - 将该实例通过session.addAlias方法增加到会话的别名清单中。也可以通过session.addAliases来同时添加多个别名

6.5.2 类型定义与构造函数
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    `Alias`_ 是别名的基础类，继承自 `MatchObject`_ 类（事实上就是除简写差异外，完全相同）。 `SimpleAlias`_ 继承自 `Alias`_ ，可以直接用命令而非函数来实现别名触发时的操作。

    二者的构造函数分别如下：

    .. code:: Python

        class Alias(MatchObject):
            def __init__(self, session, patterns, *args, **kwargs):
                pass

        class SimpleAlias(Alias):
            def __init__(self, session, patterns, code, *args, **kwargs):
                pass

    别名的基础类型 `MatchObject`_ 类也是继承自 `BaseObject`_ 类，因此，别名通过 kwargs 指定的关键字参数许多都和 `Timer`_ 定时器相同。
    别名支持和使用的关键字参数、默认值及其含义如下：

    + :id: 唯一标识符。不指定时，默认生成session中此类的唯一标识。
    + :group: 别名所属的组名，默认未空。支持使用session.enableGroup来进行整组对象的使能/禁用
    + :priority: 优先级，默认100。在对键入命令进行别名触发时会按优先级排序执行，越小优先级越高。
    + :enabled: 使能状态，默认为True。标识是否使能该别名。
    + :onSuccess: 函数的引用，默认为空。当别名被触发时自动调用的函数，函数类型应为func(id, line, wildcards)形式。
    + :ignoreCase: 忽略大小写，默认为False。别名模式匹配时是否忽略大小写。
    + :isRegExp：是否正则表达式，默认为True。即指定的别名模式匹配模式patterns是否为正则表达式。

    构造函数中的位置参数含义如下：

    + :session: 指定的会话对象，必须有
    + :patterns: 匹配模式，应传递字符串（正则表达式或原始数据）。
    + :code: SimpleAlias独有，即别名模式匹配成功后，执行的代码串。该代码串类似于zmud的应用，可以用mud命令、别名以分号（；）隔开，也可以在命令之中插入PyMUD支持的#指令，如#wait（缩写为#wa）

6.5.3 别名使用示例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    下列代码中实现了多个别名，展示了SimpleAlias, Alias的各种用法

    .. code:: Python

        # examples for Alias and SimpleAlias
        from pymud import Alias, SimpleAlias, Session

        class Configuration:
            def __init__(self, session: Session):
                self.session = session
                
                # 使用 SimpleAlias 建立一个简单别名，以 yz_xy 将从扬州中央广场到信阳小广场的路径设置为别名，可以如此建立：
                self.alias1 = SimpleAlias(self.session, "^yz_xy$", "#4 w;nw;#5 w")
                # 使用 SimpleAlias 建立一个带参数的简单别名，之后可以使用 gp silver, gp gold, gp letter 等代替 get silver/gold/letter from corpse
                self.alias2 = SimpleAlias(self.session, "^gp\s(.+)$", "get %1 from corpse")
                # 使用 Alias 建立一个标准别名，可以扩展 gp 别名的用法，此时，可以使用 gp2 gold 代替 get gold from corpse 2 命令
                self.alias3 = Alias(self.session, "^gp(\d+)?\s(.+)$", id = "ali_get", onSuccess = self.onali_getfromcorpse)
                # 多个别名可以使用list保存
                self._aliasList = [self.alias1, self.alias2, self.alias3]

                # 多个别名也可以使用dict保存 (向前兼容)
                self._aliasDict = {'alias1': self.alias1, 'alias2': self.alias2, 'ali_get': self.alias3}

                # 可以通过addAlias将单个别名加入会话
                session.addAlias(self.alias1)

                # 也可以通过addObject将单个别名加入会话
                session.addObject(self.alias2)

                # 也可以通过addObjects将所有别名添加到会话
                session.addObjects(self._aliasList)         # 支持list对象
                session.addObjects(self._aliasDict)         # 也支持dict对象

                # 也可以通过addAliases将所有定时器添加到会话, 同样也支持list对象或dict对象
                session.addAliases(self._aliasList)
                session.addAliases(self._aliasDict)

            def __unload__(self):
                # 可以通过delAlias从会话中移除单个别名
                self.session.delAlias(self.alias1)          # delAlias 支持 Alias 类或其子类对象 
                self.session.delAlias('ali_get')            # delAlias 也支持 Alias id

                # 也可以通过delObject从会话中移除单个别名
                self.session.delObject(self.alias1)         # delObject 仅支持对象形式, 不支持id形式

                # 也可以通过delAliases从会话中移除所有定时器
                self.session.delAliases(self._aliasList)    # 支持 Alias 对象的列表
                self.session.delAliases(['ali_get'])        # 也支持 Alias 对象的 id 列表

                # 还以通过delObjects从会话中移除所有定时器
                self.session.delObjects(self._aliasList)    # delObjects 支持对象列表形式
                self.session.delObjects(self._aliasDict)    # delObjects 也支持对象字典形式

            # alias3别名ali_get的成功回调调函数，该函数由系统自动调用，并传递别名的 id、键入的整行 line， 匹配的结果数组 wildcards 作为参数
            # 假设键入的命令为 gp2 gold， 则系统调用该函数时，id, line, wildcards 三个参数分别为：
            # id: 'ali_get' -> 别名的id属性，str类型
            # line: 'gp2 gold' -> 键入的完整命令，str类型
            # wildcards: ['2', 'gold'] -> 匹配的捕获数据形成的列表（数组），由str类型构成的list类型
            def onali_getfromcorpse(self, id, line, wildcards):
                "别名get xxx from corpse xxx"
                index = wildcards[0]
                item  = wildcards[1]

                if index:
                    cmd = f"get {item} from corpse {index}"
                else:
                    cmd = f"get {item} from corpse"

                self.session.writeline(cmd)




.. _#mods: syscommand.html#modules
.. _pymud.Session: references.html#pymud.Session
.. _sessions: settings.html#sessions
.. _BaseObject: references.html#pymud.objects.BaseObject
.. _MatchObject: references.html#pymud.objects.MatchObject
.. _Alias: references.html#pymud.Alias
.. _SimpleAlias: references.html#pymud.SimpleAlias
.. _Timer: references.html#pymud.Timer
.. _SimpleTimer: references.html#pymud.SimpleTimer
.. _插件: plugins.html