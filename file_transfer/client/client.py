import argparse
import socket
import os.path
import sys

# required arg

parser = argparse.ArgumentParser()
parser.add_argument('host', help="server's host.")
parser.add_argument('port', help="port to connect to server.", type=int)
args = parser.parse_args() #args.port

PORT = int(args.port)
HOST = args.host
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
chunk_size = 512

def get_file(u, file_name):
    
    u.sendto( file_name.encode(), (HOST,PORT) )
    
    pkt_list = []
    while(True):
        raw_data, addr = u.recvfrom(2048)
        #print("got something!")
        if (raw_data==b'ended') :
            #print("Got all fragments!")
            break
        
        pkt_list.append(raw_data)
        #print("asking for next fragment...")
        u.sendto( b"next", (HOST,PORT))

    file_name = pkt_list[0]

    with open(file_name, "wb") as f:
        for p in pkt_list[1:]:
            f.write(p)

    print(f"Finished downloading {file_name.decode()}")

def send_file(u, file_name):
    # file name
    file_path = os.path.join(BASE_DIR, file_name)
    f = open(file_path, "rb")

    pkt_list = [] # first packet is filename
    pkt_list.append(file_name.encode())
    
    chunk = f.read(chunk_size)
    while chunk:
        pkt_list.append(chunk)
        chunk = f.read(chunk_size)
    f.close()
    
    for fragment in pkt_list :
        u.sendto( fragment, (HOST,PORT) )
        ret, addr = u.recvfrom(2048)
        #print(ret.decode())
        
    u.sendto( b'ended', (HOST,PORT) )
    print("Sent!")



def main():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.settimeout(0.1)
    while True:
        inpu = input("%")
        arr = inpu.split()
        
        if(arr[0] == "get-file"):
            for file_name in arr[1:] :
                u.sendto( b'get_file', (HOST,PORT) )
                raw_data, addr = u.recvfrom(2048)
                get_file(u, file_name)
                
        elif(arr[0] == "send-file"):
            for file_name in arr[1:] :
                u.sendto( b'send_file', (HOST,PORT) )
                raw_data, addr = u.recvfrom(2048)
                send_file(u, file_name)
                
        elif(arr[0] == "exit"):
            u.close()
            sys.exit(0)
            
        else:
            u.sendto( inpu.encode(), (HOST,PORT) )
            ret, addr = u.recvfrom(2048)
            print(ret.decode())
        


if __name__ == "__main__":
    main()



