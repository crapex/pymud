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

        根据PyMUD模块文件中是否包含名为 Configuration 的类型，或者包含继承自 IConfig 的子类型，将PyMUD模块区分为主配置模块和子配置模块两类。

        将PyMUD模块放在当前目录下之后，可以在命令行通过 ``#load xxx`` 指令加载名为xxx的模块(xxx为模块不包括扩展名.py的文件名，下同)，也可以将名称放在本地 pymud.cfg 中的 sessions_ 字典中以进行自动加载。

        当模块加载完毕之后，可以通过 ``session.modules[module_name]`` 来访问该模块（一般情况下，不需要访问）。此对象是一个 ModuleInfo 类型，该类型有以下几个可用属性和方法:


        .. code:: Python

            readonly property name: str             # 模块名称，只读属性
            readonly property module: ModuleType    # 模块对应的Python的ModuleType类型属性, 只读属性
            readonly property config: dict          # 模块中包含的所有 Configuration 配置类型和 IConfig 配置类型的实例对象，以类型名为字典key
            readonly property ismainmodule: bool    # 模块是否为主模块（主模块定义是包含了配置类型的模块）

            load()                                  # 加载模块对象
            unload()                                # 卸载模块对象
            reload()                                # 重新加载模块对象


        可以在命令行使用 `#mods`_ 命令列出本会话中已加载的所有模块清单。利用 `#mods modulename1 modulename2` 命令列出指定模块的所有配置清单。

        特别说明:
            区分PyMUD模块类型事实上并无绝对意义上的差异。也可以不通过 #load 加载子模块，而在主模块中直接通过 import xxx 加载该模块文件。

            但由于PyMUD实现限制， 在脚本修改之后， #reload 仅可以重新加载由 PyMUD 进行管理的模块，也即是通过 #load 命令 或者 Session.load_module 所加载的模块。
            因此可以使用PyMUD子配置模块来替代 import xxx 的使用。
            对子模块的#reload，需要在引用该子模块的主模块也执行#reload之后才生效。经测试，目前看来，模块的#reload是生效的

    PyMUD子配置模块:
        PyMUD模块中不包含名为 Configuration 的类型，也不包含 IConfig 子类型的PyMUD模块即属于PyMUD子配置模块。
        加载子配置模块时，相当于在 Python 中调用 import xxx 指令。
        加载子配置模块后， ModuleInfo 对象的 config 为 空字典

    PyMUD主配置模块:    
        模块中包含一个或多个名为 Configuration 的类型和 IConfig 子类型的PyMUD模块。该类型构造函数接受一个 `pymud.Session`_ 对象作为唯一必须指定参数。
        这种模块在加载时，除了如子配置模块执行相同操作之外，还将自动创建所有 Configuration 类型以及 IConfig 子类型的实例对象。
        所有创建的对象，以其对象类型名称为 key ，保存在 ModuleInfo 对象的 config 字典中.

        注: 一个主模块中，可以存在多个配置类型

        以下是一个基本的主配置模块的示例：

        .. code:: Python
            
            # filename: mymainmodule.py
            from pymud import Session

            # 一个主模块配置类型
            class Configuration:
                def __init__(self, session: Session):
                    self.session = session

                # 注：0.20.0以后，__unload__或unload函数均可生效
                def __unload__(self):
                    pass

            # 另一个主模块配置类型，该类型既是一个自定义触发器，也是一个配置类型
            # 该配置在模块加载时也会自动创建，因此会话中会自动添加该触发器对象
            class MyCustomTrigger(Trigger, IConfig):
                def __init__(self, session: Session, *args, **kwargs):
                    id = kwargs.get('id', 'my_default_triid')
                    super(Trigger, self).__init__(session, r'^[> ]*你嘻嘻地笑了起', onSuccess = self.ontri, id = id)

                def ontri(self, id, name, wildcards):
                    self.session.exec("smile")
    
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
    
    会话的变量可以使用 #save 命令保存到会话名对应的.mud文件。当配置中设置了 var_autosave 为 True 时，当会话从远程断开连接时会自动保存。
    会话的保存使用了 Python 的 pickle 类型进行处理，因此虽然会话变量的值支持任意 Python类型, 但仍然强烈建议使用可序列化类型。
    会话变量保存的一个例外是，若一个变量名是以下划线开头的，则该变量被认为是临时变量，不会被保存到 .mud 文件中。

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

                # 以下划线开头的变量，会被视作临时变量，在 #save 时，不会保存到 .mud 文件
                self.session.setVariable('_tempVar', 'a TempVar startswith _ will Not Be Saved In .mud File')

                # 将变量保存到 .mud 文件，此时 _tempVar 这个变量不会被保存
                self.session.exec('#save')


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

        from pymud import PyMudApp, Session, Alias
        
        class ChatHook:
            def __init__(self, app: PyMudApp) -> None:
                self.app = app
                
                # 使用 PyMudApp.set_globals 设置一个布尔型全局变量 hooked，指示是否已与chat服务器连接
                self.app.set_globals("hooked", False)
                
                # 使用 快捷点访问器 将本类型的实例赋值给全局变量 hook，用于各会话中使用该对象并调用对象函数
                app.globals.hook = self

            def start_webhook(self):
                try:
                    # 使用 PyMudApp.get_globals 获取全局变量 hooked判断是否已与服务器连接
                    hooked = self.app.get_globals("hooked")
                    if not hooked:
                        asyncio.ensure_future(self.start_webserver())

                except Exception as e:
                    # 此处省略
                    pass

            def stop_webhook(self):
                try:
                    # 使用 PyMudApp.get_globals 获取全局变量 hooked 判断是否已与服务器连接
                    hooked = self.app.get_globals("hooked")
                    if hooked:
                        asyncio.ensure_future(self.stop_webserver())

                except Exception as e:
                    # 此处省略
                    pass

            async def start_webserver(self):
                try:
                    # 其他代码省略

                    # 使用 PyMudApp.set_globals 函数设置 hooked 变量的值
                    self.app.set_globals("hooked", True)

                except Exception as e:
                    # 此处省略
                    pass

            async def stop_webserver(self):
                try:
                    if isinstance(self.site, web.TCPSite):
                        # 其他代码省略

                        # 使用 PyMudApp.set_globals 函数设置 hooked 变量的值
                        self.app.set_globals("hooked", False)

                except Exception as e:
                    # 此处省略
                    pass

            def sendFullme(self, session, link, extra_text = "FULLME", user = 5):
                # 此处省略
                pass

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

    要在会话中使用定时器，需要：

    - 构建一个Timer类（或其子类）的实例。SimpleTimer是系统提供的Timer的子类，用于简单定时器创建。
    - 也可以自定义一个类型，继承自 Timer 类，并同时继承 IConfig 类型，在调用子类构造函数之前指定其他参数默认值。系统在加载该模块文件时，会自动创建该自定义定时器类型实例。

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
    + group: 触发器所属的组名，默认为空。支持使用session.enableGroup来进行整组对象的使能/禁用
    + enabled: 使能状态，默认为True。标识是否使能该定时器。
    + timeout: 超时时间，即定时器延时多久后执行操作，默认为10s
    + oneShot: 单次执行，默认为False。当为True时，定时器仅响应一次，之后自动停止。否则，每隔timeout时间均会执行。
    + onSuccess: 函数的引用，默认为空。当定时器超时时自动调用的函数，函数类型应为func(id)形式。
    + code: SimpleTimer独有，定时器到达超时时间后执行的代码串。该代码串类似于zmud的应用，可以用mud命令、别名以分号（；）隔开，也可以在命令之中插入PyMUD支持的#指令。

