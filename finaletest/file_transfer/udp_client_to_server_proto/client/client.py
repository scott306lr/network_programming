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


def send_file(u):
    # file name
    try: 
        file_name = input("File Name:")
        file_path = os.path.join(BASE_DIR, file_name)
        f = open(file_path, "rb")
    except: 
        print("File not found!")
        return


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
        print(ret.decode())
        
    u.sendto( b'ended', (HOST,PORT) )
    print("Sent!")



def main():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.settimeout(0.1)
    
    while True:
        inpu = input("%")
        u.sendto( inpu.encode(), (HOST,PORT) )
        ret, addr = u.recvfrom(2048)
        print(ret.decode())
        
        if(inpu == "sendfile"):
            send_file(u)
        


if __name__ == "__main__":
    main()



