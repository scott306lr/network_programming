import random
import socket
import threading
import sqlite3
import os.path

HOST = '127.0.0.1'
PORT1 = 9999

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def tcpHandle (conn):
    try:
        conn.sendall(b"Welcome to server!")
        # file name
        name = str(conn.recv(1024),encoding='utf-8')
        file_path = os.path.join(BASE_DIR, name)
        filetodown = open(file_path, "wb")
        
        # get file
        data = conn.recv(1024)
        while data:   
            print("Recieving...")   
            filetodown.write(data)
            data = conn.recv(1024)
        print("Finish")  
        filetodown.close()
        
        #close connection
        conn.send(b"Closing connection...")
        conn.shutdown(2)
        conn.close()
        print("Connection Closed.") 
        
    except ConnectionResetError:
        print("Connection broken")
    except Exception as e:
        print("error")
        print(e)
        



tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
tcp_server.bind((HOST,PORT1))
tcp_server.listen(50)

while True:
    conn,addr = tcp_server.accept()
    t = threading.Thread(target = tcpHandle, args = [conn])
    t.start()