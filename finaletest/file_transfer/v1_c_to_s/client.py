import socket
import sys
import os.path

HOST = sys.argv[1] # '127.0.0.1'
PORT = int(sys.argv[2])
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.connect((HOST, PORT))

welcomeMsg = str(s.recv(1024),encoding='utf-8')
print(welcomeMsg)
while True:
    # file name
    try: 
        name = input("File Name:")
        file_path = os.path.join(BASE_DIR, name)
        filetosend = open(file_path, "rb")
        break
    except KeyboardInterrupt: 
        print("close.")
        sys.exit(0)
    except: print("File not found!")
    
    
# send file name
s.send(name.encode())

# send file
data = filetosend.read(1024)
while data:
    print("Sending...")
    s.send(data)
    data = filetosend.read(1024)
filetosend.close()

#shutdown
s.shutdown(socket.SHUT_WR)
print("Done Sending.")
print (s.recv(1024).decode('utf-8'))
s.close()


