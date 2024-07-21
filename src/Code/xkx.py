"用于处理PKUXKX的环境"
import os
import re, asyncio, random, math, webbrowser, traceback, json
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from collections import namedtuple
from pymud import Alias, Trigger, Command, SimpleCommand
from pymud import Settings,GMCPTrigger

import json
import threading

#from statusWindow import statusWindow


class Configuration:
    def __init__(self, session) -> None:
        self.session = session

        self._triggers = {}
        self._commands = {}
        self._aliases  = {}
        self._timers   = {}

        self.load_modules()

        self.setupMain()
        self.setupGMCP()
        
        session.status_maker = self.status_window

    def load_modules(self):
        mods = []
        root_dir = 'D:\pkuxkx\script'

        dir = os.path.join(root_dir,"misc")
        for file in os.listdir(dir):
            if file.endswith(".py") and (not file.startswith("__")):
                mods.append(f"script.misc.{file[:-3]}")

        dir = os.path.join(root_dir,"commands")
        for file in os.listdir(dir):
            if file.endswith(".py") and (not file.startswith("__")):
                mods.append(f"script.commands.{file[:-3]}")       

        mods.append("script.Main")
        mods.append("script.GMCP")
        mods.append("script.statusWindow")

        self.session.load_module(mods)

    def setupMain(self):
        self.Main = self.session.modules["script.Main"]["module"].Main(self.session)        
        
        self.session.addAliases(self.Main._aliases)
        self.session.addTriggers(self.Main._triggers)
        self.session.addTimers(self.Main._timers)
        self.session.addCommands(self.Main._commands)

    def setupGMCP(self):
        self.GMCP = self.session.modules["script.GMCP"]["module"].GMCP(self.session)
        self.session.addGMCPs(self.GMCP._gmcps)

    #状态栏
    def status_window(self):        
        return self.session.modules["script.statusWindow"]["module"].statusWindow(self.session)       