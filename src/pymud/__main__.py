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

# def simulate(args):
    
#     prlist = args.pr
#     print('指定了{0}个PR： {1}，各仿真{2}次。{3}'.format(len(prlist), prlist, args.times, '仿真过程将记录到文件' if args.log else '仿真过程不记录'))
    
#     for pr in prlist:
#         # 若PR结果文件夹不存在，则创建文件夹
#         pr_res_dir = PATH + 'results/' + pr + '/'
#         if not Path(pr_res_dir).is_dir():
#             os.makedirs(pr_res_dir)

#         if args.log:
#             logFile = PATH + 'results/' + pr + '/' + pr.lower() + '.log'
#             logger  = Logger(logFile)

#         print('指定了PR：', pr)
#         print('即将运行', args.times, '次仿真')
    
#         sim = MonteCarlo('projs.xlsx', args.detailed)
#         sim.simulate(pr, args.times)
#         print('{0} 次选定 {1} 优先规则的仿真结束.'.format(args.times, pr))

#         if logger:
#             logger.reset()

#         gc.collect()

#     print('全部PR: {0} 仿真运行结束。'.format(prlist))

# def analyze(args):
#     if args.all:
#         print('分析所有PR结果')
#     else:
#         print('分析以下PR的结果：', *args.prlist)
    
#     print('即将运行分析，并将结果输出到：', args.file)

#     # 增加判断项目拖期情况部分
#     projsTaskIndex = pd.DataFrame(None, columns = ['start', 'stop', 'deadline'], dtype=int)
#     templates = TemplateProjects(PATH + 'projs.xlsx')   # loading template project
#     start = 0
#     simulate_start = date(2022,1,1)
#     for projInfo in PROJ_INFO:
#         proj_id = projInfo[0]
#         proj_type = projInfo[1]
#         proj_taskCnt = templates.getTemplate(proj_type).taskCount
#         proj_start = start
#         proj_stop  = proj_start + proj_taskCnt
#         proj_deadline = (projInfo[3] - simulate_start).days
#         projsTaskIndex.loc[proj_id] = (proj_start, proj_stop, proj_deadline)

#         start = proj_stop

#     _daysWork = [0,0,8,8,8,8,8] * 52
#     _daysWork.append(0)
#     daysWork = np.array(_daysWork).reshape(365, 1)
#     totalResCnt = RESOURCES.sum()

#     if args.dir == '':
#         result_path = PATH + 'results/'
#     else:
#         result_path = args.dir

#     if args.all:
#         pr_list = os.listdir(result_path)
#     else:
#         pr_list = args.prlist

#     output_file = PATH + args.file

#     writer = pd.ExcelWriter(output_file)

#     for pr in pr_list:
#         path = result_path + pr + '/'

#         if not os.path.isdir(path):
#             continue

#         files = os.listdir(path)
#         resourceResult = pd.DataFrame(data=None, columns=['total', 'total-me', 'total-ee', 'total-oe', 'total-ex', 'me-spare', 'me-overtime', 'me-sum', 'ee-spare', 'ee-overtime', 'ee-sum', 'oe-spare', 'oe-overtime', 'oe-sum', 'total-spare', 'total-overtime', 'total-sum', 'outofdateprojs', 'outofdate'], dtype=float)

#         i=1
#         for file in files:
#             if file.endswith(".npz"):               # is npz file
#                 fp = path + file
#                 loaded = np.load(fp)
#                 runtime = loaded['runtime']         # load runtime data in npz file
#                 allRes = runtime.sum(axis=1)        # resource 
#                 meRes  = allRes[:, : RESOURCES['ME']]
#                 eeRes  = allRes[:, RESOURCES['ME']: RESOURCES['ME'] + RESOURCES['EE']]
#                 oeRes  = allRes[:, RESOURCES['ME'] + RESOURCES['EE']: RESOURCES['ME'] + RESOURCES['EE'] + RESOURCES['OE']]
#                 inRes  = allRes[:, :-1]
#                 exRes  = allRes[:, -1]              # 去掉最后的EX资源（不纳入统计）

#                 total    = allRes.sum()
#                 total_me = meRes.sum()
#                 total_ee = eeRes.sum()
#                 total_oe = oeRes.sum()
#                 total_ex = exRes.sum()

#                 diff_me  = meRes - daysWork
#                 diff_me_lt = diff_me[diff_me<0].sum()
#                 diff_me_gt = diff_me[diff_me>0].sum()
#                 diff_me_all = 0.04 * abs(diff_me_lt) + diff_me_gt

