import re
import sqlite3
import os

with sqlite3.connect('MudMap.db') as conn:
    cursor = conn.cursor()

    #sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='扬州城'"
    #sql = "SELECT * FROM sqlite_master WHERE type=table AND name=扬州城"
    room = {}
    #room["name"] = 'testroom'
    sql = 'SELECT * FROM rooms WHERE roomname = "客栈"'
    #sql = "SELECT * FROM rooms WHERE roomname = 'testroom'"
    cursor.execute(sql)
    # 获取查询结果集:

    result = cursor.fetchone()
    # 检查查询结果
    print(result)