6.4.3 定时器使用示例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^        

    下列代码中实现了两个定时器，均用于在莫高窟冥想时，每隔5s发送一次mingxiang命令。
    其中一个使用SimpleTimer实现，另一个使用标准Timer实现，并增加了仅在会话连接状态下发送的判断。

    .. code:: Python

        # examples for Timer and SimpleTimer
        from pymud import IConfig, Timer, SimpleTimer, Session

        # 定义一个配置类型
        class TimerTest(IConfig):
            def __init__(self, session: Session):
                self.session = session
                
                self._objs = [
                    # 使用SimpleTimer定义一个默认10s超时的定时器, id自动生成, 超时执行代码 mingxiang. 创建时，系统将自动将该实例加入会话，后通
                    SimpleTimer(session, code = 'mingxiang'),
                    # 使用Timer定义一个5秒超时的定时器, id为timer2, 并指定本类型的onTimerMX2方法为超时执行函数，创建时默认不使能
                    Timer(session, timeout = 5, id = 'timer2', enabled = False, onSuccess = self.onTimer2)
                ]

                # 在脚本中，可以对指定id的定时器通过 点访问器快速访问
                self.session.timers.timer2.enabled = True
                # 也可以通过标准字典关键字形式访问，并且 timeout 参数还可以动态调整
                self.session.timers['timer2'].timeout = 10

            def __unload__(self):
                # 卸载时通过 delObjects 将创建的对象删除
                self.delObjects(self._objs)
                
            # timer2的超时回调函数，该函数由系统自动调用，并传递定时器的 id 作为参数
            def onTimer2(self, id, *args, **kwargs):
                # 定时器超时时若本会话处于连接状态, 则执行代码 mingxiang
                if self.session.connected:
                    self.session.exec('mingxiang')

        # 命令行中，可以使用 #ti, #timer 操作定时器，比如
        # #ti timer2 off -> 停止上面创建的定时器2
        # #ti timer2 on  -> 启动上面创建的定时器2
        # #ti timer2 del -> 删除上面创建的定时器2
        # #ti timer2     -> 查看定时器2的详细信息
        # #ti            -> 列出所有会话中的定时器              


6.5 别名
------------------------

6.5.1 别名概览
^^^^^^^^^^^^^^^^^^^^^

    当要简化一些输入的MUD命令，或者代入一些参数时，会使用到别名（Alias）。PyMUD支持多种特性的别名，并内置实现了 `Alias`_ 和 `SimpleAlias`_ 两个基础类。

    要在会话中使用别名，需要：

    - 构建一个Alias类（或其子类）的实例。SimpleAlias是系统提供的Alias的子类，用于创建简单别名。
    - 也可以自定义一个类型，继承自 Alias 类，并同时继承 IConfig 类型，在调用子类构造函数之前指定其他参数默认值。系统在加载该模块文件时，会自动创建该自定义类型实例。
    

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
    + :group: 别名所属的组名，默认为空。支持使用session.enableGroup来进行整组对象的使能/禁用
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
        from pymud import IConfig, Alias, SimpleAlias, Session

        class AliasTest(IConfig):
            def __init__(self, session: Session):
                self.session = session
                
                self._objs = [
                    # 使用 SimpleAlias 建立一个简单别名，以 yz_xy 将从扬州中央广场到信阳小广场的路径设置为别名，可以如此建立：
                    SimpleAlias(self.session, "^yz_xy$", "#4 w;nw;#5 w"),
                    # 使用 SimpleAlias 建立一个带参数的简单别名，之后可以使用 gp silver, gp gold, gp letter 等代替 get silver/gold/letter from corpse
                    SimpleAlias(self.session, "^gp\s(.+)$", "get %1 from corpse"),
                    # 使用 Alias 建立一个标准别名，可以扩展 gp 别名的用法，此时，可以使用 gp2 gold 代替 get gold from corpse 2 命令
                    Alias(self.session, "^gp(\d+)?\s(.+)$", id = "ali_get", onSuccess = self.onali_getfromcorpse)
                ]
                
                # 在脚本中，可以对指定id的别名通过 点访问器快速访问
                self.session.alis.ali_get.enabled = False
                # 也可以通过标准字典关键字形式访问，并且 patterns 参数也还可以动态调整 (别名一般不这样使用)
                self.session.alis['ali_get'].patterns = "new_patterns"

            def __unload__(self):
                self.session.delObjects(self._objs)

            # 别名ali_get的成功回调调函数，该函数由系统自动调用，并传递别名的 id、键入的整行 line， 匹配的结果数组 wildcards 作为参数
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

        # 命令行中，可以使用 #ali, #alias 操作别名，比如
        # #ali ali_get off -> 停止上面创建的别名
        # #ali ali_get on  -> 启动上面创建的别名
        # #ali ali_get del -> 删除上面创建的别名
        # #ali ali_get     -> 查看别名的详细信息
        # #ali             -> 列出会话中的所有别名    

6.6 触发器
------------------------

6.6.1 触发器概览
^^^^^^^^^^^^^^^^^^^^^

    当要针对服务器的响应执行对应的操作，则要使用到触发器（Trigger）。PyMUD支持多种特性的触发器，并内置实现了 `Trigger`_ 和 `SimpleTrigger`_ 两个基础类。

    要在会话中使用触发器，需要：

    - 构建一个Trigger类（或其子类）的实例。SimpleTrigger是系统提供的Trigger的子类，用于创建简单触发器。
    - 也可以自定义一个类型，继承自 Trigger 类，并同时继承 IConfig 类型，在调用子类构造函数之前指定其他参数默认值。系统在加载该模块文件时，会自动创建该自定义类型实例。

6.6.2 类型定义与构造函数
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    `Trigger`_ 是触发器的基础类，同 Alias 一样，也是继承自 `MatchObject`_ 类。 `SimpleTrigger`_ 继承自 `Trigger`_ ，可以直接用命令而非函数来实现触发时的操作。

    二者的构造函数分别如下：

    .. code:: Python

        class Trigger(MatchObject):
            def __init__(self, session, patterns, *args, **kwargs):
                pass

        class SimpleTrigger(Alias):
            def __init__(self, session, patterns, code, *args, **kwargs):
                pass

    触发器也是继承的基础类型 `MatchObject`_ ，与别名存在很多相似性。一个是对输入的内容进行匹配后触发相应的操作，另一个时对收到的服务器内容进行匹配后触发响应的操作。
    因此，触发器通过 kwargs 指定的关键字参数许多都和 `Alias`_ 别名相同。触发器支持和使用的关键字参数、默认值及其含义如下：

    与Alias定义基本类似的关键字参数包括:

    + :id: 唯一标识符。不指定时，默认生成session中此类的唯一标识。
    + :group: 触发器所属的组名，默认为空。支持使用session.enableGroup来进行整组对象的使能/禁用
    + :priority: 优先级，默认100。在对收到服务器内容触发时会按优先级排序执行，越小优先级越高。
    + :enabled: 使能状态，默认为True。标识是否使能该触发器。
    + :onSuccess: 函数的引用，默认为空。当触发器被触发时自动调用的函数，函数类型应为func(id, line, wildcards)形式。
    + :ignoreCase: 忽略大小写，默认为False。触发器进行模式匹配时是否忽略大小写。
    + :isRegExp：是否正则表达式，默认为True。即指定的触发器模式匹配模式patterns是否为正则表达式。

    触发器额外生效的关键字参数包括:

    + keepEval: 匹配成功后持续进行后续匹配，默认为False。当有两个满足相同匹配模式的触发器时，要设置该属性为True，否则第一次匹配成功后，该行不会进行后续触发器匹配（意味着只有最高优先级的触发器会被匹配）
    + raw: 原始代码匹配，默认为False。当为True时，对MUD服务器的数据原始代码（含ANSI字符、VT100控制指令等）进行匹配。在进行颜色匹配的时候使用。

    另外，构造函数中的位置参数含义如下：

    + :session: 指定的会话对象，必须有
    + :patterns: 匹配模式，应传递字符串（正则表达式或原始数据）。多行触发时，传递一个匹配模式的列表。
    + :code: SimpleAlias独有，即别名模式匹配成功后，执行的代码串。该代码串类似于zmud的应用，可以用mud命令、别名以分号（；）隔开，也可以在命令之中插入PyMUD支持的#指令，如#wait（缩写为#wa）

