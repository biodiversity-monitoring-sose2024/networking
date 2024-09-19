import struct, uuid, sys, psutil, time, socket

class ReceivedRSTMessageError(Exception):
    pass

class MissingACKError(Exception):
    def __init__(self, message):
        self.message = "Gotten: " + str(message)
        super().__init__(self.message)

    pass

class ReceivedRSTError(Exception):
    pass

class UnexpectedMessageError(Exception):
    def __init__(self, opcode):
        self.message = "Gotten OPCODE: " + str(opcode)
        super().__init__(self.message)
    pass

class OutOfClusterError(Exception):
    pass

class ReceivedBusyError(Exception):
    def __init__(self, duration):
        self.duration = duration
        super().__init__()
    pass

class WrongMessageLengthError(Exception):
    message = ""
    def __init__(self, expectedLength,gottenLength):
        self.message = "Wrong message length (expected {} gotten {})!".format(str(expectedLength),str(gottenLength))
        super().__init__(self.message)

def checkLength(message,lengths):
    if len(message) != sum(lengths):
        raise WrongMessageLengthError(sum(lengths),len(message))
    
def ipListToBytes(ipaddresses):
    result = bytearray()
    for address in ipaddresses:
        numbers = address.split(".")
        for number in numbers:
            result = result + (int(number).to_bytes(1,"big"))
    return result

def byteListToIp(ipBytearray):
    ipsPacked = struct.iter_unpack("4B",ipBytearray)
    resultFinal = []
    for addr in ipsPacked:
        result = []
        for byte in addr:
            result.append(str(byte))
        result = ".".join(result)
        resultFinal.append(result)
    return resultFinal

"""messages= {
        Responses:
        "00": RST
        "01": ACK
        "02": "!h",#Blocked/Busy: 2B(Expected time of business)
        "04": "" #Unknown node
                -Respond by sending a "e0" hello message to a known peer

        Session create:
        "10": "!6ccc",#Session Message 6B(NodeID) 1B(Powerlevel),1B(Memory),1B(NextOPCODE)
        
        Session upper:
        "20": "!6cqci",#Data Message 6B(sourceID), 8B(Timestamp),1B(datatype) 4B(Size of Data), Variable(data)
        "30": "!6c",   #Config Request 6B(NodeID) 
        "03": "!cqh",  #Config response 8B(Next scheduled timeslot),2B(Server addresses Lengths), Variable(SA) <- response
        
        Session peer:
        "e0": "!6cicc" #Hello Message 6B(NodeID), 4B(Own IP), 1B(Powerlevel), 1B(Memory)
        "f0": "!6c"    #Leave message 6B(NodeID)
        "ff": "!6cic"  #Event 6B(NodeID),4B(Own IP), 1B(event type, last bit reserved for ack needed), variable(Additional data)
            
            "01"  Type Network changed: 2B(length peer addresses) variable: peer addresses
                    If the sender does not get an ACK from all his peers, he (after retries), removes unresponsive devices from its
                    dataset and resend a network changed event. He does this as long as there are unresponsive devices. 
                    
                    On receiving: Replace own dataset with received one and send ACK
        
        Terminology:
            Joinee - Device that wants to join the network
            Negotiator - Device that is used as Access Point to the network
            Upper - Devices one level above the Device. Server being the top level
            Peer - Devices on the same level as the Device
            Lower - Devices one level below the Device. Microphone Sensors being the Lowest level.
            Leaver - device that plans on leaving the network.
        
        Connection establishment:
            A Joinee starts his service with at least the IP Adress of the Negotiator, a peer level device 
            and its own IP Address as command line argument. Alternatively he gets a single Upper-IP, 
            in case he is the first device in his layer.
            He then establishes a connection with the network 
            by sending a f0 Hello Message to the negotiator. 
            On receiving a 00 or on timeout message he retries 2 times before exiting.
            On receiving a 02 message he exits with appropiate info for the user.
            The negotiator must add the Joinee to his own dataset, containing his own peers, 
            as well as his upper level addresses
            and send a ff Event message (network changed) with ack needed Type to all his peers afterwards.
            If he timeouts, he sends a f0 into the void and assumes he left the network.
            
            Lower level devices gain information about thir upper level by sending 03 config requests as polling.
            
        Connection teardown:
            The leaver removes himself from his own dataset and sends a ff network changed then exits. 

        Send data:
            The sender initializes the Process by sending a 10 Session Message to the receiver. On ACK he follows with
            a 20 data message. On RST he retries. On Busy he decides whether to use a different receiver or to retry 
            after business ends. On timeout he tries a different receiver.
            
        Config request:
            In regular intervalls a node asks a upper device for a config update. This intervall can vary from device to device
            and should be given to it via command line arguments. It performs the asking by first sending a 10 session message,
            followed by a 30 config request apon receiving a ACK. 
            On Busy or timeout he decides whether to use a different receiver or to retry after business ends. On timeout he tries 
            a different receiver.
            
        
            
            
              
            
        }"""


