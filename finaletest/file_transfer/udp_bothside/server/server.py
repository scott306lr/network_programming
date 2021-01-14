import argparse
import socket
import os

# required arg

parser = argparse.ArgumentParser()
parser.add_argument('port', help="port to start server.", type=int)
args = parser.parse_args() #args.port
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PORT = int(args.port)
HOST = "127.0.0.1"
chunk_size = 512


def get_file(u):
    pkt_list = []
    while(True):
        raw_data, addr = u.recvfrom(2048)
        #print("got something!")
        if (raw_data==b'ended') :
            print("Got all fragments!")
            break
        else : pkt_list.append(raw_data)
        
        #print("asking for next fragment...")
        u.sendto( b"next", addr)

    file_name = pkt_list[0]

    with open(file_name, "wb") as f:
        for p in pkt_list[1:]:
            f.write(p)

    print(f"Finished downloading {file_name.decode()}")

def send_file(u):
    name, addr = u.recvfrom(2048)
    file_name = name.decode()
    print(f"Got name {file_name}")
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
        u.sendto( fragment, addr )
        ret, addr = u.recvfrom(2048)
        #print(ret.decode())
        
    u.sendto( b'ended', addr )
    print("Sent!")

def main():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    u.bind((HOST, PORT))
    print("start!")
    
    while True:
        raw_data, addr = u.recvfrom(2048)
        data = raw_data.decode()
        print(f"Got command: {data}")
        if( data == "hello"):
            u.sendto((f"Hello! {addr}!").encode(), addr)
            
        if( data == "get_file"):
            u.sendto(b"Ok", addr)
            send_file(u)
            
        if( data == "send_file"):
            u.sendto(b"Ok", addr)
            get_file(u)
            
        if( data == "get-file-list"):
            send = "Files:"
            for filename in os.listdir(BASE_DIR):
                if not filename.endswith('.py'):
                    send = send +" "+ filename
            
            u.sendto(send.encode(), addr)


if __name__ == "__main__":
    main()