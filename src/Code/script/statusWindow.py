from pymud import Settings
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from termcolor import colored
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
    to_formatted_text,
)
from .misc.formatMudStr import remove_ansi_color

from prompt_toolkit.formatted_text import ANSI

def pu_color(value, max):
    pu = 100
    if max:
        pu = 100*value/max

    if pu < 60:
        style = Settings.styles["red"]
    elif pu < 80:
        style = Settings.styles["yellow"]
    elif pu < 120:
        style = Settings.styles["green"]   
    else:
        style = Settings.styles["skyblue"]
        
    return style

def FormattedList(title,statusValue):
    formatted_list = list()
    formatted_list.append((Settings.styles["title"], title))

    var = [int(x) for x in statusValue]
    style = pu_color(var[0],var[1])
    str_jingqi = f"{var[0]:4d}/{var[1]:4d}"
    formatted_list.append((style, str_jingqi))

    if len(statusValue)>2:
        style = pu_color(var[2],var[1])
        if var[1]:
            pu = int(100*var[2]/var[1])        
            str_effPU = f"({pu:3d}%)"
            formatted_list.append((style, str_effPU))

    return formatted_list

def StatusList1(session):
    formatted_list = list()
    
    var = session.getVariables(("jing", "max_jing", "eff_jing"))
    formatted_list += FormattedList("【精神】",var)
    var = session.getVariables(("qi", "max_qi", "eff_qi"))
    formatted_list += FormattedList("【真气】",var)
    var = session.getVariables(("neili", "max_neili"))
    formatted_list += FormattedList("【内力】",var)
    var = session.getVariables(("jingli", "max_jingli"))
    formatted_list += FormattedList("【精力】",var)

    return formatted_list

def StatusList2(session):
    formatted_list = list()
    formatted_list.append((Settings.styles["title"], "【食物】"))

    food = int(session.getVariable('food', '0'))
    if food < 100:
        style = Settings.styles["red"]
    elif food < 200:
        style = Settings.styles["yellow"]
    elif food < 350:
        style = Settings.styles["green"]
    else:
        style = Settings.styles["skyblue"]

    formatted_list.append((style, f"{food:4d}"))
    formatted_list.append((Settings.styles["normal"], "           "))

    formatted_list.append((Settings.styles["title"], "【饮水】"))
    water = int(session.getVariable('water', '0'))
    if water < 100:
        style = Settings.styles["red"]
    elif water < 200:
        style = Settings.styles["yellow"]
    elif water < 350:
        style = Settings.styles["green"]
    else:
        style = Settings.styles["skyblue"]
    formatted_list.append((style, f"{water:4d}"))    
    formatted_list.append(("", "           "))

    formatted_list.append((Settings.styles["title"], "【经验】"))
    formatted_list.append((Settings.styles["value"], "{}".format(session.getVariable('combat_exp'))))
    formatted_list.append(("", "     "))
    formatted_list.append((Settings.styles["title"], "【潜能】"))
    formatted_list.append((Settings.styles["value"], "{}".format(session.getVariable('pot'))))    

    return formatted_list

def StatusList3(session):
    formatted_list = list()
    formatted_list.append((Settings.styles["title"], "【角色】 "))
    formatted_list.append((Settings.styles["value"], "{}".format(session.getVariable('name'))))
    formatted_list.append(("", "          "))
    formatted_list.append((Settings.styles["title"], "【门派】 "))
    #menpai = to_formatted_text(ANSI(session.getVariable('title')))
    #formatted_list.append((Settings.styles["value"], "{}".format(remove_ansi_color(session.getVariable('title')))))
    formatted_list.append((Settings.styles["value"], "{}".format(session.getVariable('title'))))

    formatted_list.append(("", "    "))
    formatted_list.append((Settings.styles["title"], "【存款】"))
    formatted_list.append((Settings.styles["value"], "{}".format(session.getVariable('deposit'))))

    return formatted_list


def StatusList4(session):
    formatted_list = list()

    ins_loc = session.getVariable("ins_loc", None)
    tm_locs = session.getVariable("tm_locs", None)
    ins = False
    if isinstance(ins_loc, dict) and (len(ins_loc) >= 1):
        ins = True
        loc = ins_loc
    elif isinstance(tm_locs, list) and (len(tm_locs) == 1):
        ins = True
        loc = tm_locs[0]

    formatted_list.append((Settings.styles["title"], "【惯导】"))
    if ins:
        formatted_list.append((Settings.styles["skyblue"], "正常"))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【位置】"))
        formatted_list.append((Settings.styles["green"], f"{loc['city']} {loc['name']}({loc['id']})"))
    else:
        formatted_list.append((Settings.styles["red"], "丢失"))
        formatted_list.append(("", "           "))
        formatted_list.append((Settings.styles["title"], "【位置】"))
        formatted_list.append((Settings.styles["value"], f"{session.getVariable('short')}"))

    return formatted_list

#状态栏
def statusWindow(session):
    formatted_list = list()    
    formatted_list += StatusList1(session)
    # a new-line
    formatted_list.append(("", "\n"))
    formatted_list += StatusList2(session)
    # a new-line
    formatted_list.append(("", "\n"))
    formatted_list += StatusList3(session)
    # a new-line
    formatted_list.append(("", "\n"))
    formatted_list += StatusList4(session)

    return formatted_list