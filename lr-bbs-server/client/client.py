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
mode = "bbs"

def nowtime():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    return current_time

def make_json(user,uid,data):
    return { "user":user, "uid":uid, "data":data }

def make_jsend(command,data):
    return { "command":command, "data":data }

class Chat_Server(threading.Thread):
    def __init__(self, socket, addr, owner, clients, msg_record, lock, ban_list):
        threading.Thread.__init__(self)
        self.socket = socket
        self.addr = addr
        self.owner = owner
        self.clients = clients
        self.msg_record = msg_record
        self.lock = lock
        self.ban_list = ban_list
    
    def run(self):
        self.lock.acquire()
        username = self.socket.recv(2048).decode()
        
        '''
        at first: 
            connect -> welcomeMsg -> ok -> broadcast 'xxx joined us'
        if banned:
            connect -> banMsg -> close -> (release_lock)
        '''
        if username in self.ban_list : 
            banMsg = "banned"
            self.socket.send(banMsg.encode())
            self.socket.close()
            self.lock.release()  
            return
        else :
            self.clients[ username ] = self.socket  #　clients += { name : socket }
            welcomeMsg = "********************************\n**Welcome to the chatroom**\n********************************"
            for rec in self.msg_record :
                welcomeMsg = welcomeMsg +'\n'+rec
                
            self.socket.send(welcomeMsg.encode())
        
        
        self.socket.recv(2048) #ensure client got welcome message.
        if (username != self.owner ): 
            self.broadcast(username,"sys",f'{username} join us.')
        self.lock.release()    
        
        try:
            while True:
                rawMsg = self.socket.recv(2048).decode()
                
                #self.lock.acquire() 
                if(rawMsg==""): break
                jMsg = json.loads(rawMsg)
                self.execute(jMsg)   ## proccess jMsg read from client.  Whether to let socket return or broadcast message
                #self.lock.release() 
                
        except BrokenPipeError:
            print('BrokenPipeError')
        except ConnectionResetError:
            print('ConnectionResetError')
        except json.JSONDecodeError:
            print('JSONDecodeError')
        self.socket.close()
        
    def record_txt(self,data):
        self.lock.acquire() 
        if (len(self.msg_record) == 3): self.msg_record.pop(0)
        self.msg_record.append(data)
        self.lock.release() 
        
    def create_msg(self,name,msg):
        t = nowtime()
        cmd = "none"
        data = f"\r{name}[{t}] : {msg}"
        if (name != "sys"): self.record_txt(data)
        jsend = make_jsend(cmd,data)
        return jsend
    
    def broadcast(self,sender,broadcast_name,msg):
        jsend = self.create_msg(broadcast_name, msg)
        for name in self.clients:
            if (name != sender): self.clients[name].sendall(json.dumps(jsend).encode() )  
            
    def switchback(self,client):
        cmd={   "command": "bbs",
                "data": "\rWelcome back to BBS." }
        client.sendall( json.dumps(cmd).encode())
        
    def execute(self,jMsg):
        user = jMsg["user"]
        if (jMsg["data"]=="leave-chatroom"):
            
            if(user!=self.owner):
                self.switchback(self.clients[user])
                self.clients.pop(user)
                self.broadcast(user, "sys", f'{user} leave us.')
            else:
                self.switchback(self.clients[user])
                self.clients.pop(user) # pop owner first so owner doesn't see sys msg.
                self.broadcast("sys", "sys", "the chatroom is close.")
                time.sleep(0.05) # to prevent tcp connecting 2 message together.   
                for c in self.clients: 
                    self.switchback(self.clients[c])
                self.clients.clear()
                
        elif (jMsg["data"]=="detach" and user==self.owner):
            self.switchback(self.clients[user])
            self.clients.pop(user)
            
        elif (jMsg["data"][0:4]=="kick" and user==self.owner):
            cmd = jMsg["data"].split(' ',2)
            name = cmd[1]
            self.switchback(self.clients[name])
            self.clients.pop(name)
            
        elif (jMsg["data"][0:3]=="ban" and user==self.owner):
            cmd = jMsg["data"].split(' ',2)
            name = cmd[1]
            self.ban_list.add(name)
            if name in self.clients:
                self.switchback(self.clients[name])
                self.clients.pop(name)

        elif (jMsg["data"][0:5]=="unban" and user==self.owner):
            cmd = jMsg["data"].split(' ',2)
            name = cmd[1]
            if name in self.ban_list:
                self.ban_list.remove(name)
            
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
        global mode
        self.t.connect((self.host, self.port))
        self.t.sendall( self.user.encode() )     #send username
        welcomeMsg = self.t.recv(2048).decode()  #recieve welcome & rec msg
        
        if (welcomeMsg == "banned"):
            print("You are banned from this server.")
            print("\r% ",end="")
            mode = "bbs"
            self.t.close()
            return
        
        else:
            self.t.sendall( b'ok' )              #sendback 'ok'
            print(welcomeMsg)
            
        while True: # when get data from server
            rawMsg = self.t.recv(2048).decode()
            jMsg = json.loads(rawMsg)
            print(jMsg['data'])
            #print(rawMsg)
            
            if (jMsg['command'] == "bbs"):
                print("\r% ",end="")
                mode = "bbs"
                self.t.close()
                break