class Connection():
    #0 = upper, 1 = peer
    globalConfig = [[],[]]
    path = "home/"
    debug = True
    dataTypes = {
        "01": ".wav",
        "02": ".csv",
        "03": ".txt"
     }
    __serverPort = 5001
    
    """def __init__(self, connsock, upperIP, parentProcess, ownIP, path) :
        self.__sock = connsock
        Connection.globalConfig = [[upperIP],[]]
        self.__parentProcess = parentProcess
        self.__macAddr = hex(uuid.getnode())
        self.__ownIP = ownIP
        self.path = path"""
    
    def __init__(self, connsock, parentProcess, ownIP, path, serverPort):
        self.__sock = connsock
        self.__parentID = parentProcess
        self.__parentProcess = psutil.Process(parentProcess)
        self.__ownIP = ownIP
        self.__macAddr = bytes.fromhex("%012x" % uuid.getnode())
        self.__serverPort = serverPort
        self.path = path
    
    __ACK = bytes.fromhex("0000000101")
    __RST = bytes.fromhex("0000000100")

    def fDebug(self,message):
        if self.debug == True:
            print("'\033[93m'[DEBUG] " + message + '\033[0m')

    def __wrapSize(self, message):
        result = len(message).to_bytes(4,"big") + message
        return result

    def __sendACK(self):
        self.__sock.send(self.__ACK)
        self.fDebug("ACK sent!")
        return

    def __sendRST(self):
        self.__sock.send(self.__RST)
        self.fDebug("RST sent!")
        raise ReceivedRSTError
        return

    def __sendBusy(self, time):
        message = self.__wrapSize(bytes.fromhex("02") + time.to_bytes(2,"big"))
        self.fDebug("Busy sent!")
        self.__sock.send(message)

    def __awaitACK(self):
        self.fDebug("Awaiting ACK!")
        response = self.__sock.recv(1024)
        if int.from_bytes(response[0:4],"big") != 1 and int.from_bytes(response[0:],"big") != 3:
            raise MissingACKError(response)
        else:
            opcode = response[4:5].hex()
            match opcode:
                case "00":
                    raise ReceivedRSTError
                case "02":
                    raise ReceivedBusyError(int.from_bytes(response[5:],"big"))
                case "04":
                    raise OutOfClusterError()
                case "01":
                    self.fDebug("Received ACK!")
                    return

    def createSessionMessage(self, opcode):
        #hardcoding power as 100%
        power = 100
        memory = int(psutil.virtual_memory().percent)
        try:
            sessionMessage = encode("10",(self.__macAddr,power.to_bytes(1,"big"), memory.to_bytes(1,"big"),bytes.fromhex(opcode)))
            self.sendMessage(sessionMessage)
            return
        except:
            raise

    def packAndSendData(self, sourcemac, timestamp, dataType, data):
        #hardcoding power as 100%
        power = 100
        dataLen = len(data)
        message = encode("20",(sourcemac,timestamp,dataType,dataLen,data))
        self.sendMessage(message)
    
    def sendMessage(self,encodedData):
        try:
            self.__sendMessage(encodedData,3)
        except:
            raise
        
    def __sendMessage(self, message, tries):
        if tries == 0:
            raise ReceivedRSTError
        
        self.__sock.send(self.__wrapSize(message))
        try:
            self.__awaitACK()
        except ReceivedRSTError:
            self.__sendMessage(message,tries-1)
        except ReceivedBusyError:
            raise
        except Exception:
            raise
 
    def __sendConfigRequest(self, message, tries):
        if tries == 0:
            raise ReceivedRSTError
        
        self.__sock.send(self.__wrapSize(message))
        try:
            self.__awaitConfig()
        except ReceivedRSTError:
            self.__sendMessage(message,tries-1)
        except ReceivedBusyError:
            raise
        except Exception:
            raise
 
    def __sendResponse(self, message):
        
        self.__sock.send(self.__wrapSize(message))
        try:
            self.__awaitACK()
        except Exception:
            raise
                 
    def __sendConfig(self):
        self.__sendResponse(encode("03",(0, len(Connection.globalConfig[1]),Connection.globalConfig[1])))
        self.fDebug("Config sent!")

    def __sendHello(self):
        #power hardcoded as 101 (inf) per cent
        power = 101
        memory = int(psutil.virtual_memory().percent)
        hello = (self.__macAddr, ipListToBytes([self.__ownIP]), power.to_bytes(1, "big"), memory.to_bytes(1, "big"))
        message = encode("e0",hello)
        try:
            self.fDebug("Sending Hello Message!")    
            self.sendMessage(message)
        except:
            raise

    def __recvMessage(self):
        self.fDebug("Trying to receive message")
        time1 = time.time()
        try: 
            size = int.from_bytes(self.__sock.recv(4),"big")
            self.fDebug("Expecting message of size " + str(size))
            buffer = bytearray()
            while len(buffer) < size:
                if (time.time()-time1) > 300:
                    raise TimeoutError 
                if (self.__parentProcess.status()== psutil.STATUS_ZOMBIE):
                    self.__sock.close()
                    sys.exit()
                data = self.__sock.recv(256000)
                #self.fDebug("Received message part: " + data.hex())
                buffer = buffer + data
            self.fDebug("Received message of size " + str(size))
            return buffer, time.time()-time1
        except ReceivedRSTMessageError:
            raise
        except WrongMessageLengthError:
            self.__sendRST()
            raise
        except SystemExit:
            sys.exit()
        except:
            self.fDebug("Exception while receiving, sending RST")
            self.__sendRST()
            raise
    
    def __awaitConfig(self):
        self.fDebug("Awaiting Config!")
        try:
            message = decode(self.__recvMessage()[0])
        except:
            raise
        if message[0] != "03":
            self.fDebug("Leaving: Config answer was not of ff or 01")
            leaveMessage = bytes.fromhex("f0") + self.__macAddr
            self.__sendMessage(leaveMessage)
            raise UnexpectedMessageError
        
        Connection.globalConfig = [Connection.globalConfig[0],[byteListToIp(message[3])]]
        self.fDebug("Config gotten! New Config: " + str(Connection.globalConfig))
        self.__sendACK()
        return
    
    def joinNetwork(self):
        self.fDebug("Attempting to join network!")
        try: 
            self.__establishConnection()
        except:
            raise
    
    def __establishConnection(self): 
        self.fDebug("Establishing Connection!")
        try:
            self.__sendHello()
        except ReceivedRSTError:
            print("Connection establishment failed!")
            sys.exit()
        except:
            raise

    def __sendConfigToAllPeers(self):
        self.fDebug("Sending Config to everyone!")
        id = 1
        data = (self.__macAddr, ipListToBytes([self.__ownIP]) , id.to_bytes(1,"big"), ipListToBytes(Connection.globalConfig[1]))
        for target in Connection.globalConfig[1]:
            if target != self.__ownIP:
                try:
                    clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                    clientSocket.connect((target, self.__serverPort))
                    newConnection = Connection(clientSocket, self.__parentID,self.__ownIP,self.path,self.__serverPort)
                    message = encode("ff", data)
                    newConnection.sendMessage(message)
                except Exception as e:
                    Connection.globalConfig[1].remove(target)
                    self.__sendConfigToAllPeers()
        return
    
    def __receiveNewSession(self, busy): 
      
        try:
            message, duration = self.__recvMessage()
        except:
            raise
        try:
            (opcode, a,b,c,d) = decode(message)
        except:
            (opcode, a,b,c) = decode(message)
        
        if opcode == "e0":
            self.fDebug("Receiving Session Hello!") 
            (opcode, nodeID, targetIP, power, memory) = decode(message)
            ipList = byteListToIp(targetIP)
            Connection.globalConfig[0] = Connection.globalConfig[0] + ipList
            self.fDebug("Received Hello! New Config: " + str(Connection.globalConfig))
            self.__sendACK()
            self.__sendConfigToAllPeers()
            return(False, None)
        
        elif opcode == "ff":
            self.fDebug("Receiving Event!") 
            (opcode,targetIP,eventType,data) = decode(message)
            match eventType:
                        case "01":
                            try:
                                Connection.globalConfig[1] = byteListToIp(data)
                                self.fDebug("Set new Config: " + str(Connection.globalConfig))
                                self.__sendACK()
                            except:
                                raise
            return(False, None)
        

        elif opcode != "10":
            self.__sendRST()
            raise UnexpectedMessageError(opcode)
        else:
            (opcode, nodeID, power, memory, nextOpcode) = decode(message)
            self.fDebug("Receiving new Session!") 
            if busy != 0:
                self.__sendBusy(busy)
                self.__sock.close()
                sys.exit()
            needsValidation = True
            self.fDebug("Expecting " + str(nextOpcode) + " next")
            return (needsValidation,nextOpcode)

    def __validateAfterNewSession(self, announcedMessageType):
        self.fDebug("Validating after Hello!")
        try:
            message = decode(self.__recvMessage()[0])
        except:
            raise
        if message[0] != announcedMessageType:
            raise UnexpectedMessageError(announcedMessageType)
        self.fDebug("Validated after Hello!")
        return message
    
    def requestConfig(self):
        #Powerlevel hardcoded
        memory = int(psutil.virtual_memory().percent)
        power = 100
        sessionHello = encode("10",(self.__macAddr,power.to_bytes(1,"big"), memory.to_bytes(1,"big"),bytes.fromhex("30")))
        self.sendMessage(sessionHello)
        self.fDebug("Requesting Config!")
        message = encode("30",self.__macAddr)
        self.__sendConfigRequest(message, 3)
        self.__sock.shutdown(2)
        self.__sock.close()
        sys.exit()
        
    def handleNewIncoming(self,busy):
        self.fDebug("New TCP Connection received!")
        sessionMessage = self.__receiveNewSession(busy)
        if sessionMessage[0] == True:
            self.__sendACK()
            message = self.__validateAfterNewSession(sessionMessage[1])
            match message[0]:
                case "20":
                    #Data Message
                    (opcode,sourceID,timestamp,dataType,dataSize,data) = message
                    self.fDebug("Received data message!")
                    dataType = Connection.dataTypes[dataType]
                    self.fDebug("Received message has type " + dataType)
                    f = open(Connection.path + "/" + sourceID.hex() + str(timestamp) + dataType , "wb")
                    f.write(data)
                    f.close()
                    self.__sendACK()
                    self.__sock.close()
                    return
                            
                case "30":
                    #Config Request
                    self.fDebug("Received Config request!")
                    self.__sendConfig()
                    return
        else:

            return
   
