# 3 系统命令

- 系统命令是指在命令行键入的用于操作系统功能的命令，一般以#号开头。
- 除少数命令外（包括#help、#exit、#session、#close等），其他命令也可以在代码中通过session.exec系列命令进行调用。
- 在命令中可以使用大括号{}将一段代码括起来，形成代码块。代码块会被作为一条代码处理。

## #close

## #exit

## #help

## #session

## #action

等同于#trigger，详见 [#trigger](#trigger-tri)

## #alias, #ali

#alias命令用于操作别名。#ali是该命令的简写方式。该命令可以不带参数、带一个参数或者两个参数。用法与示例如下。
- #ali: 无参数, 打印列出当前会话中所有的别名清单
- #ali my_ali: 一个参数, 列出id为my_ali的Alias对象的详细信息
- #ali my_ali on: 两个参数，启用id为my_ali的Alias对象（enabled = True）
- #ali my_ali off: 两个参数， 禁用id为my_ali的Alias对象（enabled = False）
- #ali my_ali del: 两个参数，删除id为my_ali的Alias对象
- #ali {^gp\s(.+)$} {get %1 from corpse}: 两个参数，新增创建一个Alias对象。使用时，gp gold = get gold from corpse

## #all

#all命令可以同时向所有会话发送统一命令。用法与示例如下。
- #all #cls: 所有会话统一执行#cls命令
- #all quit: 所有会话的角色统一执行quit退出

## #clear, #cls

#clear命令清除当前会话的内容缓冲。

## #command, #cmd

## #connect, #con

## #error

## #gag

## #global

## #gmcp

## #ignore, #ig

## #load

## #message, #mess

## #modules, #mods

## #num


## #plugins


## #py

## #reload

## #repeat, #rep

## #replace

## #reset

## #save

## #t+, #t-

## #task

## #test

## #timer, #ti

## #trigger, #tri

## #unload

## #variable, #var

## #wait, #wa

## #warning

## #info

