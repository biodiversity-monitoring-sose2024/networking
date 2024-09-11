import socket, argparse, sys, time, os, psutil



def create_socket(args):
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #try:
    tcp_sock.bind((args.A, args.P))
    #except:
    #    print("Invalid IP adress or port")
    return tcp_sock

def create_socket2(args):
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #try:
    tcp_sock.bind((args.A, 5002))
    #except:
    #    print("Invalid IP adress or port")
    return tcp_sock

def listen_traffic(sock, args):
    while True :
        print("Listening...")
        sock.listen()
        connSock, addr = sock.accept()
        parentPID = os.getpid()
        parentProcess = psutil.Process(parentPID)
        pid = os.fork()
        if (pid == 0):
            time1 = time.time()
            size = int.from_bytes(connSock.recv(4),"big")
            print("Expecting " + str(size) + " bytes")
            buffer = bytearray()
            while len(buffer) < size:
                if (time.time()-time1) > 300 or parentProcess.status()== psutil.STATUS_ZOMBIE:
                    print("Terminating forked Process")
                    sys.exit()
                data = connSock.recv(262144)
                
                buffer = buffer + data
                #print("Received " + str(len(buffer)) + " from " + str(size))
            connSock.close()
            time2 = time.time()
            print("Finished receiving (" + str(time2 - time1) + "s)")
            f = open(args.D + str(time1) + ".wav" , "wb")
            f.write(buffer)
            f.close()
            sys.exit()


def main():
    parser = argparse.ArgumentParser(description= "Data Aggregator for Wired/Wireless ESP Audio Sensors")
    
    parser.add_argument("-D", metavar= "Destination Files", action= "store", required= True, help= "Destination for recieved files")
    parser.add_argument('-A', metavar= "IP Address", action= "store", required= True, help = "IP-Adress to be used by this device")
    parser.add_argument("-I", metavar= "Input Source", action= "store", choices=["serial","wifi"], default= "wifi", help= "Input source. Supports 'serial.' and 'wifi'.")
    parser.add_argument('-P', metavar= "Port", action= "store", type = int, default = 5001, required= False, help = "Port to open up TCP server on. Defaults to port 5001")
    print("Starting...")
    try:
        args = parser.parse_args()
    except:
        sys.exit()
    sock = create_socket(args)
    #sock2 = create_socket2(args)
    #pid2 = os.fork()
    #if pid2 == 0 :
    listen_traffic(sock, args)
    #else:
    #    listen_traffic(sock2, args)
    
if __name__ == "__main__":
    main()