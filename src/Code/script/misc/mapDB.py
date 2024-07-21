import re
import sqlite3
import os
import glob

class mapDB:
    def __init__(self):
        #连接数据库
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()
            sql = f'''create table if not exists rooms(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roomname VARCHAR not null,         
                attr VARCHAR,
                relation VARCHAR,
                desc VARCHAR,
                exits VARCHAR,
                neighbors VARCHAR,
                traversed INTEGER            
            )'''
            cursor.execute(sql)
            # room = {}
            # room["name"] = 'testroom'
            # room["attr"] = 'test attr'
            # room["relation"] = 'test relation'
            # room["desc"] = 'test desc'
            # room["exits"] = 'test exits'
            # room["neighbors"] = ''
            # room["traversed"] = 0
            # sql = f'replace into rooms(roomname,attr,relation,desc,exits,neighbors) values(?,?,?,?,?,?,?)'
            # cursor.execute(sql,(room["name"],room["attr"],room["relation"],room["desc"],room["exits"],room["neighbors"]))
            conn.commit()

    def addRoom(self,room):
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()
            sql = f'insert into rooms(roomname,attr,relation,desc,exits,neighbors) values(?,?,?,?,?,?)'
            cursor.execute(sql,(room["name"],room["attr"],room["relation"],room["desc"],room["exits"],room["neighbors"]))
            conn.commit()

    def findRoomsByRoom(self,room):
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()
            sql = f'SELECT * FROM rooms WHERE roomname=? AND relation=?'
            cursor.execute(sql,(room["name"],room["relation"]))
            # 获取查询结果集:
            results = cursor.fetchall()
            return results
    
    def isRoomInDB(self,room):
        dbrooms = self.findRoomsByRoom(room)
        cnt = len(dbrooms)
        if cnt>0:
            return dbrooms[0]


    def findRoomByDesc(self,room):
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()
            sql = f'SELECT * FROM rooms WHERE roomname=? AND relation=? AND desc=?'
            cursor.execute(sql,(room["name"], room["relation"],room["desc"]))
            # 获取查询结果集:
            result = cursor.fetchone()
            return result

    
    def setupRoomLink(self,room_node,neighbor_node,exit):
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()
            sql = f"select neighbor FROM rooms  WHERE id=? AND roomname=?"   
            cursor.execute(sql,(room_node[0],room_node[1]))
            # 获取查询结果集:
            neighborStr = cursor.fetchone()

            # 编写SQL更新语句,更新两个room的link
            sql_update = f"UPDATE rooms SET neighbor = ? WHERE id=? AND roomname=?"
            neighborStr = neighborStr+f'{exit}:({neighbor_node[0]},{neighbor_node[1]})'
            cursor.execute(sql_update, (neighborStr, room_node[0],room_node[1]))        
            # 提交事务
            conn.commit()     

    
    def getRoomNode(self,room):
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()
            sql = f'SELECT id,roomname FROM rooms WHERE roomname=? AND relation =?'
            cursor.execute(sql,(room["name"],room["relation"]))
            # 获取查询结果集:
            room_node = cursor.fetchone()
            return room_node
        

    def isTraversed(self,room_node):
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()
            sql = f'SELECT traversed FROM rooms WHERE id=? AND roomname=?'
            cursor.execute(sql,(room_node[0],room_node[1]))
            # 获取查询结果集:
            result = cursor.fetchone()
            return result

    def SetTraversed(self,room_node,state):
        # 编写SQL更新语句,更新traversed 
        with sqlite3.connect('MudMap.db') as conn:
            cursor = conn.cursor()            
            sql_update = f'UPDATE rooms SET traversed=? WHERE id=? AND roomname=?'
            # 执行更新
            cursor.execute(sql_update,(state, room_node[0],room_node[1]))        
            # 提交事务
            conn.commit()        