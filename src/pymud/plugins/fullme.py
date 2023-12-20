from .. import Session, Trigger
import webbrowser


PLUGINS = {
    "name"      : "fullme",
    "version"   : "1.0.0",
    "author"    : "newstart",
}
"PLUGINS声明，应有name,version,author项"

TRIGGER_ID = "plugins_fullme_tri_webpage"

def ontri_webpage(name, line, wildcards):
    webbrowser.open(line)

def LOAD_PLUGINS(session: Session):
    "加载插件时自动调用的函数， session为加载插件的会话"
    tri = Trigger(session, id = TRIGGER_ID, patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', group = "sys", onSuccess = ontri_webpage)
    session.addTrigger(tri)

def UNLOAD_PLUGINS(session: Session):
    "卸载插件时自动调用的函数， session为卸载插件的会话"
    session.delTrigger(session.tris[TRIGGER_ID])