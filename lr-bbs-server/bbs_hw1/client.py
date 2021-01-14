import socket
import sys

HOST = sys.argv[1] # '127.0.0.1'
PORT = int(sys.argv[2])
PORT2 = int(sys.argv[2])-1
cmdDict = {'register':'udp','whoami':'udp','login':'tcp','logout':'tcp','list-user':'tcp','exit':'tcp'}
randNum = '0000'
tcpClient = None


def tcphandle(message):
    # Send data
    tcpClient.sendall(message.encode())
    
    # Receive response  
    data = str(tcpClient.recv(1024),encoding='utf-8')
    #print (data)
    arrdata = data.split('@',1)
    cmd = ' '.join( arrdata[0].split(' ',3) ).split()
    if cmd[0] == 'logged':
        global randNum
        randNum = cmd[1]
    elif cmd[0] == 'exit':
        tcpClient.close()
        sys.exit(0)
    print(arrdata[1])

def udphandle(message):
    # Send data
    udpClient = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    udpClient.sendto(message.encode(),(HOST, PORT2))

    # Receive response
    data, server = udpClient.recvfrom(4096)  
    print(data.decode('utf-8'))


#Connect
tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpClient.connect((HOST, PORT))
data = str(tcpClient.recv(1024),encoding='utf-8')
print(data)

while (True) :
    message = input("% ")
    arg = message.split(' ',1)
    message = randNum +' '+ message
    try: 
        ctype = cmdDict[arg[0]]
    except: 
        print('Unknown command.')
        continue
    
    if (ctype == 'tcp'):
        tcphandle(message)
    else:
        udphandle(message)



