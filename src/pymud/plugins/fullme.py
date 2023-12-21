from .. import PyMudApp, Session, Trigger
import webbrowser


# "PLUGINS声明name,version,author项, priority 为优先级，越小的越先加载 dependencies 指定依赖的其它插件"
PLUGIN_NAME    = "fullme_pkuxkx"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR  = "newstart"
RELEASE_DATE   = "2023-12-21"
PLUGIN_PRIORITY = 100
PLUGIN_DEPENCENCIES = []

TRIGGER_ID = "plugins_fullme_pkuxkx_tri_webpage"

def ontri_webpage(name, line, wildcards):
    webbrowser.open(line)

def PLUGIN_INIT(app: PyMudApp):
    "PYMUD自动读取并加载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动加载一次"
    pass

def PLUGIN_LOAD(session: Session):
    "在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次"
    tri = Trigger(session, id = TRIGGER_ID, patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', group = "sys", onSuccess = ontri_webpage)
    session.addTrigger(tri)

def PLUGIN_UNLOAD(session: Session):
    "在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。"
    session.delTrigger(session.tris[TRIGGER_ID])