from .. import Session, Trigger
import webbrowser

# 所有插件的定义在PLUGIN字典中
PLUGIN = {
    "name"      : "fullme",
    "version"   : "1.0.0",
    "author"    : "newstart",
    "priority"  : 100,              # temporary
    "dependencies" : []             # temporary
}
"PLUGINS声明name,version,author项, priority 为优先级，越小的越先加载 dependencies 指定依赖的其它插件"

TRIGGER_ID = "plugins_fullme_tri_webpage"

def ontri_webpage(name, line, wildcards):
    webbrowser.open(line)

def PLUGIN_LOAD(session: Session):
    "加载插件时自动调用的函数， session为加载插件的会话"
    tri = Trigger(session, id = TRIGGER_ID, patterns = r'^http://fullme.pkuxkx.net/robot.php.+$', group = "sys", onSuccess = ontri_webpage)
    session.addTrigger(tri)

def PLUGIN_UNLOAD(session: Session):
    "卸载插件时自动调用的函数， session为卸载插件的会话"
    session.delTrigger(session.tris[TRIGGER_ID])