def create_room(host, port, owner):
    client={}
    msg_record=[]
    lock = threading.Lock()
    ban_list=set()
    
    print("start to create chatroom...")
    t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # port can be reused immediately when socket close.
    t.bind((host, int(port)))
    t.listen()
    while True:
        client_socket, client_addr = t.accept()
        Chat_Server(client_socket, client_addr, owner, client, msg_record, lock, ban_list).start()
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
    def __init__(self, send_q, reply_q, chat_owner, username):
        Client_Socket.__init__(self, send_q, reply_q, username)
        self.chat_owner = chat_owner
        self.chat_client = None
        #considering whether to send cmdDict by server as client connects.
        self.cmdDict = {'hello':'udp', 'register':'udp', 'whoami':'udp', 'hi':'udp','list-chatroom':'udp',
            'login':'tcp', 'logout':'tcp', 'list-user':'tcp', 'exit':'tcp',
            'create-board':'tcp', 'create-post':'tcp', 'list-board':'tcp', 'get-ip':'tcp',
            'list-post':'tcp', 'read':'tcp', 'delete-post':'tcp', 'update-post':'tcp', 'comment':'tcp',
            'create-chatroom':'tcp','join-chatroom':'tcp','restart-chatroom':'tcp','attach':'tcp','close_chatroom':'tcp'}
        
    def cmdHandle(self,jMsg):    
        global mode
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
            mode = "chat"
            self.chat_owner = self.user
            chat_port = cmd[1]
            #create_room(HOST, chat_port, self.user)
            create_c = threading.Thread(target=create_room, args=(HOST, chat_port, self.user))
            create_c.start()
            
            time.sleep(0.1) # join room after room created
            self.chat_client = Chat_Client(HOST, chat_port, self.user)
            self.chat_client.start()
        if (cmd[0]=="join_chatroom"):  # join_chatroom {owner} {port}
            mode = "chat"
            self.chat_owner = cmd[1]
            chat_port = cmd[2]
            self.chat_client = Chat_Client(HOST, chat_port, self.user)
            self.chat_client.start()
        
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
    global mode
    send_q = queue.Queue()
    reply_q = queue.Queue()
    
    
    username = "none"
    chat_owner = "none" # joined chatroom's owner
    
    s = LR_Client(send_q, reply_q, chat_owner, username)
    s.start()
    welcomeMsg = s.t.recv(1024).decode()
    print(welcomeMsg)
    print("% ",end="")
    try:
        while True: 
            inpu = input()
            ################## bbs mode #########################
            if(mode=="bbs"):
                data = ' '.join( inpu.split() ) ## crop spaces
                send_q.put(data) #push command to queue
                if (inpu=="restart-chatroom"):
                    print("start to create chatroom...")
                    
                if (inpu=="exit"):
                    s.join()
                    break
                
                #read
                msg = reply_q.get(block=True)
                if (mode=="chat"): continue
                print (msg)
                print("% ",end="")
            ################## chat mode ########################  
            elif(mode=="chat"):
                if (inpu == "leave-chatroom" and s.chat_owner == s.user):
                    send_q.put("close_chatroom")
                    reply_q.get(block=True)
                jmsg = make_json(s.user, 0, inpu)
                s.chat_client.t.sendall(json.dumps(jmsg).encode()) #send j-msg from LRclient's tcp of chat-client 
                
    except KeyboardInterrupt:
        send_q.put("exit")
        s.join()
        print('')
    #print('\nClient will be closed.')


if __name__ == '__main__':
    main()
