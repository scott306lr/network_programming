import argparse
import socket

# required arg

parser = argparse.ArgumentParser()
parser.add_argument('port', help="port to start server.", type=int)
args = parser.parse_args() #args.port

PORT = int(args.port)
HOST = "127.0.0.1"


def get_file(u):
    pkt_list = []
    
    while(True):
        raw_data, addr = u.recvfrom(2048)
        print("got something!")
        if (raw_data==b'ended') :
            print("Got all fragments!")
            break
        else : pkt_list.append(raw_data)
        
        print("asking for next fragment...")
        u.sendto( b"next", addr)

    file_name = pkt_list[0]

    with open(file_name, "wb") as f:
        for p in pkt_list[1:]:
            f.write(p)

    print(f"Finished downloading {file_name.decode()}")
    

def main():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    u.bind((HOST, PORT))
    print("start!")
    
    while True:
        raw_data, addr = u.recvfrom(2048)
        data = raw_data.decode()
        print(data)
        if( data == "hello"):
            u.sendto((f"Hello! {addr}!").encode(), addr)
            
        if( data == "sendfile"):
            u.sendto(b"Ok", addr)
            get_file(u)



if __name__ == "__main__":
    main()