[English Version] [中文版本](README.md)

# PYMUD - a MUD client written in Pure Python

## INTRODUCTION

+ Website: https://www.pymud.cn
+ Documentation (only Chinese Version currently): https://www.pymud.cn/doc/
+ Discussion Forum: https://bbs.pymud.cn
+ Source Code: https://github.com/pkuxkx/pymud
+ Pypi Porject: https://pypi.org/project/pymud/
+ DeepWiki: https://deepwiki.com/crapex/pymmud/
+ QQ Group Number: 554672580

## FEATURES:

+ Native Python development, requiring no other third-party libraries except `prompt-toolkit <https://python-prompt-toolkit.readthedocs.io>` and its dependencies wcwidth, pygments, pyperclip.
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

### 0.22.5 (2026-05-02)

+ New Feature: Added `invalidate` method to Session class. When called, it only triggers `PyMudApp.invalidate()` for refresh if the current session is the active session.
+ Note: For `session.application.invalidate()` calls in personal scripts, it is recommended to change to `session.invalidate()`. Because session refresh checks for foreground status, while application refresh forces a refresh.
+ New Feature: Added lazy mode. When lazy mode is enabled, even `PyMudApp.invalidate()` calls will not trigger display refresh. The system only refreshes when switching sessions or on a 1-second timer. This mode can be toggled with the F4 hotkey. In lazy mode, "LAZY" is displayed on the right side of the bottom status bar. This mode can be used to reduce CPU usage when running in the background.
+ New Feature: Added verbatim mode. When verbatim mode is enabled, all commands entered in the command line are sent directly to the server without any parsing. This mode can be toggled with the F3 hotkey. In verbatim mode, "VERB" is displayed on the right side of the bottom status bar.
+ New Feature: Added a non-parsing prefix "/". When this prefix is used at the beginning of a command line, all subsequent commands are sent directly to the server without any parsing. This prefix can be overridden via `noparser` in pymud.cfg. This prefix is equivalent to temporarily using verbatim mode.
+ New Feature: Added "cmd_prefix" setting. When configured, command echo in the window or log records will display commands with this prefix. Default is empty, can be overridden via `cmd_prefix` in pymud.cfg. Also adjusted command display style to match the default info style.
+ Improvement: After executing commands like #var, temporary lists created are deleted using `del` to speed up memory release.
+ Improvement: When a session is closed, related objects in the session are cleared synchronously using `del`, and garbage collection is triggered programmatically (however, testing showed no significant effect on memory usage).

### 0.22.4 (2026-02-24)

+ New Features:
    - When a device has multiple network adapters and IP addresses, you can specify which local IP to use for the connection.
    - Added direct SOCKS5 proxy connection support, including both no-auth proxies (for example, a SOCKS5 proxy created by `ssh -D`) and username/password authenticated proxies.
    - The two capabilities above are implemented through the new `network` configuration dictionary, and can also be specified directly in `#session` and `#connect`. Usage is shown below.
+ Bug Fixes:
    - Fixed incorrect display of function name, file name, and line number in error location output.
    - Fixed a bug in memory monitor startup logic that could prevent memory monitoring from working.
+ Other Changes:
    - Further cleaned up all code style issues reported by basedpyright and adjusted code to better align with the coding standard.
    - The default value of `remain_last_input` is now `True`.
    - Confirmed the new `SessionBuffer` implementation is stable and removed the old implementation.
    - Removed all unnecessary imports.
    - When all sessions are closed, the bottom status window is now cleared.

#### Multi-IP / SOCKS5 proxy connection usage

