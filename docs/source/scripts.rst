6 脚本
===============

6.1 所需知识基础
------------------

    在PYMUD中，一切皆脚本。所有操作均可以通过脚本实现，且绝大多数情况下，仅能通过脚本实现。
    由于PYMUD是一个基于控制台UI的MUD客户端，因此不能像 zmud/mushclient/mudlet 等客户端那样，在窗口中添加触发、别名等内容。
    而PYMUD是基于Python语言的原生实现，因此其实现脚本也是使用 Python 语言。
    PYMUD使用异步架构构建了整个程序的核心框架。当然，异步在脚本中不是必须的，它只是一种可选的实现方式而已。
    其他客户端都不像PYMUD一样原生完全支持async/await语法下的异步操作，这也是本客户端与其他所有客户端的最核心差异所在。

    要能在PYMUD中实现基本的脚本功能，需要掌握以下知识和概念：
        - Python基本语法与内置类型
        - 面向对象开发（OOP）的核心概念：封装、继承与多态。 百度百科: `面向对象程序设计 <https://baike.baidu.com/item/%E9%9D%A2%E5%90%91%E5%AF%B9%E8%B1%A1%E7%A8%8B%E5%BA%8F%E8%AE%BE%E8%AE%A1/24792>`_
        - 函数式编程的基本概念。百度百科: `函数式编程 <https://baike.baidu.com/item/%E5%87%BD%E6%95%B0%E5%BC%8F%E7%BC%96%E7%A8%8B>`_
        - 位置参数与关键字参数的基本概念
        - 基于Python的正则表达式。 Python文档: `正则表达式操作 <https://docs.python.org/zh-cn/3.10/library/re.html>`_

    要在PYMUD中使用脚本的高级功能，则还需要掌握以下内容：
        - asyncio 包的熟练使用，包括 async/await 语法、coroutine、Task概念与运用、Event/Future 的使用、事件循环等。 Python文档: `asyncio - 异步I/O <https://docs.python.org/zh-cn/3.10/library/asyncio.html>`_ 


6.2 一些概念与定义
------------------------

    PYMUD 支持的脚本，可以分布在模块、插件中。而模块按其特点，又可以分为主配置模块和子配置模块。
    模块的概念与 Python 中模块的概念基本相同。为有效区分PYMUD中的概念，在称谓前增加限定语标识。

    Python 模块:
        Python 模块(Module)，是一个 Python 文件，以 .py 结尾，包含了 Python 对象定义和Python语句。
        模块能够有逻辑地组织你的 Python 代码段。
        把相关的代码分配到一个模块里能让你的代码更好用，更易懂。
        模块能定义函数，类和变量，模块里也能包含可执行的代码。

    PYMUD模块:
        PYMUD模块本身是一个标准的Python模块。为了保证PYMUD应用的正常加载，模块文件应当放在当前目录下，可以以包的形式进行组织。PYMUD支持同时加载任意多个模块。

        根据PYMUD模块文件中是否包含名为 Configuration 的类型，将PYMUD模块区分为主配置模块和子配置模块两类。

        将PYMUD模块放在当前目录下之后，可以在命令行通过 ``#load xxx`` 指令加载名为xxx的模块(xxx为模块不包括扩展名.py的文件名，下同)，也可以将名称放在本地 pymud.cfg 中的 sessions_ 字典中以进行自动加载。

        当模块加载完毕之后，可以通过 ``session.modules['xxx']['module']`` 来访问该模块，可以通过 ``session.modules['xxx']['config']`` 来访问该模块中的 Configuration 类型实例。

        可以在命令行使用 `#mods`_ 命令列出本会话中已加载的所有模块清单。

        特别说明:
            区分PYMUD模块类型事实上并无绝对意义上的差异。也可以不通过 #load 加载子模块，而在主模块中直接通过 import xxx 加载该模块文件。

            但由于PYMUD实现限制， 在脚本修改之后， #reload 仅可以重新加载由 PYMUD 进行管理的模块，也即是通过 #load 命令 或者 Session.load_module 所加载的模块。
            因此可以使用PYMUD子配置模块来替代 import xxx 的使用。

    PYMUD子配置模块:
        PYMUD模块中不包含名为 Configuration 的类型的PYMUD模块即属于PYMUD子配置模块。
        加载子配置模块时，相当于在 Python 中调用 import xxx 指令。
        加载子配置模块后， ``session.modules['xxx']['config']`` 为 None

    PYMUD主配置模块:    
        模块中包含一个名为 Configuration 的类型的PYMUD模块。该类型构造函数接受一个 `pymud.Session`_ 对象作为唯一参数。
        这种模块在加载时，除了如子配置模块执行相同操作之外，还将自动创建一个 Configuration 类型的实例。

        以下是一个基本的主配置模块的示例：

        .. code:: Python
            
            # filename: mymainmodule.py
            from pymud import Session

            class Configuration:
                def __init__(self, session: Session):
                    self.session = session

                def unload(self):
                    pass
    
    PYMUD插件:
        PYMUD插件本身也是一个标准的 Python模块。插件应放在 pymud包目录的plugins子目录下，或者当前脚本目录的plugins子目录下，在PYMUD启动时自动加载。

        插件有相应的插件规范，详细参见 `插件`_


