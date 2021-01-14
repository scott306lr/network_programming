import threading
import socket
import abc
import json
from commands import tcpCmdHandler,udpCmdHandler
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('port', help="port to start server.", type=int)
args = parser.parse_args() #args.port

PORT = int(args.port)
HOST = "127.0.0.1"
MAX_THREADS = 5
'''
client's json message form: 
{
    "user":
    "uid":
    "data":
}

server's json message form:
{
    "command":
    "data":
}

'''
class TCP_Server_Socket(threading.Thread, metaclass=abc.ABCMeta):
    def __init__(self,socket,semaphore):
        threading.Thread.__init__(self)
        self.socket=socket
        self.semaphore=semaphore
    def run(self):
        print("Got new connection!")
        welcomeMsg = b"********************************\n** Welcome to the BBS server. **\n********************************"
        self.socket.send(welcomeMsg)
        
        try:
            while True:
                rawMsg = self.socket.recv(2048).decode()
                if(rawMsg==""): break
                jMsg = json.loads(rawMsg)
                self.execute(jMsg)
                
        except BrokenPipeError:
            print('BrokenPipeError')
        except ConnectionResetError:
            print('ConnectionResetError')
        except json.JSONDecodeError:
            print('JSONDecodeError')
            
        print('Client closed.')
        self.socket.close()
        
    @abc.abstractmethod
    def execute(self,jMsg): pass
    
class UDP_Server_Socket(threading.Thread, metaclass=abc.ABCMeta):
    def __init__(self,socket):
        threading.Thread.__init__(self)
        self.socket=socket
    def run(self):
        print("UDP server started!")
        try:
            while True:
                rawMsg,addr= self.socket.recvfrom(2048)
                #if(rawMsg==" "): pass  #for testing
                jMsg = json.loads(rawMsg)
                self.execute(jMsg,addr)
                
        except BrokenPipeError:
            print('BrokenPipeError')
        except ConnectionResetError:
            print('ConnectionResetError')
        except json.JSONDecodeError:
            print('JSONDecodeError')
            
        print("UDP server broken.")
        self.socket.close()
        
    @abc.abstractmethod
    def execute(self,jMsg,addr): pass

class TCP_LRserver(TCP_Server_Socket,tcpCmdHandler):
    def __init__(self, socket, addr, lock, semaphore):
        TCP_Server_Socket.__init__(self,socket,semaphore)
        tcpCmdHandler.__init__(self, lock, addr)
        self.username = "none"
        self.UID = "none"
    def execute(self,jMsg):
        jres = self.runcmd(jMsg)
        print(jres)
        self.socket.sendall( json.dumps(jres).encode())

class UDP_LRserver(UDP_Server_Socket,udpCmdHandler):
    def __init__(self,socket,lock):
        UDP_Server_Socket.__init__(self,socket)
        udpCmdHandler.__init__(self,lock)
    def execute(self,jMsg,addr):
        jres = self.runcmd(jMsg)
        self.socket.sendto( json.dumps(jres).encode() , addr)

def main(): 
    lock = threading.Lock()
    semaphore = threading.Semaphore(MAX_THREADS)
    #start UDP server
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    u.bind((HOST, PORT))
    UDP_LRserver(u,lock).start()
    
    #start TCP server
    t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # port can be reused immediately when socket close.
    t.bind((HOST, PORT))
    t.listen()
    
    while True:
        client_socket, client_addr = t.accept()
        TCP_LRserver(client_socket, client_addr, lock, semaphore).start()
        


if __name__ == "__main__":
    main()

