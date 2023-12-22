from pymud import PyMudApp, Session, Trigger
from functools import partial
import requests, json

# 插件唯一名称
PLUGIN_NAME    = "chathook"

# 插件有关描述信息
PLUGIN_DESC = {
    "VERSION" : "1.0.0",
    "AUTHOR"  : "newstart",
    "RELEASE_DATE"  : "2023-12-21",
    "DESCRIPTION" : "基于PYMUD的一个北侠webhook插件，将站点内聊天有关信息通过webhook发送到其他应用中"
}

TRIGGER_ID  = "plugins_chathook"
WEBHOOK_URL = "https://www.crapex.cc:5001/webapi/entry.cgi?api=SYNO.Chat.External&method=incoming&version=2&token=%2252ROQ304uBUz1KCVrlEfMoNRzR2dGiCKjUjP7kPXvuYPz6HX2XetfzK9yJk0Fpn0%22"

def ontri_chat(session, name, line, wildcards):
    data = {"payload": json.dumps({"text": line})}
    resp = requests.post(WEBHOOK_URL, data)
    info = resp.json()
    success = info.get("success")
    error   = info.get("error")
    if not success:
        session.info(f"Send message fail with error code: {error}", f"PLUGIN {PLUGIN_NAME}")

def PLUGIN_PYMUD_START(app: PyMudApp):
    "PYMUD自动读取并加载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动加载一次"
    app.set_status(f"插件{PLUGIN_NAME}已加载!")

def PLUGIN_SESSION_CREATE(session: Session):
    "在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次"
    tri = Trigger(session, id = TRIGGER_ID, patterns = r'^【.+】.+$', group = PLUGIN_NAME, onSuccess = partial(ontri_chat, session), keepEval = True, priority = 150)
    session.addTrigger(tri)
    session.info(f"插件{PLUGIN_NAME}已被本会话加载!!! 已成功向本会话中添加触发器 {TRIGGER_ID} !!!")

def PLUGIN_SESSION_DESTROY(session: Session):
    "在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。"
    session.delTrigger(session.tris[TRIGGER_ID])