def decode(message):
    opcode = (message[0:1]).hex()
    match opcode: 
        case "02":
            data = struct.unpack("!h",message[1:])
            try:
                checkLength(message,(1,2))
            except:
                raise
            return (opcode,data)
        
        case "03":
            (timeslot,nextLevelAddrLen) = struct.unpack("!qh",message[1:11])
    
            listOfAddressesNL = message[11:]
            try:
                checkLength(message,(1,8,2,nextLevelAddrLen*4))
            except:
                raise
            return(opcode,timeslot,nextLevelAddrLen,listOfAddressesNL)
        
        case "10":
            (nodeID,powerlevel,memory,nextOpcode) = struct.unpack("6sccc",message[1:10])
            try:
                checkLength(message,(1,6,1,1,1))
            except:
                raise
            return (opcode,nodeID,powerlevel,memory,nextOpcode.hex())
        
        case "20":
            (sourceID,timestamp,dataType,dataSize) = struct.unpack("!6sqci",message[1:20])
            try:
                checkLength(message,(1,6,8,1,4,dataSize))
            except:
                raise
            data = message[20:]
            return (opcode,sourceID,timestamp,dataType.hex(),dataSize,data) 
        
        case "30":
            try:
                checkLength(message,(1,6))
            except:
                raise
            (nodeID) = struct.unpack("!6s",message[1:])
            return(opcode,nodeID)
        
        case "e0":
            try:
                checkLength(message,(1,6,4,1,1))
            except:
                raise
            (nodeID,targetIP,power,memory) = struct.unpack("!6s4scc",message[1:14])
            return(opcode,nodeID,targetIP,power,memory)
        
        case "f0":
            try:
                checkLength(message,(1,6))
            except:
                raise
            (nodeID) = struct.unpack("!6c", message[1:])
            return (opcode,nodeID)
        
        case "ff":
            (nodeID,targetIP,eventType) = struct.unpack("!6s4sc",message[1:12])
            
            return (opcode,targetIP,eventType.hex(),message[12:])
        
        case _:
            raise UnexpectedMessageError(opcode)
            
