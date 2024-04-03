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

.. _#mods: syscommand.html#modules
.. _pymud.Session: references.html#pymud.Session
.. _sessions: settings.html#sessions
.. _插件: plugins.html