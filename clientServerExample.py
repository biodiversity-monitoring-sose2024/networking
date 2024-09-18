import messages, threading, socket, os, argparse, psutil, random, time

def passiveIncomingListener(args):
    
    return

def upperConfigPoll(args, controlPID, intervall):
    try:
        parentProc = psutil.Process(controlPID)
        print("Polling Config")
        while parentProc.status()!= psutil.STATUS_ZOMBIE:
            clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            clientSocket.connect((random.choice(messages.Connection.globalConfig[0]),args.T))
            print(clientSocket)
            connection = messages.Connection(clientSocket, controlPID, args.A, args.D, args.T)
            connection.requestConfig()
            time.sleep(intervall)
    except:
        raise
        
def connectToNegotiator(args, controlPID):
    try:
        clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        clientSocket.connect((args.E,args.T))
        connection = messages.Connection(clientSocket, controlPID, args.A, args.D, args.T)
        connection.joinNetwork()
    except:
        raise

def handleIncoming(args, serverSocket):
    print("Handling incoming on " + str(args.P))
    while True:
        try:
            serverSocket.listen()
            connSocket,addr = serverSocket.accept()
            print("Listen returns new connected socket")
            connection = messages.Connection(connSocket, controlPID, args.A, args.D, args.T)
            connection.handleNewIncoming(0)
        except:
            raise

if __name__ == "__main__":
    controlPID = os.getpid()
    parser = argparse.ArgumentParser(description= "Data Aggregator for Wired/Wireless ESP Audio Sensors")
    
    parser.add_argument("-D", metavar= "Destination Files", action= "store", required= True, help= "Destination for recieved files")
    parser.add_argument('-A', metavar= "IP Address", action= "store", required= True, help = "IP-Adress to be used by this device")
    parser.add_argument("-I", metavar= "Input Source", action= "store", choices=["serial","wifi"], default= "wifi", help= "Input source. Supports 'serial.' and 'wifi'.")
    parser.add_argument('-P', metavar= "Port", action= "store", type = int, default = 5001, required= False, help = "Port to open up TCP server on. Defaults to port 5001")
    parser.add_argument('-U', metavar= "Upper", action= "store", required= False, default = None, help = "Initial IP to connect to and get config from, in case the device is the first one on its peer layer")
    parser.add_argument('-T', metavar= "Target Port", action= "store", type = int, default = 5001, required= False, help = "Port to connect to upper instance, defaults to 5001")
    parser.add_argument('-S', metavar= "Is Server", action= "store", type = bool, default = False, required= False, help = "Indicates if device is  main server")
    parser.add_argument('-E', metavar= "peer address", action= "store", required= False, default = None, help = "Address of the negotiator peer")
    
    args = parser.parse_args()
    
    print("Starting...")
    #self, connsock, upperIP, parentProcess, ownIP, path
    serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    serverSocket.bind((args.A,args.P))
    messages.Connection.globalConfig[1] = [args.A]
    #Upper -> First device in layer
    if args.U != None:
        print("Is first device in layer")
        messages.Connection.globalConfig[0] = [args.U]
        t2 = threading.Thread(target=upperConfigPoll,args=(args,controlPID,300))
        t2.setDaemon(True)
        t2.start()
    #Peer -> Get Config from Peer
    elif args.E != None:
        print("Establishing connection via peer")
        t1 = threading.Thread(target=connectToNegotiator,args=(args,controlPID))
        t2 = threading.Thread(target=upperConfigPoll,args=(args,controlPID,300))
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()
    #Runs as server
    elif args.S:
        print("Running as main Server")
    else:
        raise AttributeError
    handleIncoming(args,serverSocket)
    
    
    