6.6.3 触发器基本使用示例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    下列代码中实现了多个触发器，展示了SimpleTrigger, Trigger的各种用法

    .. code:: Python

        # examples for Trigger and SimpleTrigger
        import webbrowser
        from pymud import IConfig, Trigger, SimpleTrigger, Session


        HP_KEYS = (
                "combat_exp", "potential", "max_neili", "neili", "max_jingli", "jingli", 
                "max_qi", "eff_qi", "qi", "max_jing", "eff_jing", "jing", 
                "vigour/qi", "vigour/yuan", "food", "water", "fighting", "busy"
            )

        REGX_HPBRIEF   = [
            r'^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$', 
            r'^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$', 
            r'^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$'
        ]

        REGX_WEAR = r"^.+□(?:\x1b\[[\d;]+m)?(身|脚)\S+一[双|个|件|把](?:\x1b\[([\d;]+)m)?([^\x1b\(\)]+)(?:\x1b\[[\d;]+m)?\(.+\)"

        class TriggerTest(IConfig):
            def __init__(self, session: Session):
                self.session = session
                
                self._trisList = [
                    # 简单触发器使用示例: 
                    # 在新手任务（平一指配药）任务中，要在要到任务后，自动n一步，并在延时500ms后进行配药;配药完成后自动s，并提交配好的药，并再次接下一个任务，则可以使用SimpleTrigger如此建立触发器：
                    SimpleTrigger(self.session, "^[> ]*你向平一指打听有关『工作』的消息。", "n;#wa 500;peiyao"),
                    SimpleTrigger(self.session, "^[> ]*不知过了多久，你终于把药配完。", "s;#wa 500;give ping yao;#wa 500;ask ping about 工作"),

                    # 标准触发器使用示例:
                    # 当收到有关fullme或者其他图片任务的链接信息时，自动调用浏览器打开该网址，则可以建立一个标准触发器（示例中同时指定了触发器id），并使用lambda函数来作为成功回调：
                    Trigger(self.session, id = 'tri_webpage', patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', onSuccess = lambda id, line, wildcards: webbrowser.open(line)),

                    # 多行触发器使用示例
                    # 对hpbrief命令的long模式建立三行触发器，获取hpbrief内容并保存到对应的变量中
                    Trigger(self.session, id = 'tri_hpbrief', patterns = REGX_HPBRIEF, group = "sys", onSuccess = self.ontri_hpbrief),

                    # ANSI触发器使用示例。如果要捕获文字中的颜色、闪烁等特性，则可以使用触发器的raw属性，即使用ANSI触发器。
                    # 在长安爵位任务中，要同时判断路人身上的衣服和鞋子的颜色和类型时，可以使用如下触发：
                    Trigger(self.session, patterns = REGX_WEAR, onSuccess = self.ontri_wear, raw = True)
                ]

                # 可以直接使用点访问器操纵触发器对象
                self.session.tris.tri_hpbrief.enabled = False
                # 也可以使用字典访问，还可以动态调整触发器的 patterns 属性
                self.sessions.tris['tri_hpbrief'].patterns = ['xxx', 'xxx']  # 如从long的三行模式改为两行触发模式

            def __unload__(self):
                # 通过delObjects从会话中移除所有触发器
                self.session.delObjects(self._trisList)    # delObjects 支持对象列表形式

            # hpbrief触发器的成功回调调函数，该函数由系统自动调用，并传递别名的 id、键入的整行 line (多行触发模式下，会返回拼接的多行）， 匹配的结果数组 wildcards 作为参数
            def ontri_hpbrief(self, id, line, wildcards):
                "hpbrief自动保存属性变量参数"
                self.session.setVariables(HP_KEYS, wildcards)

            # 身上穿着look时的成功回调
            def ontri_wear(self, name, line, wildcards):
                buwei = wildcards[0]        # 身体部位，身/脚
                color = wildcards[1]        # 颜色，30,31,34,35为深色，32,33,36,37为浅色
                wear  = wildcards[2]        # 着装是布衣/丝绸衣服、凉鞋/靴子等等
                # 对捕获结果的进一步判断，此处省略

        # 命令行中，可以使用 #tri, #trigger 操作触发器，比如
        # #ali tri_hpbrief off -> 停止上面创建的触发器
        # #ali tri_hpbrief on  -> 启动上面创建的触发器
        # #ali tri_hpbrief del -> 删除上面创建的触发器
        # #ali tri_hpbrief     -> 查看指定触发器详细信息
        # #ali                 -> 列出所有会话中的触发器    


6.6.4 异步触发器
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    PyMUD的触发器同时支持同步模式和异步模式。异步触发器一般用在自定义的Command中。

    - Trigger类的triggered方法是一个async定义的异步函数。可以直接使用await来异步等待触发器的执行。使用异步触发器时，可以不设置onSuccess同步回调函数。
    - 使用异步触发器时，应该使用标准的Trigger类或自定义子类，而不要使用SimpleTrigger，因为其code代码的执行是包含在触发器类的定义中。
    - 当一个触发器同时设置了 onSuccess 回调，并且也使用 await 来异步等待其结果时，其同步回调onSuccess一定在await异步返回之前发生。

    以下以一个打坐触发的异步使用为示例说明异步触发器的用法。
    在该示例中，dazuo/eat/drink代码不是放在Trigger的触发中的，而且该代码逻辑阅读简便，因为async/await是以同步思维进行的异步实现。
    另外，此代码仅用来说明异步触发器的使用示例，若不通过Command进行实现的话，该代码事实上在实际过程中是无法被调用触发的

    .. code:: Python

        from pymud import IConfig, Trigger

        class AsyncTriggerTest(IConfig):
            def __init__(self, session):
                self.session = session
                self._mytri = Trigger(self.session, r"^[> ]*你运功完毕，深深吸了口气，站了起来。", id = "tri_dazuo")

            def __unload__(self):
                self.session.delObject(self._mytri)

            async def dazuo_always(self):
                # 本函数仅用来说明异步触发器的使用示例，若不通过Command进行实现的话，该函数在实际过程中无法被调用触发
                # 此处仅为了说明异步触发器的使用，假设气是无限的，可以无限打坐
                # 目的是每打坐100次，吃干粮，喝酒袋
                time = 0
                while True:                                       # 永久循环
                    self.session.writeline("dazuo 10")            # 发送打坐命令
                    # 此处使用了几个技巧
                    # 1. 使用 tris 快捷访问器 + 触发器 id 来实现获取触发器对象
                    # 2. 使用 session.create_task而不是asyncio.create_task将触发器的异步触发包装成一个任务。好处时该任务会纳入会话的管理中
                    # 使用任务包裹async函数，其目的是为了后续可以对任务进行取消，当没有取消需求，也不需要会话管理时，也可以不使用任务包裹
                    # 即，下面代码也可直接写成：
                    #    await self.session.tris.tri_dazuo.triggered()
                    await self.session.create_task(self.session.tris.tri_dazuo.triggered())     # 等待dazuo触发
                    times += 1
                    if times > 100:
                        self.session.writeline("eat liang")
                        self.session.writeline("drink jiudai")
                        times = 0

6.7 GMCP触发器 (GMCPTrigger)
--------------------------------

6.7.1 GMCP触发器概览
^^^^^^^^^^^^^^^^^^^^^

    当要针对服务器的GMCP消息响应执行对应的操作，则要使用到GMCP触发器（GMCPTrigger）。PyMUD内置实现了 `GMCPTrigger`_ 来处理GMCP消息的响应。
    GMCP触发器调用时通过其id来进行判断的，当存在与服务器数据相同id的GMCPTrigger时，该触发器会被执行。当没有找到匹配id的GMCPTrigger时，会调用默认的打印命令，将收到的GMCP数据打印到当前会话中。
    为保持通用性和一致性，GMCPTrigger许多定义与触发器Trigger相同，比如回调函数接受的参数数量与类型相同，也支持异步模式 triggered 函数，可以在命令Command中统一使用。

    要在会话中使用GMCP触发器，需要：

    - 创建一个GMCPTrigger类（或其子类）的实例, 并将其 id (参数名为 name) 指定为服务器的GMCP消息的标识（区分大小写）

6.7.2 类型定义与构造函数
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    `GMCPTrigger`_ 是GMCP触发器的基础类，继承自 `BaseObject`_ 类。 其构造函数如下：

    .. code:: Python

        class GMCPTrigger(BaseObject):
            def __init__(self, session, name, *args, **kwargs):
                pass

    构造函数参数中，session 用于指定会话对象， name 指定该GMCP触发对应的服务器名称。
    其余参数都通过命名参数在kwargs中指定。支持和使用的命名参数、默认值及其含义如下：

    + group: GMCP触发器所属的组名，默认为空。支持使用session.enableGroup来进行整组对象的使能/禁用
    + enabled: 使能状态，默认为True。标识是否使能该定时器。
    + onSuccess: 函数的引用，默认为空。当定时器超时时自动调用的函数，函数类型应为func(id, line, wildcards)形式。

6.7.3 GMCP触发器使用示例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    下列代码中展示了GMCPTrigger的用法，对北侠服务器中的 GMCP.Status 类型的GMCP数据进行处理。
    北侠服务器 GMCP.Status 类型的GMCP原始数据大概是这样的：
    GMCP.Status = {"is_busy":"false","is_fighting":"false","fighter_spirit":100,"int":18,"per":18,"dex":11,"potential":63206,"con":33,"str":30}

    .. code:: Python

        # examples for GMCPTrigger
        from pymud import IConfig, GMCPTrigger, Session

        class GMCPTest(IConfig):
            def __init__(self, session):
                self.session = session
                self._gmcp_status = GMCPTrigger(self.session, "GMCP.Status", group = "sys", onSuccess = self.ongmcp_status)

            def __unload__(self):
                self.session.delObject(self._gmcp_status)

            ### GMCP处理函数 ###
            # 系统调用该函数时，会传递三个参数，id 为该GMCP的id, line 为GMCP收到的原始数据， wildcards 为经 eval处理后的数据。
            # 比如，对应 GMCP.Status = {"is_busy":"false","is_fighting":"false","fighter_spirit":100,"int":18,"per":18,"dex":11,"potential":63206,"con":33,"str":30} 的这一行数据，三个参数为：
            # id -> GMCP.Status , str 类型
            # line -> {"is_busy":"false","is_fighting":"false","fighter_spirit":100,"int":18,"per":18,"dex":11,"potential":63206,"con":33,"str":30} , str类型
            # wildcards -> {"is_busy":"false","is_fighting":"false","fighter_spirit":100,"int":18,"per":18,"dex":11,"potential":63206,"con":33,"str":30} , 此处会被解析成dict类型
            def ongmcp_status(self, id, line, wildcards):
                # 自己的Status和敌人的Status均会使用GMCP.Status发送
                # 区别在于，敌人的Status会带有id属性。但登录首次自己也会发送id属性，但同时有很多属性，因此增加一个实战经验属性判定

                if isinstance(wildcards, dict):     # 正常情况下，GMCP.Status 应该是一个dict，但为保险起见，此处增加一个类型判断
                    if ("id" in wildcards.keys()) and (not "combat_exp" in wildcards.keys()):
                        # 说明是敌人的状态, 不进行处理
                        pass

                    else:
                        # 说明个人状态是GMCP Status方式，此时hpbrief将不能使用，设置标识供其他地方判断使用
                        self.session.setVariable("status_type", "GMCP")

                        # 将收到的数据中的字符串 "true" 和 "false" 转换为布尔类型的 True 和 False，并将数据保存到会话变量中
                        for key, value in wildcards.items():
                            if value == "false": value = False
                            elif value == "true": value = True
                            self.session.setVariable(key, value)


6.8 命令 (Command)
------------------------

6.8.1 命令概览
^^^^^^^^^^^^^^^^^^^^^

    命令是 PyMUD 的最大特色，也是PyMUD与其他MUD客户端的最大差异所在。它是一组归纳了同步/异步执行、等待响应、处理的集成对象。
    可以这么理解，PyMUD的命令就是将MUD的命令输入、返回响应等封装在一起的一种对象。
    基于命令可以实现从最基本的MUD命令响应，到最复杂的完整的任务辅助脚本。

    `Command`_ 基类仅是提供了一个命令的框架，PyMUD应用基于该框架来在运行中调用和处理各类命令。

    要在PyMUD中使用命令，不能直接使用 `Command`_ 类型，应总是设计自己的命令子类型，继承自 `Command`_ 基类，并覆盖基类的 `execute <references.html#pymud.Command.execute>`_ 方法。

    当对继承Command的自定义命令足够熟悉后，对于某些特定应用场景，可以使用 `SimpleCommand`_ 子类来简化代码写法。
    
    要在会话中使用命令，需要：

    - 设计一个 Command 类型的子类类型，并创建一个该子类类型的实例。
    - 也可以将设计的该子类型同时继承 IConfig, 系统将在加载本文件时自动创建该类型。需要注意的是，子类型构造函数中，只能有session一个必须指定参数。

    此时，调用该命令，只需在命令行与输入该命令匹配模式（patterns) 匹配的文本即可，也可以在脚本中调用 session.exec 系列方法来调用该命令

