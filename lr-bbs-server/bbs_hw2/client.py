import socket
import json
import sys
import threading
import abc
import queue
import os,signal

HOST = sys.argv[1] # '127.0.0.1'
tPORT = int(sys.argv[2])
uPORT = int(sys.argv[2])
mode = "bbs"

def make_json(user,uid,data):
    return { "user":user, "uid":uid, "data":data }

class Client_Socket(threading.Thread, metaclass=abc.ABCMeta):
    def __init__(self, send_q, reply_q):
        threading.Thread.__init__(self)
        self.send_q = send_q
        self.reply_q = reply_q
        self.u = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def run(self):
        self.t.connect((HOST, tPORT))
        welcomeMsg = self.t.recv(1024).decode()
        self.reply_q.put(welcomeMsg)
        
        # try:
        while True:
            data = self.send_q.get(block=True)
            reply = self.execute(data)
            self.reply_q.put(reply)

    @abc.abstractmethod
    def execute(self, cmd):
        pass
    
class LR_Client(Client_Socket):
    def __init__(self, send_q, reply_q):
        Client_Socket.__init__(self, send_q, reply_q)

    #considering whether to send cmdDict by server as client connects.
    cmdDict = {'hello':'udp','register':'udp','whoami':'udp','hi':'udp',
            'login':'tcp','logout':'tcp','list-user':'tcp','exit':'tcp',
            'create-board':'tcp','create-post':'tcp','list-board':'tcp',
            'list-post':'tcp','read':'tcp','delete-post':'tcp','update-post':'tcp','comment':'tcp'}
    
    user = "none"
    uid = "none"
        
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
            
        return jMsg['data']
        
    def tcpHandle(self,jsend):
        self.t.sendall( json.dumps(jsend).encode() )
        #recieve
        rawMsg = str(self.t.recv(2048),encoding='utf-8')
        jMsg = json.loads(rawMsg)
        #proccess
        return self.cmdHandle(jMsg)
        
    def udpHandle(self,jsend):
        self.u.sendto( json.dumps(jsend).encode(), (HOST, uPORT) )
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
    socket = LR_Client(send_q,reply_q)
    socket.start()

    try:
        while True: 
            msg = reply_q.get(block=True)
            print (msg)
            if(mode=="bbs"):
                inpu = input('% ')
                data = ' '.join( inpu.split() ) ## crop spaces
                send_q.put(data) #push command to queue
                
                if inpu=="exit":
                    socket.join()
                    break
                
    except KeyboardInterrupt:
        send_q.put("exit")
        socket.join()
        print('')
    #print('\nClient will be closed.')


if __name__ == '__main__':
    main()
