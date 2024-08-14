import sys, os, json, platform, shutil, logging, argparse
from .pymud import main
from .settings import Settings

CFG_TEMPLATE = {
    "client": {
        "buffer_lines"      : 5000,                 # 保留缓冲行数

        "interval"          : 10,                   # 在自动执行中，两次命令输入中的间隔时间（ms）
        "auto_connect"      : True,                 # 创建会话后，是否自动连接
        "auto_reconnect"    : False,                # 在会话异常断开之后，是否自动重连
        "var_autosave"      : True,                 # 断开时自动保存会话变量
        "var_autoload"      : True,                 # 初始化时自动加载会话变量

        "echo_input"        : False,
        "beautify"          : True,                 # 专门为解决控制台下PKUXKX字符画对不齐的问题

        "status_display"    : 1,                    # 状态窗口显示情况设置，0-不显示，1-显示在下方，2-显示在右侧
        "status_height"     : 4,                    # 下侧状态栏的高度
        "status_width"      : 30,                   # 右侧状态栏的宽度

    },
    "sessions" : {
        "pkuxkx" : {
            "host" : "mud.pkuxkx.net",
            "port" : "8081",
            "encoding" : "utf8",
            "autologin" : "{0};{1}",
            "default_script": "examples",
            "chars" : {
                "display_title" : ["yourid", "yourpassword", ""],
            }
        }
    },
    "keys" : {
        "f3"    : "#ig",
        "f4"    : "#clear",
        "f11"   : "#close",
        "f12"   : "#exit",
    }
}

def init_pymud_env(args):
    print(f"欢迎使用PyMUD, 版本{Settings.__version__}. 使用PyMUD时, 建议建立一个新目录（任意位置），并将自己的脚本以及配置文件放到该目录下.")
    print("即将开始为首次运行初始化环境...")
    system = platform.system().lower()

    dir = args.dir
    if dir:
        print(f"你已经指定了创建脚本的目录为 {args.dir}, 将不再检测操作系统")

    else:
        if system == "windows":
            dir = input("检测到当前系统为Windows, 请指定游戏脚本的目录（若目录不存在会自动创建），直接回车表示使用默认值[d:\pkuxkx]:")
            if not dir: dir = "d:\\pkuxkx"

        elif system == "linux":
            dir = input("检测到当前系统为Linux, 请指定游戏脚本的目录（若目录不存在会自动创建），直接回车表示使用默认值[~/pkuxkx]:")
            if not dir: dir = "~/pkuxkx"

        elif system == "darwin":
            dir = input("检测到当前系统为MacOS, 请指定游戏脚本的目录（若目录不存在会自动创建），直接回车表示使用默认值[~/pkuxkx]:")
            if not dir: dir = "~/pkuxkx"

        else:
            print(f"当前系统不是Windows、Linux或MacOS, 无法通过init来进行配置, 请手动配置. 默认配置即将推出")


    if not os.path.exists(dir):
        print(f'检测到给定目录 {dir} 不存在，正在创建目录...', end = "")
        os.mkdir(dir)
        os.chdir(dir)
        print(f'完成!')

    if os.path.exists('pymud.cfg'):
        print(f'检测到脚本目录下已存在pymud.cfg文件，将直接使用此文件进入PyMUD...')
    else:
        print(f'检测到脚本目录下不存在pymud.cfg文件，将使用默认内容创建该配置文件...')
        with open('pymud.cfg', mode = 'x') as fp:
            fp.writelines(json.dumps(CFG_TEMPLATE, indent = 4))

    if not os.path.exists('examples.py'):
        from pymud import pkuxkx
        module_dir = pkuxkx.__file__
        shutil.copyfile(module_dir, 'examples.py')
        print(f'已将样例脚本拷贝至脚本目录，并加入默认配置文件')

    print(f"后续可自行修改 {dir} 目录下的 pymud.cfg 文件以进行配置。")
    if system == "windows":
        print(f"后续运行PyMUD， 请在 {dir} 目录下键入命令： python -m pymud")
    else:
        print(f"后续运行PyMUD， 请在 {dir} 目录下键入命令： python3 -m pymud")

    input('所有内容已初始化完毕, 请按回车进入PyMUD.')

    module_entry(args)

def module_entry(args):
    if args.debug:
        logging.basicConfig(level = logging.NOTSET,
            format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt = '%m-%d %H:%M',
            filename = args.logfile,
            filemode = 'a' if args.filemode else 'w',
            encoding = "utf-8"
            )
        
    else:
        logging.basicConfig(level = logging.NOTSET,
            format = '%(asctime)s %(name)-12s: %(message)s',
            datefmt = '%m-%d %H:%M',
            handlers = [logging.NullHandler()],
            )
        
    cfg = "pymud.cfg"
    if os.path.exists(cfg):
        with open(cfg, "r", encoding="utf8", errors="ignore") as fp:
            cfg_data = json.load(fp)
            main(cfg_data)
    else:
        main()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog = "pymud", usage = "python -m pymud [-h] [-d] [-l logfile] [-a] {init} ...", description = "PyMUD命令行参数帮助")
    subparsers = parser.add_subparsers(help = 'init用于初始化运行环境')

    par_init = subparsers.add_parser('init', usage = "python -m pymud init [-h] [-d dir]", description = '初始化pymud运行环境, 包括建立脚本目录, 创建默认配置文件, 创建样例脚本等.')
    par_init.add_argument('-d', '--dir', dest = 'dir', metavar = 'dir', type = str, default = '', help = '指定构建脚本目录的名称, 不指定时会根据操作系统选择不同默认值')
    par_init.set_defaults(func = init_pymud_env)

    parser.add_argument('-d', '--debug', dest = 'debug', action = 'store_true', default = False, help = '指定以调试模式进入PyMUD。此时，系统log等级将设置为logging.NOTSET, 所有log数据均会被记录。默认不启用。')
    parser.add_argument('-l', '--logfile', dest = 'logfile', metavar = 'logfile', default = 'pymud.log', help = '指定调试模式下记录文件名，不指定时，默认为当前目录下的pymud.log')
    parser.add_argument('-a', '--appendmode', dest = 'filemode', action = 'store_true', default = True, help = '指定log文件的访问模式是否为append尾部添加模式，默认为True。当为False时，使用w模式，即每次运行清空之前记录')

    args=parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        module_entry(args)