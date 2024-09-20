import messages, threading, socket, os, argparse, psutil, random, time

#Testkommentar

def upperConfigPoll(args, controlPID):
    try:
        print("Polling Config")
        clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        clientSocket.connect((random.choice(messages.Connection.config.upper),args.T))
        print(clientSocket)
        connection = messages.Connection(clientSocket, controlPID, args.A, args.D, args.T)
        connection.requestConfig()
    except:
        raise
        
def connectToNegotiator(args, controlPID):
    try:
        clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        clientSocket.connect((args.E,args.T))
        connection = messages.Connection(clientSocket, controlPID, args.A, args.D, args.T)
        connection.joinNetwork()
        while(len(messages.Connection.config.upper) == 0):
            print("No Uppers, waiting!")
            time.sleep(5)
    except:
        raise

def handleIncoming(args, serverSocket, parentPID):
    parentProcess = psutil.Process(parentPID)
    print("Handling incoming on " + str(args.P))
    while parentProcess.status()!= psutil.STATUS_ZOMBIE:
        print("Loop")
        try:
            serverSocket.listen()
            connSocket,addr = serverSocket.accept()
            print("Listen returns new connected socket")
            connection = messages.Connection(connSocket, controlPID, args.A, args.D, args.T)
            connection.handleNewIncoming(0)
        except:
            raise

def pollOnIntervall(args, controlPID, intervall):
    parentProc = psutil.Process(controlPID)
    while parentProc.status()!= psutil.STATUS_ZOMBIE:
        upperConfigPoll(args, controlPID)
        time.sleep(intervall)
        
if __name__ == "__main__":
    controlPID = os.getpid()
    parser = argparse.ArgumentParser(description= "Data Aggregator for Wired/Wireless ESP Audio Sensors")
    
    # Required arguments
    parser.add_argument("-D", metavar="Destination Files", action="store", required=True, help="Destination for received files")
    parser.add_argument("-A", metavar="IP Address", action="store", required=True, help="IP address to be used by this device")
    parser.add_argument("-P", metavar="Port", action="store", type=int, default=5001, required=False, help="Port to open up TCP server on. Defaults to port 5001")
    parser.add_argument("-T", metavar="Target Port", action="store", type=int, default=5001, required=False, help="Port to connect to upper instance, defaults to 5001")
    parser.add_argument("-I", metavar="Input", action="store", default="./", required=False, help="Path to find data to send in")

    
    # Mutually exclusive options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-S", action="store_true", help="Indicates if device is main server")
    group.add_argument("-U", metavar="Upper", action="store", help="Initial IP to connect to and get config from, in case the device is the first one on its peer layer")
    group.add_argument("-E", metavar="peer address", action="store", help="Address of the negotiator peer")

    args = parser.parse_args()
    
    
    print("Starting...")
    #self, connsock, upperIP, parentProcess, ownIP, path
    serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    serverSocket.bind((args.A,args.P))
    messages.Connection.config.peer = [args.A]
    #Upper -> First device in layer
    if args.U != None:
        print("Is first device in layer")
        messages.Connection.config.upper = [args.U]
        t2 = threading.Thread(target=upperConfigPoll,args=(args,controlPID))
        t3 = threading.Thread(target=handleIncoming,args=(args,serverSocket, controlPID))
        t2.setDaemon(True)
        t3.start()
        t2.start()
        t2.join()
    #Peer -> Get Config from Peer
    elif args.E != None:
        print("Establishing connection via peer")
        t3 = threading.Thread(target=handleIncoming,args=(args,serverSocket, controlPID))
        t1 = threading.Thread(target=connectToNegotiator,args=(args,controlPID))
        t2 = threading.Thread(target=upperConfigPoll,args=(args,controlPID))
        t1.setDaemon(True)
        t2.setDaemon(True)
        t3.start()
        t1.start()
        t1.join()
        t2.start()
        t2.join()
    #Runs as server
    elif args.S:
        print("Running as main Server")
        messages.Connection.path = args.D
        handleIncoming(args,serverSocket, controlPID)
        
    else:
        raise AttributeError
    print("Connection Done, starting poll on intervall")
    if not args.S:
        while True:
            t2 = threading.Thread(target=pollOnIntervall,args=(args,controlPID,300))
            files = os.listdir(args.I)
            if len(files) != 0:
                for file in files:
                    clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                    clientSocket.connect((random.choice(messages.Connection.config.upper),args.T))
                    connection = messages.Connection(clientSocket, controlPID, args.A, args.D, args.T)
                    connection.createSessionMessage("20")
                    f = open(args.I + "/" + file,"rb")
                    data = f.read()
                    if file.endsWith(".wav"):
                        dataType = bytes.fromhex("01")
                    elif file.endswith(".csv"):
                        dataType = bytes.fromhex("02")
                    else:
                        dataType = bytes.fromhex("03")
                    sourcemac = bytes.fromhex(file[0:6])    
                    timestamp = file[6:14]
                    connection.packAndSendData(sourcemac,timestamp,dataType,data)
                    f.close()
                    os.remove(f)
            time.sleep(15)


