import re
import sqlite3
import os
import glob

def getBookData(bookFile):
    page = []
    book = []
    chanting = []
    with open(bookFile, 'r') as file:
        lines = file.readlines()
        # 去掉每行末尾的换行符
        lines = [line.rstrip() for line in lines]
        for k in range(len(lines)-4):
            pt =re.search(r'page\s+\d+',lines[k])
            if pt:
                page.append(pt.group())
                bookstr = lines[k+1].replace('>', "", 2).lstrip()
                book.append(bookstr)
                chanting.append(lines[k+4])

    return (page,book,chanting)

# 使用glob模块列出所有txt文件
txt_files = glob.glob('D:\mud\少林\经书\*.txt')

#连接数据库
con = sqlite3.connect('MudMap.db')
cur = con.cursor()

def updateRoom:
for bookFile in txt_files:
    page, book ,chanting = getBookData(bookFile)
    bookStr = os.path.basename(bookFile).rstrip('.txt')

    sql = f'drop table if exists {bookStr}'
    cur.execute(sql)
    sql = f'''create table if not exists {bookStr}(
        page VARCHAR not null,
        book VARCHAR not null,
        chanting VARCHAR not null 
    )'''
    cur.execute(sql)

    sql = f'insert into {bookStr}(page,book,chanting) values(?,?,?)'
    for k in range(len(page)):
        cur.execute(sql,(page[k],book[k],chanting[k]))
    con.commit()

cur.close()