# 需求、安装与运行

## 特点

PYMUD具有以下特点：
+ 原生纯Python开发，除prompt-toolkit及其依赖库（wcwidth, pygments, pyperclip）外，不需要其他第三方库支持
+ 使用原生asyncio库进行网络和事务处理，支持async/await语法的原生异步操作（PYMUD最大特色）。原生异步意味着可以支持很多其他异步库，例如可以使用aiohttp来进行网络页面访问而不产生阻塞等等:)
+ 基于控制台的全屏UI界面设计，支持鼠标操作（可触摸设备上支持触摸屏操作）
+ 支持分屏显示，在数据快速滚动的时候，上半屏保持不动，以确保不错过信息
+ 解决了99%情况下，北大侠客行中文对不齐，也就是看不清字符画的问题（因为我没有走遍所有地方，不敢保证100%）
+ 真正的支持多session会话，支持命令和鼠标切换会话
+ 原生支持多种服务器端编码方式，不论是GBK、BIG5、还是UTF-8
+ 支持NWAS、MTTS协商，支持GMCP、MSDP、MSSP协议, MXP待开发。
+ 一次脚本开发，多平台运行。只要能在该平台上运行Python，就可以运行PyMUD客户端
+ 脚本所有语法均采用Python原生语法，因此你只要会用Python，就可以自己写脚本，免去了再去学习lua、熟悉各类APP的使用的难处
+ Python拥有极为强大的文字处理能力，用于处理文本的MUD最为合适
+ Python拥有极为丰富的第三方库，能支持的第三方库，就能在PyMUD中支持
+ 我自己还在玩，所以本客户端会持续进行更新:)

## 环境需求

PYMUD是一个原生基于Python语言的MUD客户端，因此最基本的环境是Python环境而非操作系统环境。理论上，只要你的操作系统下可以运行Python，就可以运行PyMUD。另外，本客户端的UI设计是基于控制台的，因此也不需要有图形环境的支持。

- 操作系统需求：不限，能运行Python是必要条件。
- 版本需求：要求 >=3.7(已测试3.7.9,更旧的版本不确定能否使用，请自行尝试），32位/64位随意，但建议用64位版，可以支持4G以上的内存访问
- 支持库需求：prompt-toolkit 3.0（代码在 https://github.com/prompt-toolkit/python-prompt-toolkit ), 以及由prompt-toolkit所依赖的wcwidth、pygment、pyperclip
- prompt-toolkit 帮助页面： https://python-prompt-toolkit.readthedocs.io/en/master/

## 安装

- 安装Python，这个就不讲了。如果不会python语言可以学，如果不会任何编程语言，用这个客户端可能还是有点难度。所以假设用户是会python的。
- 安装PyMUD程序本体：可以直接使用pip安装或更新。所需的支持库会自动安装。

```
pip install pymud
pip install --upgrade pymud
```

## 运行

使用pip安装的pymud，可以通过标准模块调用语法：python -m pymud调用模块执行。
```
python -m pymud
```