#                 diff_ee  = eeRes - daysWork
#                 diff_ee_lt = diff_ee[diff_ee<0].sum()
#                 diff_ee_gt = diff_ee[diff_ee>0].sum()
#                 diff_ee_all = 0.04 * abs(diff_ee_lt) + diff_ee_gt

#                 diff_oe  = oeRes - daysWork
#                 diff_oe_lt = diff_oe[diff_oe<0].sum()
#                 diff_oe_gt = diff_oe[diff_oe>0].sum()
#                 diff_oe_all = 0.04 * abs(diff_oe_lt) + diff_oe_gt

#                 diff   = inRes - daysWork
#                 difflt = diff[diff<0].sum()
#                 diffgt = diff[diff>0].sum()
#                 difall = abs(diffgt) + 0.04 * abs(difflt)

#                 outofdateprojs = 0
#                 outofdate = 0
#                 for prjInfo in PROJ_INFO:
#                     prj = projsTaskIndex.loc[prjInfo[0]]
#                     if prj.loc['deadline'] > 365:
#                         continue

#                     prjRuntime = runtime[:, prj.loc['start']:prj.loc['stop'], :].sum(axis=1).sum(axis=1)
#                     workDays = np.where(prjRuntime>0)
#                     enddate = np.max(workDays)
#                     if enddate > prj.loc['deadline']:
#                         outofdateprojs += 1
#                         outofdate += enddate - prj.loc['deadline']

#                 resourceResult.loc[file] = (total, total_me, total_ee, total_oe, total_ex, diff_me_lt, diff_me_gt, diff_me_all, diff_ee_lt, diff_ee_gt, diff_ee_all, diff_oe_lt, diff_oe_gt, diff_oe_all, difflt, diffgt, difall, outofdateprojs, outofdate)

#                 del runtime
#                 del loaded

#                 print(pr, i, "file done:", file)
#                 i+=1

#         columns = len(resourceResult.columns)
#         avg_line = np.zeros(columns, dtype=np.float64)
#         for col in range(len(resourceResult.columns)):
#             avg_val = np.average(resourceResult.iloc[:, col])
#             avg_line[col] = avg_val

#         resourceResult.loc['average'] = avg_line
        
#         tavg  = np.average(resourceResult['total'])
#         meavg = np.average(resourceResult['total-me'])
#         eeavg = np.average(resourceResult['total-ee'])
#         oeavg = np.average(resourceResult['total-oe'])
#         exavg = np.average(resourceResult['total-ex'])
#         mean  = np.mean(resourceResult['total-sum'])
#         var   = np.var(resourceResult['total-sum'])
#         stdev = np.std(resourceResult['total-sum'])
#         mean_avg = mean / (totalResCnt - 1)

#         resourceResult.loc['result', ['total', 'total-me', 'total-ee', 'total-oe', 'total-ex', 'me-spare', 'me-overtime', 'me-sum', 'ee-spare']] = (tavg, meavg, eeavg, oeavg, exavg, mean, var, stdev, mean_avg)

#         resourceResult.to_excel(writer, sheet_name=pr)
#         del resourceResult
#         writer.save()

#     writer.save()
#     print("Analysis results have been saved to file: ", output_file)

# def summarize(args):
#     ifile = args.input
#     ofile = args.output

#     print('读取 {0} 进行总结分析，并将结果输出到 {1}'.format(ifile, ofile))

#     summary = pd.DataFrame(columns=['总工时', '结构工时', '电路工时', '光学工时', '外部工时', '结构空闲工时', '结构加班工时', '结构总不恰当工时', '电路空闲工时', '电路加班工时', '电路总不恰当工时', '光学空闲工时', '光学加班工时', '光学总不恰当工时', '总空闲工时', '总加班工时', '总不恰当工时', '延期项目数', '总延期天数', '期望值', '方差', '标准差', '归一化期望值', '归一化方差', '归一化标准差'], dtype=np.float64)
#     colcnt  = len(summary.columns)
#     indata = openpyxl.load_workbook(PATH + ifile, data_only=True)
#     for name in indata.sheetnames:
#         sheet = indata[name]
#         print('正在读取PR: ', name)
#         row = 1
#         while True:
#             if str(sheet[row][0].value) == 'average':
#                 break
#             row += 1

#         data = np.zeros(colcnt, dtype=np.float64)
#         for col in range(colcnt - 6):
#             data[col] = sheet[row][col + 1].value

#         data[col+1] = sheet[row+1][6].value
#         data[col+2] = sheet[row+1][7].value
#         data[col+3] = sheet[row+1][8].value