6.3 变量的使用
------------------------

6.3.1 变量概览
^^^^^^^^^^^^^^^^^^^^^

    从被管理的情况以及访问的范围划分，PYMUD可以使用的变量可以包括三大类：

        - Python 变量
            即在脚本中，自己定义的 Python 变量对象。此类对象不受 PYMUD 应用管理，当应用退出、会话关闭、脚本重新加载后，变量的结果由脚本代码自行设定，其定义、使用请按照 Python 的语法要求执行。
            Python 变量请参考 Python 语言有关文档，此处不再详细展开。

        - 单会话访问的变量
            即 Session 所属的 Variable 对象。此类对象包括了系统提供的部分变量，以及自行定义的变量。自行定义的变量在会话的所有脚本中都可以直接访问使用，并且可以通过 pymud.cfg 设置（默认已设置），在应用退出、会话关闭、脚本重新加载时，进行了持久化存储操作。
            Variable 对象，通过会话对象的属性字典实现和保存。PYMUD 规定，字典的键key作为变量名，必须为 str 类型，值 value 为变量的值，可以为任意 Python 类型，但仍建议采用可以持久化的类型。
        
        - 跨会话访问的变量
             即 PYMUD 所属的 Global 对象。此类对象与 Variable 对象区别为，这些对象可以在不同的会话之间进行访问，共享同一个变量对象。
             Global 对象通过 PyMudApp 对象的属性字典实现和保存。该对象不会被持久化，字典的键key作为变量名，必须为 str 类型。值可以为任何 Python 支持的类型。

    在设计自己脚本的时候，要根据上述不同类型变量的特点，选择合适的类型。
    个人建议，默认首选 Variable 类型，若有跨会话访问需求，请选择 Global 类型。对于某些函数或方法中的临时变量，再使用 Python 变量。

6.3.1 单会话访问的变量 (Variable) 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    PYMUD 应用系统本身提供了部分 Variable 变量，这些变量均用 % 开头。其中，部分为单个函数中使用的局部变量，部分为可全局访问使用的变量。 系统提供的 Variable 变量包括：

    - %1 ~ %9: 在触发器、别名的同步响应函数中，使用正则匹配的匹配组。 类似于 mushclient 与 zmud 中的 %1 ~ 9%。
    - %line: 在触发器、别名的同步响应函数中，匹配的行本身（经ANSI转义处置后的纯文本）。对于多行触发器， %line会返回多行。
    - %raw: 在触发器的同步响应函数中，匹配的行本身的原始代码（未经ANSI转义处置）。
    - %copy: 使用PYMUD复制功能（非系统复制功能）复制到当前剪贴板中的内容。

    变量可以使用 Session 对象提供的方法以及 Session 对象提供的快捷点访问器在脚本中进行操作。也可以使用 `#var <syscommand.html#var>`_ 命令来进行操作。
    
    创建变量/修改变量值的方法:
    可以使用 `setVariable <references.html#pymud.Session.setVariable>`_, `setVariables <references.html#pymud.Session.setVariables>`_, `vars <references.html#pymud.Session.vars>`_ 来创建变量（当变量不存在时）或修改变量值（当变量存在时）。
    可以使用 `getVariable <references.html#pymud.Session.getVariable>`_, `getVariables <references.html#pymud.Session.getVariables>`_, `vars <references.html#pymud.Session.vars>`_ 来读取变量值。
    可以使用 `delVariable <references.html#pymud.Session.delVariable>`_ 来移除一个变量。
    
    具体使用示例如下：

    .. code:: Python

        from pymud import Session, Trigger, SimpleAlias, SimpleTrigger
        
        class Configuration:
            def __init__(self, session: Session):
                self.session = session

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



.. _#mods: syscommand.html#modules
.. _pymud.Session: references.html#pymud.Session
.. _sessions: settings.html#sessions
.. _插件: plugins.html