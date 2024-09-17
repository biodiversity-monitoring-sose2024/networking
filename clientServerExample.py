import messages, threading, socket, os, argparse, psutil, random, time

def passiveIncomingListener(args):
    
    return

def upperConfigPoll(args, parentPID, intervall):
    try:
        while parentPID.status()== psutil.STATUS_ZOMBIE:
            clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            connSocket = clientSocket.connect((random.choice(messages.Connection.globalConfig[0]),args.T))
            connection = messages.Connection(connSocket, controlPID, args.A, args.D)
            connection.requestConfig()
            time.sleep(intervall)
    except:
        raise
        
def connectToNegotiator(args, parentPID):
    try:
        clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        connSocket = clientSocket.connect(args.E,args.T)
        connection = messages.Connection(connSocket, controlPID, args.A, args.D)
        connection.joinNetwork()
    except:
        raise

def handleIncoming(args, serverSocket):
    while True:
        try:
            serverSocket.listen()
            connSocket = serverSocket.accept()
            connection = messages.Connection(connSocket, controlPID, args.A, args.D)
            connection.handleNewIncoming()
        except:
            raise
        return

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
    serverSocket.bind((args.A,args.P))
    if args.U != None:
        messages.Connection.globalConfig[0] = [args.U]
        
    elif args.E != None:
        t1 = threading.Thread(target=connectToNegotiator,args=(args,controlPID))
    elif args.S:
        print("Running as main Server")
    else:
        raise AttributeError
    
    t2 = threading.Thread(target=upperConfigPoll,args=(args,300))
    handleIncoming(args,serverSocket)
    
    
    