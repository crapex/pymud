[English Version] [中文版本](README.zh_CN.md)

# PYMUD - a MUD client written in Pure Python

## INTRODUCTION

+ Source Code: https://github.com/pkuxkx/pymud
+ Documentation (only Chinese Version currently): https://pymud.readthedocs.io/ 
+ Pypi Porject: https://pypi.org/project/pymud/
+ DeepWiki: https://deepwiki.com/crapex/pymmud/
+ QQ Group Number: 554672580

## FEATURES:

+ Native Python development, requiring no other third-party libraries except `prompt-toolkit <https://python-prompt-toolkit.readthedocs.io>` and its dependencies wcwidth, pygment, pyperclip.
+ Native Python asyncio-based communication protocol handling, supporting async/await syntax for direct use in scripts - you can choose between synchronous and asynchronous modes for your scripts.
+ Console-based full-screen UI design supporting mouse operations (touch screen operations on MobilePhone), with extremely low resource requirements - runs smoothly on a single-core 1GB RAM Linux VPS.
+ Split-screen display support, keeping the upper half static during rapid data scrolling to ensure you don't miss any information.
+ Solves 99% of Eastern-Asia characters alignment issue in chinese MUD (eg. PKUXKX, Peking University Knight-Errant), making character art clearly visible.
+ True multi-session support with command or mouse-based session switching.
+ Native support for multiple server-side encodings including GBK, BIG5, and UTF-8.
+ Supports NWAS, MTTS negotiation, and GMCP, MSDP, MSSP protocols.
+ Write once, run anywhere - if Python runs on the platform, PyMUD client can run on it.
+ All script syntax uses Python syntax, so if you know Python, you can write scripts without learning Lua or familiarizing yourself with various app usages.
+ Fully open-source code, making scripts easily debuggable with tools like Visual Studio Code - you can set breakpoints and inspect variables.
+ Python has extremely powerful text processing capabilities, making it perfect for text-based MUDs.
+ Python has an extremely rich ecosystem of third-party libraries - any library that supports Python can be used in PyMUD.
+ Multi-language support framework is in place, currently providing Chinese and English support, with ability to add other translated language versions.
+ Provides web-based client interface plugins for PKU Knight-Errant, allowing direct character operation on the interface with multi-end synchronized data/state display and fullme images (see QQ group files).
+ I'm still actively using PYMUD to play MUD games, so this client will continue to be updated :)

## Who is PyMUD suitable for
+ Those familiar with Python programming -> PyMUD is pure native Python development, support almost all Python features.
+ Those not very familiar with Python but wanting to learn -> perfect for learning Python while playing Knight-Errant and writing scripts with PyMUD
+ Those who feel current clients lack certain features -> if you have needs, I'll add them, it's that convenient
+ Those who want to build their own customized client -> PyMUD is fully open-source, and except for the UI framework, all code is written from scratch line by line, making it a perfect reference for your own design.

## UPDATE HISTORIES

### 0.22.0

+ BUG FIX: 'Beautify' use the previous impletation. Uniformly adding characeters on the right side.
+ BUF FIX: Fixed the alignment issue when using Eastern-Asia characters variable names in #var command. (Left part before the "=" symbole was not properly aligned)
+ BUF FIX: Fixed the issue where decoraors couldn't be used when create with multiple inheritance that inherit from both Command and IConfig. Now only one super() call is needed to resolve this.
+ Bug Fix: Fixed the issue where unload/reload operations sometimes didn't display successful unloading messages. Now errors during unloading can be properly reported.
+ Bug Fix: The 'remain_last_input' now properly retains command line input (thanks to @cantus for the code contribution).
+ New Feature: Added client settings split_ratio for setting split screen ratio. Default value is 0.5, meaning 50% split between upper and lower screens. Additionally, you can dynamically adjust the split ratio using Shift + ↑/↓ shortcuts (thanks to @cantus for the code contribution).
+ New Feature: The up arrow now prioritizes auto-completion when the cursor is at the far right position. If no auto-completion is available, it switches to history command navigation.
+ New Feature: ESC key can now clear all content in the command line (limited by terminal key handling, requires pressing ESC three times consecutively to take effect).
+ New Feature: Tab key now also has auto-completion functionality.
+ New Feature: Added info, warning, and error methods to the IConfigBase interface. Types inheriting from IConfig can now directly use self.info.
+ New Feature: @alias, @trigger, @timer, @gmcp, @exception decorators can now be directly applied to 'async def' asynchronous functions. Similarly, all types inheriting from BaseObject, including Trigger, Alias, Timer, GMCPTrigger, etc., can now have their onSuccess, onFailure callbacks directly assigned to asynchronous functions.
+ New Feature: In @exception output exception information, it will print the location of the function marked with @exception and the file where the exception occurred.
+ New Feature: Added a wait_triggers method to the Session type, which simplifies the code for handling waiting on multiple triggers.
+ Deprecation Notice: Since the @exception decorator can now be directly used with async functions, the @async_exception decorator will be removed in the next version.
