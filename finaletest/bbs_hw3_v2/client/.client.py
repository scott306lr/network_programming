import socket
import json
import sys
import threading
import abc
import queue
import os,signal,time
import argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('host', help="server's host.")
parser.add_argument('port', help="port to connect to server.", type=int)
args = parser.parse_args() #args.port

PORT = int(args.port)
HOST = args.host

def nowtime():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    return current_time

def make_json(user,uid,data):
    return { "user":user, "uid":uid, "data":data }

def make_jsend(command,data):
    return { "command":command, "data":data }

class Chat_Server(threading.Thread):
    def __init__(self, socket, owner, clients, msg_record):
        threading.Thread.__init__(self)
        self.socket = socket
        self.owner = owner
        self.clients = clients
        self.msg_record = msg_record
    
    def run(self):
        username = self.socket.recv(2048).decode()
        self.clients[ username ] = self.socket  #　clients += { name : socket }
        welcomeMsg = "********************************\n**Welcome to the chatroom**\n********************************"
        for rec in self.msg_record :
            welcomeMsg = welcomeMsg +'\n'+rec
        self.socket.send(welcomeMsg.encode()) 
        if (username != self.owner ): 
            self.broadcast(username,"sys",f'{username} join us.')
        
        try:
            while True:
                rawMsg = self.socket.recv(2048).decode()
                if(rawMsg==""): break
                jMsg = json.loads(rawMsg)
                self.execute(jMsg)   ## proccess jMsg read from client.  Whether to let socket return or broadcast message
                
        except BrokenPipeError:
            print('BrokenPipeError')
        except ConnectionResetError:
            print('ConnectionResetError')
        except json.JSONDecodeError:
            print('JSONDecodeError')
        self.socket.close()
        
    def record_txt(self,data):
        if (len(self.msg_record) == 3): self.msg_record.pop(0)
        self.msg_record.append(data)
        
    def create_msg(self,name,msg):
        t = nowtime()
        cmd = "none"
        data = f"{name}[{t}] : {msg}"
        if (name != "sys"): self.record_txt(data)
        jsend = make_jsend(cmd,data)
        return jsend
    
    def broadcast(self,sender,broadcast_name,msg):
        jsend = self.create_msg(broadcast_name, msg)
        for name in self.clients:
            if (name != sender): self.clients[name].sendall(json.dumps(jsend).encode() )  
            
    def switchback(self,client):
        cmd={   
                "command": "bbs",
                "data": "Welcome back to BBS."
            }
        client.sendall( json.dumps(cmd).encode())
        
    def execute(self,jMsg):
        user = jMsg["user"]
        if (jMsg["data"]=="leave-chatroom"):
            if(user!=self.owner):
                self.switchback(self.clients[user])
                self.clients.pop(user)
                self.broadcast(user, "sys", f' {user} leave us.')
            else:
                self.broadcast("sys", "sys", "the chatroom is close.")
                for c in self.clients: 
                    self.switchback(self.clients[c])
                
                
        
        elif (jMsg["data"]=="detach" and user==self.owner):
            self.switchback(self.clients[user])
            self.clients.pop(user)
            
        else:
            self.broadcast(user, user, jMsg['data'])  

class Chat_Client(threading.Thread):
    def __init__(self, host, port, user):
        threading.Thread.__init__(self)
        self.host = host
        self.port = int(port)
        self.user = user
        self.t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def run(self):
        #print("joining...")
        self.t.connect((self.host, self.port))
        self.t.sendall( self.user.encode() )
        welcomeMsg = self.t.recv(1024).decode()
        print(welcomeMsg)
        while True: 
            rawMsg = self.t.recv(1024).decode()
            jMsg = json.loads(rawMsg)
            print(jMsg['data'])
            if (jMsg['command'] == "bbs"):
                print("% ",end="")
                self.t.close()
                break

def create_room(host, port, owner):
    client={}
    msg_record=[]
    
    t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # port can be reused immediately when socket close.
    t.bind((host, int(port)))
    t.listen()
    while True:
        client_socket, client_addr = t.accept()
        Chat_Server(client_socket, owner, client, msg_record).start()
    return
    
def join_room(host, port, user):
    j = Chat_Client(host, port, user)
    j.start()
    return

class Client_Socket(threading.Thread, metaclass=abc.ABCMeta):
    def __init__(self, send_q, reply_q, username):
        threading.Thread.__init__(self)
        self.send_q = send_q
        self.reply_q = reply_q
        self.u = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.user = username
        self.uid = "none"
        
    def run(self):
        self.t.connect((HOST, PORT))
        # welcomeMsg = self.t.recv(1024).decode()
        # self.reply_q.put(welcomeMsg)
        
        while True:
            data = self.send_q.get(block=True)
            reply = self.execute(data)
            self.reply_q.put(reply)

    @abc.abstractmethod
    def execute(self, cmd):
        pass
    