def encode(opcode,data):
    bOpcode = bytes.fromhex(opcode)
    match opcode:
        case "02":
            return(struct.pack("!ch",bOpcode,data[1]))
        case "03":
            (timeslot,nlal,nla) = data
            header = struct.pack("!cqh",bOpcode,timeslot,nlal)
            nlaB = ipListToBytes(nla)
            return(header + nlaB)
        case "10":
            (nodeID,powerlevel,memory,nextOpcode) = data
            return(struct.pack("!c6sccc",bOpcode, nodeID, powerlevel, memory, nextOpcode))
        case "20":
            (nodeID,timestamp,dataType,dataLen,sounddata) = data
           
            return(struct.pack("!c6sqci",bOpcode,nodeID,timestamp,dataType,dataLen) + sounddata)
        case "30":
            return(struct.pack("!c6s", bOpcode, data))
        case "e0":
            (nodeID,ownIP,powerlevel,memory) = data
            return(struct.pack("!c6s4scc",bOpcode,nodeID,ownIP,powerlevel,memory))
        case "f0":
            return(struct.pack("!c6s",bOpcode,data))
        case "ff":
            try:
                (nodeID, ownIP, eventType, additionals) = data
            except:
                (nodeID, ownIP, eventType) = data
            return(struct.pack("!c6s4sc", bOpcode, nodeID, ownIP, eventType) + additionals)        
            
if __name__ == "__main__":
    addrs = ["192.168.178.32","192.168.178.33","192.168.178.34"]
    print("Hello")
    bytes1 = ipListToBytes(addrs)
    #for byte in bytes:
    #    print(int.from_bytes(byte,"big"))
    ips = byteListToIp(bytes1)
    print(ips)