#         data[col+4] = data[col+1] / data[0]
#         data[col+6] = data[col+3] / data[0]
#         data[col+5] = data[col+6] ** 2

#         summary.loc[name] = data

#     writer = pd.ExcelWriter(PATH + ofile)
#     summary.to_excel(writer, '汇总')
#     writer.save()

#     print('汇总数据已保存到： ', ofile)


# parser = argparse.ArgumentParser(description='我的毕业论文研究的执行命令行')
# subparsers = parser.add_subparsers(help='simulate用于仿真，analyze用于分析，summarize用于汇总分析数据')

# par_sim = subparsers.add_parser('simulate', help='对指定PR进行仿真，详细参见-h帮助')
# par_sim.add_argument('pr', nargs="+", help='需要开展仿真的优先规则PR，可同时指定多个，以空格隔开。')
# par_sim.add_argument('-t', dest='times', metavar='times', default=100, type=int, help='指定仿真的次数，默认为100次。')
# par_sim.add_argument('-l', dest='log', action='store_true', default=True, help='保存执行过程log到指定PR输出目录，采用添加模式。默认已打开。')
# par_sim.add_argument('-d', '--detailed', action='store_true', default=False, help='指定本参数时, 仿真过程中将打印任务细节。默认为关闭。')
# par_sim.set_defaults(func=simulate)

# par_ana = subparsers.add_parser('analyze', help='对指定PR清单结果进行分析，可指定全部或多个PR，详细参见-h帮助')
# par_ana.add_argument('-a', '--all', action='store_true', help='指定分析所有的PR结果')
# par_ana.add_argument('prlist', nargs='*', help='当不指定--all参数时，要指定分析的PR清单')
# par_ana.add_argument('-d', dest='dir', metavar='results_dir', type=str, default='', help='指定读取的结果目录，默认为当前目录下的results目录')
# par_ana.add_argument('-o', dest='file', metavar='output_file', type=str, default='results.xlsx', help='指定分析结果保存的文件, 默认为当前目录results.xlsx')
# par_ana.set_defaults(func=analyze)

# par_sum = subparsers.add_parser('summarize', help='对分析的所有数据进行汇总，详细参见-h帮助')
# par_sum.add_argument('-i', dest='input', metavar='input_file', help='输入的数据文件。当不指定时，默认为当前目录下的results.xlsx', action='store', default='results.xlsx')
# par_sum.add_argument('-o', dest='output', metavar='output_file', help='汇总数据的输出文件。当不指定时，默认为当前目录下的summary.xlsx', default='summary.xlsx')
# par_sum.set_defaults(func=summarize)

# args=parser.parse_args()
# if hasattr(args, 'func'):
#     args.func(args)
# else:
#     parser.print_help()


if __name__ == "__main__":
    args = sys.argv
    if (len(args) == 2) and (args[1] == "init"):
        print(f"欢迎使用PyMUD, 版本{Settings.__version__}. 使用PyMUD时, 建议建立一个新目录（任意位置），并将自己的脚本以及配置文件放到该目录下.")
        print("即将开始为首次运行初始化环境...")
        uname = platform.uname()
        system  = uname[0].lower()
        if system == "windows":
            dir = input("检测到当前系统为Windows, 请指定游戏脚本的目录（若目录不存在会自动创建），直接回车表示使用默认值[d:\pkuxkx\]:")
            if not dir: dir = "d:\\pkuxkx\\"
        elif system == "linux":
            dir = input("检测到当前系统为Linux, 请指定游戏脚本的目录（若目录不存在会自动创建），直接回车表示使用默认值[~/pkuxkx/]:")
            if not dir: dir = "~/pkuxkx/"
        else:
            print(f"当前系统不是windows或linux，可能无法通过init来进行配置，请注意.")
            dir = input("未能识别当前系统, 请指定游戏脚本的目录:")

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
        if system == "linux":
            print(f"后续运行PyMUD， 请在 {dir} 目录下键入命令： python3 -m pymud")
        else:
            print(f"后续运行PyMUD， 请在 {dir} 目录下键入命令： python -m pymud")

        input('所有内容已初始化完毕, 请按回车进入PyMUD.')

    if (len(args) == 2) and (args[1] == "withlog"):
        # 指定带log时，打印log信息
        # 所有级别log都存入文件
        logging.basicConfig(level=logging.NOTSET,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filename='myapp.log',
                            filemode='a')
        
    else:
        logging.disable()

    cfg = "pymud.cfg"
    if os.path.exists(cfg):
        with open(cfg, "r", encoding="utf8", errors="ignore") as fp:
            cfg_data = json.load(fp)
            main(cfg_data)
    else:
        main()