class LR_Client(Client_Socket):
    def __init__(self, send_q, reply_q, mode, chat_owner, username):
        Client_Socket.__init__(self, send_q, reply_q, username)
        self.mode = mode
        self.chat_owner = chat_owner
        self.chat_client = None
        #considering whether to send cmdDict by server as client connects.
        self.cmdDict = {'hello':'udp', 'register':'udp', 'whoami':'udp', 'hi':'udp','list-chatroom':'udp',
            'login':'tcp', 'logout':'tcp', 'list-user':'tcp', 'exit':'tcp',
            'create-board':'tcp', 'create-post':'tcp', 'list-board':'tcp',
            'list-post':'tcp', 'read':'tcp', 'delete-post':'tcp', 'update-post':'tcp', 'comment':'tcp',
            'create-chatroom':'tcp','join-chatroom':'tcp','restart-chatroom':'tcp','attach':'tcp'}
        
    def cmdHandle(self,jMsg):    
        cmd = jMsg['command'].split(' ',3)
        if (cmd[0]=="setuser"):
            self.user = cmd[1]
            self.uid = cmd[2]
        if (cmd[0]=="logout"):
            self.user = "none"
            self.uid = "none"
        if (cmd[0]=="exit"):
            self.u.close()
            self.t.close()
            sys.exit(0)
        if (cmd[0]=="create_chatroom"): # create_chatroom {port}
            self.mode = "chat"
            self.chat_owner = self.user
            chat_port = cmd[1]
            #create_room(HOST, chat_port, self.user)
            create_c = threading.Thread(target=create_room, args=(HOST, chat_port, self.user))
            create_c.start()
            
            time.sleep(0.1)
            self.chat_client = Chat_Client(HOST, chat_port, self.user)
            self.chat_client.start()
        if (cmd[0]=="join_chatroom"):  # join_chatroom {owner} {port}
            self.mode = "chat"
            self.chat_owner = cmd[1]
            chat_port = cmd[2]
            self.chat_client = Chat_Client(HOST, chat_port, self.user)
            self.chat_client.start()
            #join_room(HOST, chat_port, self.user)
        
        return jMsg['data']
        
    def tcpHandle(self,jsend):
        self.t.sendall( json.dumps(jsend).encode() )
        #recieve
        rawMsg = str(self.t.recv(2048),encoding='utf-8')
        jMsg = json.loads(rawMsg)
        #proccess
        return self.cmdHandle(jMsg)
        
    def udpHandle(self,jsend):
        self.u.sendto( json.dumps(jsend).encode(), (HOST, PORT) )
        #recieve
        rawMsgb, server = self.u.recvfrom(2048)
        jMsg = json.loads(rawMsgb.decode('utf-8'))
        #proccess
        return self.cmdHandle(jMsg)

    def execute(self,data):  
        try:
            cmd = data.split()
            #print(f"cmd: {cmd}")
            cmdType = self.cmdDict[cmd[0]]
            jsend = make_json(self.user,self.uid,data)
            if   ( cmdType =='tcp' ): return self.tcpHandle(jsend)
            elif ( cmdType =='udp' ): return self.udpHandle(jsend)
            else: return 'You fucked up.'
            
        except KeyError:
            return 'Unknown command.'
    


def main():
    send_q = queue.Queue()
    reply_q = queue.Queue()
    mode = "bbs"
    
    username = "none"
    chat_owner = "none" # joined chatroom's owner
    
    s = LR_Client(send_q, reply_q, mode, chat_owner, username)
    s.start()
    welcomeMsg = s.t.recv(1024).decode()
    print(welcomeMsg)
    print("% ",end="")
    try:
        while True: 
            inpu = input()
            ################## bbs mode #########################
            if(s.mode=="bbs"):
                data = ' '.join( inpu.split() ) ## crop spaces
                send_q.put(data) #push command to queue
                if (inpu=="exit"):
                    s.join()
                    break
                
                #read
                msg = reply_q.get(block=True)
                if (s.mode=="chat"): continue
                print (msg)
                print("% ",end="")
            ################## chat mode ########################  
            elif(s.mode=="chat"):
                jmsg = make_json(s.user, 0, inpu)
                s.chat_client.t.sendall(json.dumps(jmsg).encode())
                
                if (inpu == "detach" ):
                    if (s.user == s.chat_owner):
                        s.mode="bbs"
                        continue
                
                if (inpu == "leave-chatroom"):
                    if(s.user == s.chat_owner): send_q.put("close_chatroom")
                    s.mode="bbs"
                    continue
                
    except KeyboardInterrupt:
        send_q.put("exit")
        s.join()
        print('')
    #print('\nClient will be closed.')


if __name__ == '__main__':
    main()
