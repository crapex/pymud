# 需求、安装与运行

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

## windows下的安装与启动步骤示例

- 建议使用Windows Terminal作为shell，并使用PowerShell 7作为启动终端
- 使用pip安装pymud，shell中执行: pip install pymud
- 创建自己的脚本目录，如d:\pkuxkx： mkdir pkuxkx
- 进入自己的脚本目录，cd pkuxkx
- 启动运行pymud: python -m pymud

### 安装步骤
![install and run](_static/install_and_run.png)

### 启动后的界面
![pymud-ui](_static/ui_empty.png)

