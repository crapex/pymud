7 插件
===============

    插件是为了方便大家共享，将一个或多个通用功能到模块按照一定的规范所编写的特殊脚本。
    插件需要放在当前目录下的 plugins 目录中，PyMUD在启动时会自动从该文件夹下搜索符合插件规范的文件并加载为插件。

    按照插件规范，插件文件中必须要存在以下几个部分：

    - 插件名称, 在文件中以 str 类型赋值给 PLUGIN_NAME 变量，如： PLUGIN_NAME    = "your-plugin-name"
    - 插件有关描述，在文件中以 dict 类型赋值给 PLUGIN_DESC 变量，字典内应包含 "VERSION" (版本), "AUTHOR" (作者), "RELEASE_DATE" (发布日期), "DESCRIPTION" （插件描述）四个字段。如：
    - 一个在应用启动时读取到本插件是调用的函数，应为 `def PLUGIN_PYMUD_START(app: PyMudApp):` 这种形式，其中 app 为传递的应用程序实例
    - 一个在每一个会话创建时调用的函数，应为 `def PLUGIN_SESSION_CREATE(session: Session):` 这种形式，其中 session 为传递的创建的会话实例
    - 一个在某一个会话被销毁（关闭）时调用的函数，应为 `def PLUGIN_SESSION_DESTROY(session: Session):` 这种形式，其中 session 为传递的销毁的会话实例

    下面给出一个我使用的用于与群晖Synology Chat进行双向通信的插件，供参考插件制作：

    .. code:: Python

        from pymud import Session, Alias, Command
        from functools import partial
        import re, json, asyncio, urllib.parse, traceback, time, platform
        from datetime import datetime
        from aiohttp import web, ClientSession
        from aiohttp.web_request import Request

        # 插件唯一名称
        PLUGIN_NAME    = "chathook"

        # 插件有关描述信息
        PLUGIN_DESC = {
            "VERSION" : "1.0.1",
            "AUTHOR"  : "newstart",
            "RELEASE_DATE"  : "2024-02-14",
            "DESCRIPTION" : "使用群晖Synology Chat的webhook插件，可以用于与游戏进行交互"
        }

        WEBHOOK_URL = "https://Please.Change.The.URL.To.Your.Own.Address"

        class ChatHook:
            HOOK_COMMANDS = {
                "get": "hookget",
            }

            def __init__(self, app) -> None:
                self.app = app
                self.app.set_globals("hooked", False)
                app.globals.hook = self
                self.site = None

            def start_webhook(self):
                try:
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

                except Exception as e:
                    self.app.set_status(f"插件CHATHOOK的WEBHOOK监听服务关闭时出现错误: {e}")

            async def start_webserver(self):
                try:
                    self.webapp = web.Application()
                    self.webapp.add_routes([web.post('/', self.handle_post), web.get('/', self.handle_get)])
                    self.runner = web.AppRunner(self.webapp)
                    await self.runner.setup()
                    self.site = web.TCPSite(self.runner, '0.0.0.0', 8000)
                    await self.site.start()
                    
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
                        self.app.set_globals("hooked", False)
                        self.app.set_status("插件CHATHOOK的WEBHOOK已关闭8000端口的监听.")
                        if self.app.current_session:
                            self.app.current_session.info("插件CHATHOOK的WEBHOOK已关闭8000端口的监听.", "CHATHOOK")
                except Exception as e:
                    self.app.set_status(f"插件CHATHOOK的WEBHOOK监听服务关闭时出现错误: {e}")

            async def execute_session_command(self, name, command, from_user):
                if name in self.app.sessions.keys():
                    await self.app.sessions[name].exec_command_async(command)
                else:
                    self.app.set_status(f"不存在名称为 {name} 的会话，请重试！")
                    await self.asyncSendMessage(f"【错误】发送命令执行错误：不存在名称为 {name} 的会话，请重试！", user = from_user)

            async def execute_hook_command(self, name, command, param, from_user):
                if name in self.app.sessions.keys():
                    if command == "lock":    # 锁定指定会话，后续发送消息时，可以不声明会话
                        self.app.set_globals(f"session_lock_{from_user}", name)
                        self.app.sessions[name].info(f"已将用户 {from_user} 的WEBHOOK命令锁定到本会话", "WEBHOOK")
                        await self.asyncSendMessage(f"【状态】成功将本用户的WEBHOOK命令消息锁定到会话 {name} .", user = from_user)
                    elif command == "unlock":
                        self.app.set_globals(f"session_lock_{from_user}", None)
                        self.app.sessions[name].info(f"已将用户 {from_user} 的WEBHOOK命令从本会话解锁", "WEBHOOK")
                        await self.asyncSendMessage(f"【状态】成功将本用户的WEBHOOK命令消息从本会话解锁 {name} .", user = from_user)
                    else:
                        cmd = self.HOOK_COMMANDS.get(command, command)
                        command = f"{cmd} {param}"
                        cmd_hook = self.app.sessions[name].cmds["cmd_hook"]
                        #await self.app.sessions[name].exec_command_async(command)
                        await self.app.sessions[name].create_task(cmd_hook.execute(command, from_user = from_user))

                elif not name:
                    if command == "get":
                        alive_sessions, dead_sessions = list(), list()
                        for key, session in self.app.sessions.items():
                            if isinstance(session, Session):
                                if session.connected:
                                    alive_sessions.append(key)
                                else:
                                    dead_sessions.append(key)
                        
                        alive_session_msg = f'已连接会话包括：{",".join(alive_sessions)}' if len(alive_sessions) > 0 else "没有已连接会话"
                        dead_session_msg  = f'未连接会话包括：{",".join(dead_sessions)}' if len(dead_sessions) > 0 else "没有未连接会话"
                        lock = self.app.get_globals(f"session_lock_{from_user}", None)
                        lock_msg = f'已锁定会话{lock}' if lock else '未锁定会话'
                        send_msg = ", ".join((alive_session_msg, dead_session_msg, lock_msg)) + "。"

                        await self.asyncSendMessage(send_msg, user = from_user)

                else:
                    self.app.set_status(f"不存在名称为 {name} 的会话，请重试！")
                    await self.asyncSendMessage(f"【错误】发送命令执行错误：不存在名称为 {name} 的会话，请重试！", user = from_user)

            async def handle_post(self, request: Request):
                try:
                    text = await request.text()
                    data = urllib.parse.parse_qs(text)
                    from_username = data['username'][0]
                    from_userid   = data['user_id'][0]
                    message       = data['text'][0]

                    # 命令特性处置
                    if ":" in message:
                        msg = message.split(":")
                        if len(msg) == 2:
                            session_lock = self.app.get_globals(f"session_lock_{from_userid}", None)
                            if session_lock and session_lock in self.app.sessions.keys():
                                self.app.sessions[session_lock].info(f"收到来自 {from_username}({from_userid}) 发送的消息: {message}", "CHATHOOK")
                                await self.execute_hook_command(session_lock, msg[0], msg[1], from_userid)
                            elif msg[0] in self.app.sessions.keys():
                                self.app.sessions[msg[0]].info(f"收到来自 {from_username}({from_userid}) 发送的消息: {message}", "CHATHOOK")
                                await self.execute_session_command(msg[0], msg[1], from_userid)

                        elif len(msg) == 3:
                            name, op, param = msg[0], msg[1], msg[2]
                            if name in self.app.sessions.keys():
                                self.app.sessions[name].info(f"收到来自 {from_username}({from_userid}) 发送的消息: {message}", "CHATHOOK")
                            await self.execute_hook_command(name, op, param, from_userid)

                    else:
                        session_lock = self.app.get_globals(f"session_lock_{from_userid}", None)
                        if session_lock and session_lock in self.app.sessions.keys():
                            self.app.sessions[session_lock].info(f"收到来自 {from_username}({from_userid}) 发送的消息: {message}", "CHATHOOK")
                            await self.execute_session_command(session_lock, message, from_userid)
                        else:
                            await self.asyncSendMessage(f"【错误】既没有锁定会话，也没有指定会话，当前消息「{message}」无法执行。", user = from_userid)

                    return web.json_response({'success': True})
                
                except json.JSONDecodeError as e:
                    return web.Response(text=str(e), status=400)
                
                except Exception as e2:
                    self.app.set_status(f"post发生错误： {e2}")

            async def handle_get(self, request):
                return web.Response(text="GET method not supported.", status=501)
            
            def sendMessage(self, text, user = 5):
                asyncio.ensure_future(self.asyncSendMessage(text, user = user))

            def sendImage(self, imagelink, text = "图像测试", user = 5):
                asyncio.ensure_future(self.asyncSendMessage(text, imagelink, user))

            def sendFullme(self, session, link, extra_text = "FULLME", user = 5):
                asyncio.ensure_future(self.loadAndSendFullme(session, link, extra_text, user))

            async def loadAndSendFullme(self, session, link, extra_text, user = 5):
                try:
                    fmadress = link.split("robot.php?filename=")[-1]
                    url = f"http://fullme.pkuxkx.net/robot.php?filename={fmadress}"
                    imgs = list()

                    client = ClientSession()
                    for i in range(0, 3):
                        async with client.get(url) as response:
                            if response.status != 200:
                                continue

                            text = await response.text()
                            matches = re.search(r'src="\.([^"]+\.jpg)"', text)
                            if not matches:
                                continue

                            img_url = "http://fullme.pkuxkx.net" + matches.group(1)
                            # imgs.append(img_url)

                            msg = f"来自会话[{session.name}] 的 {extra_text} 消息："
                            await self.asyncSendMessage(msg, img_url, user)
                            await asyncio.sleep(0.5)

                    await client.close()

                except Exception as e:
                    session.error(f"执行fullme的HOOK挂接时出现错误，信息为： {e}")
                    session.error(f"异常追踪为： {traceback.format_exc()}")

            async def asyncSendMessage(self, text, file_url = None, user = 5):
                try:
                    text = f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: {text}'
                    if file_url:
                        data = {"payload": json.dumps({"text": text, "file_url": file_url, "user_ids": [user]})}
                    else:
                        data = {"payload": json.dumps({"text": text, "user_ids": [user]})}

                    async with ClientSession() as client:
                        async with client.post(WEBHOOK_URL, data = data) as response:
                            info = await response.json()
                            if info.get("success"):
                                self.app.set_status(f"消息成功发送到用户 {user}.")
                            else:
                                self.app.set_status(f"消息没有成功发送到用户 {user}. 错误为 {info.get('error')}")

                except Exception as e:
                    self.app.set_status(f"执行fullme的HOOK挂接时出现错误，信息为： {e}")
                    #session.error(f"异常追踪为： {traceback.format_exc()}")
                    if self.app.current_session:
                        self.app.current_session.error(f"执行fullme的HOOK挂接时出现错误，信息为： {e}")
                        self.app.current_session.error(f"异常追踪为： {traceback.format_exc()}")
                    
        class CmdHookMessageHandler(Command):
            def __init__(self, session, *args, **kwargs):
                super().__init__(session, r"^(hookget)(?:\s+(\S.+))$", *args, **kwargs)

            def get_status(self) -> str:
                msg_lines = list()
                msg_lines.append("")
                fullme = int(self.session.getVariable('%fullme', 0))
                delta = time.time() - fullme
                msg_lines.append(f"FULLME时间: {int(delta // 60)}分钟")
                exp, pot, food, water = self.session.getVariables(["combat_exp", "potential", "food", "water"])
                busy, fight = self.session.getVariables(["is_busy", "is_fighting"])
                msg_lines.append(f"实战经验: {exp}, 潜能: {pot}")
                msg_lines.append(f"食物: {food}, 饮水: {water} {'【忙】' if busy else '【不忙】'} {'【战斗中】' if fight else '【空闲中】'}")
                jing, eff_jing, max_jing = self.session.getVariables(["jing", "eff_jing", "max_jing"])
                msg_lines.append(f"精神: {jing} / {eff_jing} / {max_jing}")
                qi, eff_qi, max_qi = self.session.getVariables(["qi", "eff_qi", "max_qi"])
                msg_lines.append(f"气血: {qi} / {eff_qi} / {max_qi}")
                jingli, max_jingli, neili, max_neili = self.session.getVariables(["jingli", "max_jingli", "neili", "max_neili"])
                msg_lines.append(f"精力: {jingli} / {max_jingli}, 内力: {neili} / {max_neili}")
                loc, ins_loc = self.session.getVariables(["room", "ins_loc"])
                if ins_loc:
                    msg_lines.append(f"当前位置(惯导): {ins_loc['city']} {ins_loc['name']} {ins_loc['id']}")
                else:
                    msg_lines.append(f"当前位置(无惯导): {loc}")
                jobManager = self.session.cmds["jobmanager"]
                msg_lines.append(f"当前任务: {jobManager.currentJob}, 当前状态: {jobManager.currentStatus}")
                return "\n".join(msg_lines)

            async def get_skills(self) -> str:
                await asyncio.wait([self.create_task(self.session.exec_command_async("skills")),], timeout = 3)
                msg_lines = list()
                msg_lines.append("")
                skills = self.session.getVariable("skills", dict())
                for key, value in skills.items():
                    skill_line = f"{value[2]}({key}): {value[0]} / {value[1]}"
                    msg_lines.append(skill_line)

                return "\n".join(msg_lines)

            async def execute(self, cmd, *args, **kwargs):
                try:
                    from_user = kwargs.get("from_user", 5)
                    m = re.match(self.patterns, cmd)
                    if m:
                        command, param = m[1], m[2]
                        if command == "hookget":
                            get_func = getattr(self, f"get_{param}")
                            if asyncio.iscoroutine(get_func) or asyncio.iscoroutinefunction(get_func):
                                id, name = self.session.getVariables(["id", "name"])
                                result = await get_func()
                                msg = f"来自{name}({id})的信息：{result}"
                                self.session.globals.hook.sendMessage(msg, from_user)
                            elif callable(get_func):
                                id, name = self.session.getVariables(["id", "name"])
                                msg = f"来自{name}({id})的信息：{get_func()}"
                                self.session.globals.hook.sendMessage(msg, from_user)
                            else:
                                msg = f"CHATHOOK不支持获取{param}参数"
                                self.session.globals.hook.sendMessage(msg, from_user)
                        else:
                            msg = f"CHATHOOK不支持{command}命令"
                            self.session.globals.hook.sendMessage(msg, from_user)

                except Exception as e:
                    self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
                    self.error(f"异常追踪为： {traceback.format_exc()}")

        def sendMessageToHook(session, name, line, wildcards):
            msg = f"来自会话[{session.name}]的消息： {wildcards[0]}"
            session.globals.hook.sendMessage(msg)

        def PLUGIN_PYMUD_START(app):
            "PYMUD自动读取并加载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动加载一次"
            chathook = ChatHook(app)
            app.set_status(f"插件{PLUGIN_NAME}已加载!")

        def PLUGIN_SESSION_CREATE(session: Session):
            "在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次"
            # 对象在创建时会自动加入会话，因此不再需要 session.addXXX 方法调用了
            Alias(session, "^starthook$",  id = "ali_starthook", onSuccess = lambda name, line, wildcards: session.globals.hook.start_webhook())
            Alias(session, "^stophook$",   id = "ali_stophook",  onSuccess = lambda name, line, wildcards: session.globals.hook.stop_webhook())
            Alias(session, r"^send\s(.+)$", id = "ali_sendmsg", onSuccess = partial(sendMessageToHook, session))
            CmdHookMessageHandler(session, id = "cmd_hook")

        def PLUGIN_SESSION_DESTROY(session: Session):
            "在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。"
            pass