6.8.2 类型定义与常用方法
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    `Command`_ 也继承自 `MatchObject`_ 类。 其构造函数及使用的参数，与Alias完全相同，此处不再列举。

    与Alias、Trigger的差异是，Command中包含几个新的会经常被使用的方法调用，如下。

    - `create_task <references.html#pymud.Command.create_task>`_ : 实际是session.create_task的包装，在创建任务的同时，除将其加入了session的task清单外，也加入到本Command的Task清单，可以保证执行，也可以供后续操作使用
    - `reset <references.html#pymud.Command.reset>`_ : 复位该任务。复位除了清除标识位之外，还会清除所有未完成的task。在Command的多次调用时，可以手动调用reset方法，以防止同一个命令被多次触发。
    - `unload 或 __unload__ <references.html#pymud.Command.unload>`_ : 卸载方法，子类应该覆盖该方法并在其中清理命令自己添加的各类对象。该方法在Command从会话中移除时自动调用。
    - `execute <references.html#pymud.Command.execute>`_ : async定义的异步方法，子类必须覆盖该方法。该方法在Command被执行时自动调用。

6.8.3 命令使用示例一：CmdMove
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    以下代码设计了一个CmdMove命令，用来处理执行北侠游戏中的移动命令。该命令加入了移动重试功能，当由于某种原因导致行走失败时，可以自动重试5次。

    .. code:: Python

        import asyncio
        from pymud import IConfig, Session, Command, Trigger, GMCPTrigger

        # 房间名匹配正则表达式
        REGX_ROOMNAME = r'^[>]*(?:\s)?(\S.+)\s-\s*(?:杀戮场)?(?:\[(\S+)\]\s*)*(?:㊣\s*)?[★|☆|∞|\s]*$'

        # 移动命令中的各种方位清单
        DIRECTIONS = (
            "n","s","w","e","ne","nw","se","sw",
            "u","d","nu","su","wu","eu","nd","sd","wd","ed",
            "north", "south", "west", "east", "northeast", "northwest", "southeast", "southwest", 
            "up", "down","northup","southup","westup","eastup","northdown","southdown","westdown","eastdown",
            "enter(\s\S+)?", "out", "zuan(\s\S+)?", "\d", "leave(\s\S+)?", "jump\s(jiang|out)", "climb(\s(ya|yafeng|up|west|wall|mount))?",
            "sheshui", "tang", "act zuan to mao wu", "wander", "xiaolu", "cai\s(qinyun|tingxiang|yanziwu)", "row mantuo", "leave\s(\S+)"
            )

        # 移动失败（无法移动）的描述正则匹配清单
        MOVE_FAIL = (
            r'^[> ]*哎哟，你一头撞在墙上，才发现这个方向没有出路。$', 
            r'^[> ]*这个方向没有出路。$',
            r'^[> ]*守军拦住了你的去路，大声喝到：干什么的？要想通过先问问我们守将大人！$',
        )

        # 本次移动失败（但可以重新再走的）的描述正则匹配清单
        MOVE_RETRY = (
            r'^[> ]*你正忙着呢。$', 
            r'^[> ]*你的动作还没有完成，不能移动。$', 
            r'^[> ]*你还在山中跋涉，一时半会恐怕走不出这(六盘山|藏边群山|滇北群山|西南地绵绵群山)！$', 
            r'^[> ]*你一脚深一脚浅地沿着(\S+)向着(\S+)方走去，虽然不快，但离目标越来越近了。',
            r'^[> ]*你一脚深一脚浅地沿着(\S+)向着(\S+)方走去，跌跌撞撞，几乎在原地打转。',
            r'^[> ]*你小心翼翼往前挪动，遇到艰险难行处，只好放慢脚步。$', 
            r'^[> ]*山路难行，你不小心给拌了一跤。$', 
            r'^[> ]*你忽然不辨方向，不知道该往哪里走了。',
            r'^[> ]*走路太快，你没在意脚下，被.+绊了一下。$',
            r'^[> ]*你不小心被什么东西绊了一下，差点摔个大跟头。$',
            r'^[> ]*青海湖畔美不胜收，你不由停下脚步，欣赏起了风景。$', 
            r'^[> ]*(荒路|沙石地|沙漠中)几乎没有路了，你走不了那么快。$', 
            r'^[> ]*你小心翼翼往前挪动，生怕一不在意就跌落山下。$',
        )

        # 直接继承Command和IConfig，这样在加载模块时就会自动创建该类型
        class CmdMove(Command, IConfig):
            MAX_RETRY = 5

            def __init__(self, session: Session, *args, **kwargs):
                # 将所有可能的行走命令组合成匹配模式
                pattern = "^({0})$".format("|".join(DIRECTIONS))
                # 给定一个默认id。用于自动创建该类型时的默认参数
                kwargs.setdefault("id", "cmd_move")
                super().__init__(session, pattern, *args, **kwargs)
                self.session = Session
                self.timeout = 10
                self._executed_cmd = ""

                self._objs = list()

                # 此处使用的GMCPTrigger和Trigger全部使用异步模式，因此均无需指定onSuccess
                self._objs.append(GMCPTrigger(self.session, "GMCP.Move"))
                self._objs.append(Trigger(self.session, REGX_ROOMNAME, id = "tri_move_succ", group = "cmdmove", keepEval = True, enabled = False))

                idx = 1
                for s in MOVE_FAIL:
                    self._objs.append(Trigger(self.session, patterns = s, id = f"tri_move_fail{idx}", group = "cmdmove", enabled = False"))
                    idx += 1

                idx = 1
                for s in MOVE_RETRY:
                    self._objs.append(Trigger(self.session, patterns = s, id = f"tri_move_retry{idx}", group = "cmdmove", enabled = False"))
                    idx += 1

            def __unload__(self):
                self.session.delObjects(self._objs)
                # 注意：命令的 unload 方法中，无论是否继承IConfig，都无需包括删除命令自身的命令
                #   self.session.delObject(self)  意味着这句话不需要（不能有，会导致递归调用）

            async def execute(self, cmd, *args, **kwargs):
                self.reset()

                retry_times = 0
                self.session.enableGroup('cmdmove')

                while True:

                    tasklist = list()
                    for tr in self._objs:
                        tasklist.append(self.create_task(tr.triggered()))

                    done, pending = await self.session.waitfor(cmd, asyncio.wait(tasklist, timeout = self.timeout, return_when = "FIRST_COMPLETED"))

                    for t in list(pending):
                        self.remove_task(t)

                    result = self.NOTSET
                    tasks_done = list(done)
                    if len(tasks_done) > 0:
                        task = tasks_done[0]

                        # 所有触发器在 onSuccess 时需要的参数，在此处都可以通过 task.result() 获取
                        # result返回值与 await tri.triggered() 返回值完全相同
                        # 这种返回值比onSuccess中多一个state参数，该参数在触发器中必定为 self.SUCCESS 值
                        state, id, line, wildcards = task.result()
                        
                        # success
                        if id == 'GMCP.Move':
                            # GMCP.Move: [{"result":"true","dir":["west"],"short":"林间小屋"}]
                            move_info = wildcards[0]
                            if move_info["result"] == "true":
                                roomname = move_info["short"]
                                self.session.setVariable("roomname", roomname)
                                result = self.SUCCESS
                            elif move_info["result"] == "false":
                                result = self.FAILURE
                            
                            break

                        elif id == 'tri_move_succ':
                            roomname = wildcards[0]
                            self.session.setVariable("roomname", roomname)
                            result = self.SUCCESS
                            break

                        elif id.startswith('tri_move_fail'):
                            self.error(f'执行{cmd}，移动失败，错误信息为{line}', '移动')
                            result = self.FAILURE
                            break

                        elif id.startswith('tri_move_retry'):
                            retry_times += 1
                            if retry_times > self.MAX_RETRY:
                                result = self.FAILURE
                                break

                            await asyncio.sleep(2)

                    else:
                        self.warning(f'执行{cmd}超时{self.timeout}秒', '移动')  
                        result = self.TIMEOUT
                        break

                self.session.enableGroup('cmdmove', False)
                return result

    这种命令设计方式能带来很多益处。
    其中一个是，使用这种 Command 方式可以确保该命令被执行完成，而且还可以根据命令的返回值来判定下一步该执行操作。
    另外，这种 Command 不需要额外记忆其他命令，直接使用MUD中的命令即可触发该 Command 对象。
    在上述CmdMove命令创建完成之后，在命令行中键入任意方向（DIRECTIONS中列出的所有可能匹配项）行走，都会触发调用该命令的execute方法。
    另外，在代码中也可以使用以下方式来调用该命令：

    .. code:: Python
        
        # 方式一: 直接使用session方法同步调用。由于同步调用会立即返回，因此该调用方法无发获取返回值
        self.session.exec('e')        
        self.session.exec('s;e;s')               # 还可以在调用中同时指定多个命令。通过 CmdMove 设计中的重试机制，可以确保三步行走到对应的位置
        
        # 方式二: 直接使用session方法异步调用, 该调用方法可以获取返回值, 但这样使用由于需要搜索命令，因此会存在一些性能损失
        result = await self.session.exec_async('e')       # 此处 e 会被匹配为 CmdMove 运行，因此其返回值即为 CmdMove 的 execute 方法运行的返回值。若未被匹配为某个 Command 对象，则返回 None
        result = await self.session.exec_async('s;e;s')   # 异步调用中也可以同时指定多个命令，但此时返回值为最后一个命令的返回值。          
        
        # 方式三: 直接调用该命令的execute方法, 该调用方法也可以获取返回值，这种性能损失最小，并且也可以延迟到对象调用时刻再获取
        #         这种方式下，execute 只能接受一条指令，不能像前面一样传入 "s;e;s" 这种连续指令。
        result = await self.session.cmds.cmd_move.execute("w") 
        result = await self.session.cmds["cmd_move"].execute("w")       # 与上面一行等价

        # 上面建议使用方式三来进行命令调用，因为这种调用将获取命令对象实例延迟到调用的时刻。如果修改了模块配置需要 #reload 的时候，引用此命令的模块不需要重新 #reload。方式二虽然有相同效果，但是方式二存在

        # 在确保命令执行完毕后，并根据返回结果判断下一步处置：
        if result == self.SUCCESS:
            # 成功后的代码
            self.session.exec('buy jiudai')
            pass
        elif result == self.FAILURE:
            # 失败后的代码
            pass
        elif result == self.TIMEOUT:
            # 超时之后的代码
            pass
        

6.8.4 命令使用示例二：CmdDazuoto
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    以下代码设计了一个CmdDazuoto命令，用来处理执行北侠游戏中的打坐有关的事项。
    要使用该命令，也应该在创建一个命令的实例，并添加到会话中。有关代码此处省略。
    之后，可以通过命令行键入 dzt xxx 来执行不同的打坐
    并且，'dzt;e;s;n' 这种键入方式也可以确保移动是在打坐完成之后才进行。

    .. code:: Python

        import re, traceback, math
        from pymud import IConfig, Command, Session, Trigger

        # 本Command引用了其他三个设计好的Command，分别用于处理 'jifa/enable'命令, 'hpbrief' 命令, 以及各类生活命令（吃、喝）

        class CmdDazuoto(Command, IConfig):
            """
            各种打坐的统一命令, 使用方法：
            dzt 0 或 dzt always: 一直打坐
            dzt 1 或 dzt once: 执行一次dazuo max
            dzt 或 dzt max: 持续执行dazuo max，直到内力到达接近2*maxneili后停止
            dzt dz: 使用dz命令一直dz
            dzt stop: 安全终止一直打坐命令
            """

            def __init__(self, session, *args, **kwargs):
                id = kwargs.get("id", "cmd_dazuoto")    # 配置id默认值供自动加载使用
                super().__init__(session, "^(dzt)(?:\s+(\S+))?$", *args, **kwargs)
                                
                self._triggers = {}
                self._initTriggers()

                self._force_level = 0   # 内功激发后有效等级
                self._dazuo_point = 10  # 每次打坐点数，默认为10

                self._halted = False

            def _initTriggers(self):
                self._triggers["tri_dz_done"]   = self.tri_dz_done      = Trigger(self.session, r'^[> ]*(..\.\.)*你运功完毕，深深吸了口气，站了起来。', id = "tri_dz_done", keepEval = True, group = "dazuoto")
                self._triggers["tri_dz_noqi"]   = self.tri_dz_noqi      = Trigger(self.session, r'^[> ]*你现在的气太少了，无法产生内息运行全身经脉。|^[> ]*你现在气血严重不足，无法满足打坐最小要求。|^[> ]*你现在的气太少了，无法产生内息运行小周天。', id = "tri_dz_noqi", group = "dazuoto")
                self._triggers["tri_dz_nojing"] = self.tri_dz_nojing    = Trigger(self.session, r'^[> ]*你现在精不够，无法控制内息的流动！', id = "tri_dz_nojing", group = "dazuoto")
                self._triggers["tri_dz_wait"]   = self.tri_dz_wait      = Trigger(self.session, r'^[> ]*你正在运行内功加速全身气血恢复，无法静下心来搬运真气。', id = "tri_dz_wait", group = "dazuoto")
                self._triggers["tri_dz_halt"]   = self.tri_dz_halt      = Trigger(self.session, r'^[> ]*你把正在运行的真气强行压回丹田，站了起来。', id = "tri_dz_halt", group = "dazuoto")
                self._triggers["tri_dz_finish"] = self.tri_dz_finish    = Trigger(self.session, r'^[> ]*你现在内力接近圆满状态。', id = "tri_dz_finish", group = "dazuoto")
                self._triggers["tri_dz_dz"]     = self.tri_dz_dz        = Trigger(self.session, r'^[> ]*你将运转于全身经脉间的内息收回丹田，深深吸了口气，站了起来。|^[> ]*你的内力增加了！！', id = "tri_dz_dz", group = "dazuoto")

            def __unload__(self):
                self.session.delObjects(self._triggers)

            # 各种打坐的具体逻辑处理
            async def dazuo_to(self, to):
                # 开始打坐
                dazuo_times = 0             # 记录次数，用于到次数补充食物和水

                self.tri_dz_done.enabled = True

                # 首次执行时，调用 jifa命令以获取有效内功等级
                if not self._force_level:
                    await self.session.exec_async("enable")     # 此处调用了其他模块中设计的 cmdEnable 命令
                    force_info = self.session.getVariable("eff-force", ("none", 0))
                    self._force_level = force_info[1]

                # 根据有效内功等级，设置每次打坐的点数。具体为：有效等级-5后除以10圆整，最小为10
                self._dazuo_point = (self._force_level - 5) // 10
                if self._dazuo_point < 10:  self._dazuo_point = 10
                
                # 通过hpbrief命令获取当前的各种状态。若状态模式使用GMCP时，自动从GMCP中获取
                if self.session.getVariable("status_type", "hpbrief") == "hpbrief":
                    await self.session.exec_async("hpbrief")    # 此处调用了其他模块中设计的 cmdHpbrief命令

                # 根据hpbrief命令或者自动从GMCP中获取的数据，取出当前内力、最大内力
                neili = int(self.session.getVariable("neili", 0))
                maxneili = int(self.session.getVariable("max_neili", 0))

                # 设置触发器等待超时时间，一般情况下10秒，当执行dz 或者 dazuo max 时，需要等待的时间都可能超过10s，因此设置一个大值
                TIMEOUT_DEFAULT = 10
                TIMEOUT_MAX = 360

                timeout = TIMEOUT_DEFAULT

                # 根据不同参数，设置不同的相关命令和提示
                if to == "dz":
                    cmd_dazuo = "dz"
                    timeout = TIMEOUT_MAX
                    self.tri_dz_dz.enabled = True
                    self.info('即将开始进行dz，以实现小周天循环', '打坐')

                elif to == "max":
                    cmd_dazuo = "dazuo max"
                    timeout = TIMEOUT_MAX
                    need = math.floor(1.90 * maxneili)
                    self.info('当前内力：{}，需打坐到：{}，还需{}, 打坐命令{}'.format(neili, need, need - neili, cmd_dazuo), '打坐')

                elif to == "once":
                    cmd_dazuo = "dazuo max"
                    timeout = TIMEOUT_MAX
                    self.info('将打坐1次 {dazuo max}.', '打坐')

                else:
                    cmd_dazuo = f"dazuo {self._dazuo_point}"
                    self.info('开始持续打坐, 打坐命令 {}'.format(cmd_dazuo), '打坐')

                # 各类打坐命令的主循环
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

                    done, pending = await self.session.waitfor(cmd_dazuo, asyncio.wait(waited_tris, timeout = timeout, return_when = "FIRST_COMPLETED"))

                    for t in list(pending):
                        self.remove_task(t)

                    tasks_done = list(done)
                    if len(tasks_done) == 0:
                        # 这里表示超时了
                        self.info('打坐中发生了超时问题，将会继续重新来过', '打坐')

                    elif len(tasks_done) == 1:
                        task = tasks_done[0]
                        _, name, _, _ = task.result()
                        
                        # 若完成的触发器任务是 tri_dz_done 或者 tri_dz_dz， 根据to的不同判断如何进行后续
                        if name in (self.tri_dz_done.id, self.tri_dz_dz.id):
                            if (to == "always"):
                                dazuo_times += 1
                                if dazuo_times > 100:
                                    # 此处，每打坐100次，补满水食物
                                    self.info('该吃东西了', '打坐')
                                    await self.session.exe_async("feed")        # 此处调用了其他模块设计的吃喝命令
                                    dazuo_times = 0

                            elif (to == "dz"):
                                dazuo_times += 1
                                if dazuo_times > 50:
                                    # 此处，每打坐50次，补满水食物
                                    self.info('该吃东西了', '打坐')
                                    await self.session.exe_async("feed")        # 此处调用了其他模块设计的吃喝命令
                                    dazuo_times = 0

                            elif (to == "max"):
                                # 当执行max后，如果有效内功大于161级，吸个气
                                if self._force_level >= 161:
                                    self.session.writeline("exert recover")
                                    await asyncio.sleep(0.2)

                            elif (to == "once"):
                                self.info('打坐1次任务已成功完成.', '打坐')
                                break

                        # 若捕获到 noqi 的触发器（你的气不足），根据有效内功等级判断处理。当161以上使用正循环，即吸气后继续；当小于时，等待（发呆）15秒后继续打坐
                        elif name == self.tri_dz_noqi.id:
                            if self._force_level >= 161:
                                await asyncio.sleep(0.1)
                                self.session.writeline("exert recover")
                                await asyncio.sleep(0.1)
                            else:
                                await asyncio.sleep(15)

                        # 若捕获到 nojing 的触发器（你的精不足），直接吸气
                        elif name == self.tri_dz_nojing.id:
                            await asyncio.sleep(1)
                            self.session.writeline("exert regenerate")
                            await asyncio.sleep(1)

                        # 若捕获触发器为 dz_wait （处于exert qi/exert jing过程中），等待5秒
                        elif name == self.tri_dz_wait.id:
                            await asyncio.sleep(5)

                        # 若捕获到人工halt命令输入后，终止本循环
                        elif name == self.tri_dz_halt.id:
                            self.info("打坐已被手动halt中止。", '打坐')
                            break

                        # 若捕获到最大内力触发器，终止本循环
                        elif name == self.tri_dz_finish.id:
                            self.info("内力已最大，将停止打坐。", '打坐')
                            break

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


6.8.5 SimpleCommand示例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    在已经理解了 Command 用法之后，在某些特定情况下，可以使用 SimpleCommand 来简化代码。
    SimpleCommand 类型的构造函数如下：

    .. code:: Python

        class SimpleCommand(Command)
            def __init__(self, session, patterns, succ_tri, *args, **kwargs):
                pass

    可以看出，相对于Command, SimpleCommand 的位置参数中多了一个 succ_tri，用于指定表示成功的触发器。位置参数意味着必须指定该属性。
    另外，在 kwargs 的关键字参数中， SimpleCommand 多出了 fail_tri 和 retry_tri 两个字段，用于指定失败和重试的触发器。在关键字参数中意味着可以不指定。

    以上面示例一， CmdMove 命令来讲解如何使用 SimpleCommand 简化代码：

    .. code:: Python

        aSimpleMove = SimpleCommand(
            session, 
            "^({0})$".format("|".join(DIRECTIONS)),
            succ_tri = Trigger(self.session, REGX_ROOMNAME, id = "tri_move_succ", group = "cmdmove", keepEval = True, enabled = False),
            fail_tri = [Trigger(self.session, patterns = s, id = f"tri_move_fail{idx}", group = "cmdmove", enabled = False") for s in MOVE_FAIL],
            retry_tri = [Trigger(self.session, patterns = s, id = f"tri_move_retry{idx}", group = "cmdmove", enabled = False")],
            timeout = 10
        )

    其 execute 方法有一个默认调用，当命令输入后，若触发的是succ_tri中的对象（例中只有一个），则返回 SUCCESS， 若触发的是 fail_tri 中的对象，则返回 FAIL，
    若触发的是 retry_tri 中的对象，则重试 SimpleCommand.MAX_RETRY 次数（20）。若超过 timeout 指定的超时时间（未指定时默认10s），则返回 TIEMOUT。

    从上面的示例可以看出， SimpleCommand 只是简化了代码写法，因此应该被翻译为“简化的Command”，而不是“简单的Command” :）

    SimpleCommand 使用局限性太大，除了极少数懒得写代码的场景，我个人已经不使用 SimpleCommand 而是使用自定义类继承 Command 来解决一切问题了。


6.9 状态栏与状态窗口
------------------------
    状态栏是指命令行下面的灰色背景的栏目，其左边部分可以通过代码设置显示纯文本信息。设置代码为：

    .. code:: Python
        
        session.application.set_status('您要显示的信息')

    可以通过 pymud.cfg 文件中的 status_display , status_width, status_height 的组合使用设置状态窗口的显示位置和尺寸，可以显示在下方、右方或不显示。
    
    状态栏通过脚本定制状态窗口内容。要定制状态窗口的显示内容，将session.status_maker属性赋值为一个返回支持显示结果的函数即可。可以支持标准字符串或者prompt_toolkit所支持的格式化显示内容。
    
    有关prompt_toolkit的格式化字符串显示，可以参见该库的官方帮助页面： https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html

    以下是一个实现状态窗口的示例，使用了 FormattedTextTuple 形式展示了带格式并且可以支持鼠标操作的状态窗口。显示效果见下图

    .. image:: _static/status_window.png
        :alt: 状态窗口样例

    .. code:: Python

        def status_window(self):
            try:
                formatted_list = list()

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
                formatted_list.append((Settings.styles["value"], "{0}({1})".format(self.session.getVariable('name'), self.session.getVariable('id'))))
                formatted_list.append(("", " "))

                # fullme time
                fullme = int(self.session.getVariable('%fullme', 0))
                delta = time.time() - fullme
                formatted_list.append((Settings.styles["title"], "【FULLME】"))
                if delta < 30 * 60:
                    style = Settings.styles["value"]
                elif delta < 60 * 60:
                    style = Settings.styles["value.worse"]
                else:
                    style = Settings.styles["value.worst"]
                if fullme == 0:
                    formatted_list.append((Settings.styles["value.worst"], "从未"))
                else:
                    formatted_list.append((style, "{}".format(int(delta // 60))))
                formatted_list.append(("", " "))

                
                formatted_list.append((Settings.styles["title"], "【食物】"))
                
                food = int(self.session.getVariable('food', '0'))
                max_food = self.session.getVariable('max_food', 350)
                if food < 100:
                    style = Settings.styles["value.worst"]
                elif food < 200:
                    style = Settings.styles["value.worse"]
                elif food < max_food:
                    style = Settings.styles["value"]
                else:
                    style = Settings.styles["value.better"]

                formatted_list.append((style, "{}".format(food)))
                formatted_list.append(("", " "))

                formatted_list.append((Settings.styles["title"], "【饮水】"))
                water = int(self.session.getVariable('water', '0'))
                max_water = self.session.getVariable('max_water', 350)
                if water < 100:
                    style = Settings.styles["value.worst"]
                elif water < 200:
                    style = Settings.styles["value.worse"]
                elif water < max_water:
                    style = Settings.styles["value"]
                else:
                    style = Settings.styles["value.better"]
                formatted_list.append((style, "{}".format(water)))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【经验】"))
                formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('combat_exp'))))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【潜能】"))
                formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('potential'))))
                formatted_list.append(("", " "))

                formatted_list.append((Settings.styles["title"], "【门派】"))
                formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('family/family_name'))))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【存款】"))
                formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('deposit'))))
                formatted_list.append(("", " "))
                
                # line 2. hp
                #(jing, effjing, maxjing, jingli, maxjingli, qi, effqi, maxqi, neili, maxneili) = self.session.getVariables(("jing", "eff_jing", "max_jing", "jingli", "max_jingli", "qi", "eff_qi", "max_qi", "neili", "max_neili"))
                jing = self.session.getVariable("jing", 0)
                effjing = self.session.getVariable("eff_jing", 0)
                maxjing = self.session.getVariable("max_jing", 0)
                jingli = self.session.getVariable("jingli", 0)
                maxjingli = self.session.getVariable("max_jingli", 0)
                qi = self.session.getVariable("qi", 0)
                effqi = self.session.getVariable("eff_qi", 0)
                maxqi = self.session.getVariable("max_qi", 0)
                neili = self.session.getVariable("neili", 0)
                maxneili = self.session.getVariable("max_neili", 0)
                #if jing and effjing and maxjing and effqi and maxqi and qi and jingli and maxjingli and neili and maxneili:
                # a new-line
                formatted_list.append(("", "\n"))

                formatted_list.append((Settings.styles["title"], "【精神】"))
                if int(effjing) < int(maxjing):
                    style = Settings.styles["value.worst"]
                elif int(jing) < 0.8 * int(effjing):
                    style = Settings.styles["value.worse"]
                else:
                    style = Settings.styles["value"]
                
                if maxjing == 0: 
                    pct1 = pct2 = 0
                else:
                    pct1 = 100.0*float(jing)/float(maxjing)
                    pct2 = 100.0*float(effjing)/float(maxjing)
                formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(jing, pct1, effjing, pct2)))

                formatted_list.append(("", " "))

                formatted_list.append((Settings.styles["title"], "【气血】"))
                if int(effqi) < int(maxqi):
                    style = Settings.styles["value.worst"]
                elif int(qi) < 0.8 * int(effqi):
                    style = Settings.styles["value.worse"]
                else:
                    style = Settings.styles["value"]

                if maxqi == 0: 
                    pct1 = pct2 = 0
                else:
                    pct1 = 100.0*float(qi)/float(maxqi)
                    pct2 = 100.0*float(effqi)/float(maxqi)
                formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(qi, pct1, effqi, pct2)))
                formatted_list.append(("", " "))

                formatted_list.append((Settings.styles["title"], "【精力】"))
                if int(jingli) < 0.6 * int(maxjingli):
                    style = Settings.styles["value.worst"]
                elif int(jingli) < 0.8 * int(maxjingli):
                    style = Settings.styles["value.worse"]
                elif int(jingli) < 1.2 * int(maxjingli):
                    style = Settings.styles["value"]   
                else:
                    style = Settings.styles["value.better"]
                
                if maxjingli == 0: 
                    pct = 0
                else:
                    pct = 100.0*float(jingli)/float(maxjingli)

                formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(jingli, maxjingli, pct)))
                formatted_list.append(("", " "))

                formatted_list.append((Settings.styles["title"], "【内力】"))
                if int(neili) < 0.6 * int(maxneili):
                    style = Settings.styles["value.worst"]
                elif int(neili) < 0.8 * int(maxneili):
                    style = Settings.styles["value.worse"]
                elif int(neili) < 1.2 * int(maxneili):
                    style = Settings.styles["value"]   
                else:
                    style = Settings.styles["value.better"]

                if maxneili == 0: 
                    pct = 0
                else:
                    pct = 100.0*float(neili)/float(maxneili)
                formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(neili, maxneili, pct)))
                formatted_list.append(("", " "))

                

                # a new-line
                formatted_list.append(("", "\n"))
                formatted_list.append((Settings.styles["title"], "【任务】"))
                formatted_list.append((Settings.styles["value"], "{}".format(self.jobmanager.currentJob)))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【状态】"))
                formatted_list.append((Settings.styles["value"], "{}".format(self.jobmanager.currentStatus)))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【持续】"))
                formatted_list.append((Settings.styles["value"], "{}".format("开启" if self.jobmanager.always else "关闭")))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【范围】"))
                formatted_list.append((Settings.styles["value"], "{}".format(self.jobmanager.activeJobs)))

                # a new-line
                formatted_list.append(("", "\n"))

                # line 3. GPS info
                formatted_list.append((Settings.styles["title"], "【惯导】"))
                if ins:
                    formatted_list.append((Settings.styles["value"], "正常"))
                    formatted_list.append(("", " "))
                    formatted_list.append((Settings.styles["title"], "【位置】"))
                    formatted_list.append((Settings.styles["value"], f"{loc['city']} {loc['name']}({loc['id']})"))
                else:
                    formatted_list.append((Settings.styles["value.worst"], "丢失"))
                    formatted_list.append(("", " "))
                    formatted_list.append((Settings.styles["title"], "【位置】"))
                    formatted_list.append((Settings.styles["value"], f"{self.session.getVariable('room')}"))

                if self.session.getVariable("is_busy", False):
                    formatted_list.append((Settings.styles["value.worse"], "【忙】"))
                else:
                    formatted_list.append((Settings.styles["value"], "【不忙】"))

                if self.session.getVariable("is_fighting", False):
                    formatted_list.append((Settings.styles["value.worse"], "【战斗】"))
                else:
                    formatted_list.append((Settings.styles["value"], "【空闲】"))

                if self.session.idletime > 60:
                    formatted_list.append((Settings.styles["value.worse"], f"【发呆{self.session.idletime // 60:.0f}分钟】"))
                else:
                    formatted_list.append((Settings.styles["value"], "【正常】"))

                formatted_list.append((Settings.styles["title"], "【BUFF】"))
                buff = self.session.getVariable("buff", list())
                #formatted_list.append((Settings.styles["value"], f"{' '.join(buff)}"))
                #formatted_list.append(to_formatted_text(ANSI(f"{' '.join(buff)}")))
                buff_styled = to_formatted_text(ANSI(f"{' '.join(buff)}"))
                formatted_list.extend(buff_styled)

                # a new-line
                formatted_list.append(("", "\n"))

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
                        if dir in DIRS_ABBR.keys():
                            dir = DIRS_ABBR[dir]
                        else:
                            m = re.match(r'(\S+)\((.+)\)', dir)
                            if m:
                                dir_cmd = m[2]

                        formatted_list.append((Settings.styles["link"], f"{dir}: {link.city} {link.name}({link.linkto})", functools.partial(go_direction, dir_cmd)))
                        formatted_list.append(("", " "))
                
                return formatted_list
        
            except Exception as e:
                self.session.error(f"状态窗口发生错误！错误信息为： {e}")
                return f"{e}"

.. _#mods: syscommand.html#modules
.. _pymud.Session: references.html#pymud.Session
.. _sessions: settings.html#sessions
.. _BaseObject: references.html#pymud.objects.BaseObject
.. _MatchObject: references.html#pymud.objects.MatchObject
.. _Alias: references.html#pymud.Alias
.. _SimpleAlias: references.html#pymud.SimpleAlias
.. _Trigger: references.html#pymud.Trigger
.. _SimpleTrigger: references.html#pymud.SimpleTrigger
.. _GMCPTrigger: references.html#pymud.GMCPTrigger
.. _Command: references.html#pymud.Command
.. _SimpleCommand: references.html#pymud.SimpleCommand
.. _Timer: references.html#pymud.Timer
.. _SimpleTimer: references.html#pymud.SimpleTimer
.. _插件: plugins.html