import random
import socket
import threading
import sqlite3
import os.path

HOST = '127.0.0.1'
PORT1 = 9999
PORT2 = 9998

# tcp_serv = None
# udp_serv = None

rdict={}    
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'userinf.db')


def login(username, password):
    con = sqlite3.connect(db_path)
    c = con.cursor()
    c.execute(f"SELECT * FROM user WHERE name='{username}' AND password='{password}'")
    result = c.fetchone()
    con.close()
    if result != None:
        return 0
    else: 
        return -1


def listall():
    con = sqlite3.connect(db_path)
    c = con.cursor()
    msg = 'NAME:'.ljust(15, ' ') + 'EMAIL:'.ljust(20, ' ') + '\n'
    for row in c.execute('SELECT * FROM user ORDER BY id'):
        msg = msg + str(row[1]).ljust(15, ' ') + str(row[2]).ljust(20, ' ') + '\n'
    con.close()
    return msg

def register(username, email, password):
    con = sqlite3.connect(db_path)    
    c = con.cursor()
    c.execute(f"SELECT * FROM user WHERE name='{username}'")
    if c.fetchone() is None:
        c.execute(f"INSERT INTO USER VALUES (null,'{username}','{email}','{password}')")
        con.commit()
        con.close()
        return 0
    else:
        con.close()
        return -1

def response(msg,user,addr,conn,type='udp'):
    global rdict
    msgrand = msg[:4]
    arg = ' '.join( msg[5:].split(' ',5) ).split()
    cmd = 'none'
    sendmsg = 'none'
    #print(f'test: {arg[0]}')
    if type == 'tcp':
        if(arg[0]=='login'):
            if rdict.get(msgrand) != None :
                sendmsg = 'Please logout first!'
            else:    
                try:
                    username = arg[1]
                    password = arg[2]
                    
                    login_check = login(username,password)
                    if login_check == 0 :
                        sendmsg = f'Welcome, {username}.'
                        randNum = str(random.randint(1000,9999))
                        cmd = f'logged {randNum}'
                        rdict[randNum] = username 
                    elif login_check == -1 :
                        sendmsg = 'Login failed.'
                        
                except:
                    sendmsg = "login <username> <password>"

        elif(arg[0]=='logout'):
            try:
                username = rdict[msgrand]
                rdict.pop(msgrand)
                sendmsg = f'Bye, {username}.'
            except:
                sendmsg = 'Please login first!'
            
            
        elif(arg[0]=='list-user'):
            sendmsg = listall()
            
        elif(arg[0]=='exit'):
            #print(f'test: {arg[0]}')
            if rdict.get(msgrand) != None :
                rdict.pop(msgrand)
            cmd = 'exit'
        
        else:
            sendmsg = 'Unknown command!' 
        sendmsg = cmd + '@' + sendmsg   
        conn.sendto(sendmsg.encode('utf-8'),addr)
        # conn.close()
        
    elif type == 'udp':
        if(arg[0]=='register'):
            try:
                username = arg[1]
                email = arg[2]
                password = arg[3]
                
                reg_check = register(username,email,password)
                if reg_check == 0 :
                    sendmsg = "Registered successfully."
                else:
                    sendmsg = 'Username is already used.'
            except:
                sendmsg = "register <username> <email> <password>"

        elif(arg[0]=='whoami'):
            try:
                username = rdict[msgrand]
                sendmsg = username
                print(username)
            except:
                sendmsg = "Please login first."

        #sendmsg = cmd + '@' + sendmsg
        conn.sendto(sendmsg.encode('utf-8'), addr)
        
    else:
        return

def udpHandle(serv):
    while True:
        bdata,addr= serv.recvfrom(2048)
        data = str(bdata, encoding='utf-8')
        print(f'got UDP msg "{data}" from {addr}')
        #mutex.acquire()
        response(data,None,addr,serv,'udp')
        #mutex.release()


def tcpHandle(conn,addr):
    print (f'[NEW CONNECTION] {addr} connected.')
    welcomeMsg = '********************************\n** Welcome to the BBS server. **\n********************************'
    conn.sendto(welcomeMsg.encode('utf-8'),addr)
    while True:
        try:
            data = str(conn.recv(1024), encoding='utf-8')
            print(f'got TCP msg "{data}" from {addr}')
            #mutex.acquire()
            response(data,None,addr,conn,'tcp')
            #mutex.release()
        except:
            print(f'Bye! {addr}')
            conn.close()
            break


tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_server.bind((HOST,PORT1))
tcp_server.listen(50)
udp_server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
udp_server.bind((HOST,PORT2))
mutex = threading.Lock()

u = threading.Thread(target = udpHandle, args = [udp_server])
u.start() 
while True:
    conn,addr = tcp_server.accept()
    t = threading.Thread(target = tcpHandle, args = (conn,addr))
    t.start()