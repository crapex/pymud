import sqlite3
import pandas as pd

# 连接SQLite数据库
conn = sqlite3.connect('MudMap.db')

# 获取数据库中的所有表名
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# 创建一个Excel写入器
writer = pd.ExcelWriter('xkxMap.xlsx', engine='openpyxl')

# 将每个表写入Excel
for table_name in tables:
    table_name = table_name[0]
    table = pd.read_sql_query("SELECT * from %s" % table_name, conn)
    table.to_excel(writer, sheet_name=table_name, index=False)

# 保存Excel文件
writer._save()

# 关闭数据库连接
conn.close()