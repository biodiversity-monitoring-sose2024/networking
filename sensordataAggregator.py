import socket, argparse, sys, time, os, psutil
import messages as msg


def sendMessage(tcpsocket,message):
    try:
        tcpsocket.sendall(message)
        response,duration = recvMessage(tcpsocket , )
        return response
    except Exception:
        raise msg.MissingACKError
    
def awaitACK(tcpsocket,message)
    


def recvMessage(tcpsocket, parentProcess):
    time1 = time.time()
    try: 
        size = tcpsocket.recv(4)
        buffer = bytearray()
        while len(buffer) < size:
            if (time.time()-time1) > 300:
                raise TimeoutError 
            if (parentProcess.status()== psutil.STATUS_ZOMBIE):
                tcpsocket.close()
                sys.exit()
            data = tcpsocket.recv(262144)
            buffer = buffer + data
        
        return buffer, time.time()-time1
    except msg.ReceivedRSTMessageError:
        raise
    except msg.WrongMessageLengthError:
        raise
    except SystemExit:
        sys.exit()
    
def create_socket(args):
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.bind((args.A, args.P))
    return tcp_sock

def listen_traffic(sock, args, controlPID):
    while True :
        print("Listening...")
        sock.listen()
        connSock, addr = sock.accept()
        controlPID = os.getpid()
        parentProcess = psutil.Process(controlPID)
        pid = os.fork()
        if (pid == 0):
            (buffer, duration) = recvMessage(connSock, controlPID)
            print("Message received in {} seconds".format(duration))
            try:
                (nodeID,timestamp,dataSize,soundfile) = msg.decode(buffer)
            except msg.WrongMessageLengthError:
                connSock.send(msg.RST)
                print(msg.WrongMessageLengthError.message)
            except Exception as e:
                connSock.send(msg.RST)
            
            f = open(args.D + str(timestamp) + ".wav" , "wb")
            f.write(soundfile)
            f.close()
            connSock.send(msg.ACK)
            connSock.disconnect()
            connSock.close()
            sys.exit()


def main():
    controlPID = os.getpid()
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
    listen_traffic(sock, args, controlPID)
    
if __name__ == "__main__":
    main()