+ First, add a `network` field in `pymud.cfg` as shown below (remove comments if you copy it directly):

    ```jsonc
    {
        // Put this inside the root object
        "network" : {
            "ipv6": false,              // Whether to enable IPv6, accepts true|false, default false. This only affects auto mode (whether IPv6 addresses are auto-discovered).
            "local_addr": "auto",       // Local bind IP, accepts auto|preset. Default auto (discover IPs from all local network devices). When set to preset, IPs in ip_list will be used.
            "ip_list": [                // Required when local_addr is preset; used to specify which IP can be selected for connection.
                "192.168.1.100",
                "192.168.2.100",
            ],
            "proxy": true,              // Whether to enable proxy, accepts true|false, default false.
            "proxies": {                // SOCKS5 proxy list; supports multiple proxies, including no-auth and username/password-auth proxies.
                "proxy1": "socks5://192.168.6.66:1080",                         // no-auth proxy identified as proxy1
                "proxy2": "socks5://user:password@yoursock5proxy.site:1080",    // username/password proxy identified as proxy2
            }
        }
    }
    ```

+ After configuration is completed, when PyMUD starts, each character under the World menu will have a submenu. IP entries and proxy entries are added as submenu items. You can connect either from the character menu itself or from those submenu items.
+ Clicking the character menu itself still uses the system default network interface.
+ Clicking an IP item in the character submenu binds to that specific local IP. For example, if one machine has two NICs (e.g., Telecom and Unicom), even when the OS default route uses NIC-1, you can still connect via NIC-2 by binding its IP.
+ Clicking a proxy item in the character submenu connects through that proxy. For example, if `proxy1` is configured, clicking `proxy1` uses that proxy for the connection.
+ You can also specify IP/proxy in `#session` / `#connect`. Syntax is the same for both: append `>>` followed by the selector at the end. Note: there must be no space after `>>`.
    + `#session pkuxkx.newstart >>#2`             # use the 2nd IP (index starts from 1) from `ip_list` (when `local_addr=preset`) or from the auto-discovered IP list shown in menu
    + `#session pkuxkx.newstart >>@proxy1`        # `@` means using proxy `proxy1` defined in `proxies`
    + `#con >>>#1`                                # after a session is disconnected (for example with `#dis`), reconnect temporarily using the 1st IP
    + `#con >>socks5://192.168.6.67:1080`         # you can also directly specify a new SOCKS5 proxy in command (IP can only be selected by index, not by manual IP literal)
+ `#con` also supports three greater-than signs `>>>`. The difference is: with `>>`, the specified network setting becomes the new default for the current session; with `>>>`, it is only used this time and does not overwrite the session default.

### 0.22.3 (2026-01-18)

+ Bug Fixes:
    - Removed unnecessary imports from various code files. Verified to work normally with Python 3.8.
    - Fixed an issue in the getVariable method where non-alphabetic characters would cause the variable value to return None.
    - Fixed a bug in #var nested variable support. Previously, if a digit was used as a dictionary key, it would be incorrectly identified as a list and return None.
+ Feature Improvements:
    - Updated #mem diff to compare against the memory usage at initial startup, rather than against the previous execution.
+ Other Changes:
    - Updated the help documentation for #close to include a description of its parameters, specifically support for the -f and session_name arguments (previously supported but undocumented).
    - Refactored multiple instances of non-standard syntax and replaced deprecated code.

### 0.22.2 (2026-01-11)

+ NEW FEATURE: You can specify "auto_chars" in the .cfg file to define which sessions are automatically opened when starting pymud.
+ BUG FIX: Fixed an issue where the enabled property of GMCPTrigger was not taking effect.
+ BUG FIX: Fixed an issue where timers that were previously enabled would not fire after the session was disconnected and reconnected.
+ BUG FIX: Fixed a potential exception when adding or removing system clock callbacks.
+ BUG FIX: Fixed an issue where an exception raised inside a newly added system clock callback could cause the system clock to stop.
+ IMPROVEMENT: Optimized the implementation of SessionBuffer to use a ring buffer plus a cached buffer in a double‑buffered design, reducing the number of memory allocations and clears during runtime.
+ NEW FEATURE: #var now supports displaying nested variables, including list, dict and other nested types. See the forum for details.
+ NEW FEATURE: Added #mem/#memory commands to support memory monitoring, and a -m option at startup to enable memory monitoring immediately. See #help memory or the forum for details.
+ OTHER: The help website opened by the F1 shortcut now points to the official documentation page at https://www.pymud.cn/doc/


### 0.22.1

+ BUG FIX: Fixed the issue where script errors would not be properly displayed.

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
