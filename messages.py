import struct, uuid, sys, psutil, time, socket

class ReceivedRSTMessageError(Exception):
    pass

class MissingACKError(Exception):
    pass

class ReceivedRSTError(Exception):
    pass

class UnexpectedMessageError(Exception):
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
    result = []
    for address in ipaddresses:
        numbers = address.split(".")
        for number in numbers: 
            result.append(int(number).to_bytes(1,"big"))
    return result

def byteListToIp(bytelist):
    ipsPacked = struct.iter_unpack("4B",b"".join(bytelist))
    resultFinal = []
    for addr in ipsPacked:
        result = []
        for byte in addr:
            result.append(str(byte))
        result = ".".join(result)
        print(result)
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
    
    dataTypes = {
        "01": ".wav",
        "02": ".csv"
     }
    
    """def __init__(self, connsock, upperIP, parentProcess, ownIP, path) :
        self.__sock = connsock
        Connection.globalConfig = [[upperIP],[]]
        self.__parentProcess = parentProcess
        self.__macAddr = hex(uuid.getnode())
        self.__ownIP = ownIP
        self.path = path"""
    
    def __init__(self, connsock, parentProcess, ownIP, path):
        self.__sock = connsock
        self.__parentProcess = parentProcess
        self.__ownIP = ownIP
        self.path = path
    
    __ACK = bytes.fromhex("0000000101")
    __RST = bytes.fromhex("0000000100")

    def __wrapSize(message):
        result = len(message).to_bytes(4,"big") + encode(message)
        return result

    def __sendACK(self):
        self.__sock.send(self.__ACK)
        return

    def __sendRST(self):
        self.__sock.send(self.__RST)
        return

    def __sendBusy(self, time):
        message = self.__wrapSize(bytes.fromhex("02") + time.to_bytes(2,"big"))
        self.__sock.send(message)

    def __awaitACK(self):
        response = self.__sock.recv(1024)
        if int.from_bytes(response[0:5],"big") != 1 and int.from_bytes(response[0:5],"big") != 3:
            raise MissingACKError
        else:
            message = decode(response)
            match message[0]:
                case "00":
                    raise ReceivedRSTError
                case "02":
                    raise ReceivedBusyError(message[1])
                case "04":
                    raise OutOfClusterError()
                case "01":
                    return

    def sendMessage(self, encodedData):
        try:
            self.__sendMessage(self.__sock,encodedData,3)
        except:
            raise
        
    def __sendMessage(self, message, tries):
        if tries == 0:
            raise ReceivedRSTError
        self.__sock.send(self.__wrapSize(message))
        try:
            self.__awaitACK(self.__sock)
        except ReceivedRSTError:
            self.__sendMessage(self.__sock,message,tries-1)
        except ReceivedBusyError:
            raise
        except Exception:
            raise
 
    def __sendResponse(self, message):
        
        self.__sock.send(self.__wrapSize(message))
        try:
            self.__awaitACK(self.__sock)
        except Exception:
            raise
                 
    def __sendConfig(self):
        self.__sendResponse(encode("03",Connection.globalConfig))
        try:
            self.__awaitACK(self.__sock)
        except:
            raise
        return

    def __sendHello(self):
        #power hardcoded as 101 (inf) per cent
        power = 101
        memory = int(psutil.virtual_memory().percent.floor())
        hello = self.__macAddr + ipListToBytes([self.__ownIP]) + power.to_bytes(1, "big") + memory.to_bytes(1, "big")
        try:    
            self.__sendMessage(hello)
        except:
            raise

    def __recvMessage(self):
        time1 = time.time()
        try: 
            size = self.__sock.recv(4)
            buffer = bytearray()
            while len(buffer) < size:
                if (time.time()-time1) > 300:
                    raise TimeoutError 
                if (self.__parentProcess.status()== psutil.STATUS_ZOMBIE):
                    self.__sock.close()
                    sys.exit()
                data = self.__sock.recv(262144)
                buffer = buffer + data
                self.__sendACK()
            return buffer, time.time()-time1
        except ReceivedRSTMessageError:
            raise
        except WrongMessageLengthError:
            raise
        except SystemExit:
            sys.exit()
     
    def __awaitConfig(self):
        try:
            message = decode(self.__recvMessage())
        except:
            raise
        self.__awaitConfig()
        if message[0] != "ff" or message[1] != "01":
            leaveMessage = bytes.fromhex("f0") + self.__macAddr
            self.__sendMessage(leaveMessage)
            raise UnexpectedMessageError
        Connection.globalConfig = [Connection.globalConfig[0],[byteListToIp(message[2])]]
        return
    
    def joinNetwork(self):
        try: 
            self.__establishConnection()
        except:
            raise
    
    def __establishConnection(self): 
        
        try:
            self.__sendHello()
        except ReceivedRSTError:
            print("Connection establishment failed!")
            sys.exit()
        except:
            raise
        try:
            self.__awaitConfig()
            return
        except:
            raise
    
    def __receiveHello(self, busy):
        try:
            message = self.__recvMessage(self)
        except:
            raise
        (opcode,nodeID,targetIP,power,memory) = decode(message)
        if opcode != "10":
            self.__sendRST()
            raise UnexpectedMessageError
        else:
            if busy != 0:
                self.__sendBusy(busy)
                self.__sock.close()
                sys.exit()
            Connection.globalConfig[0] = Connection.globalConfig[0] + targetIP
            return 

    def __validateAfterHello(self, announcedMessageType):
        self.__sendACK()
        try:
            message = decode(self.__recvMessage())
        except:
            raise
        if message[0] != announcedMessageType:
            raise UnexpectedMessageError
        return message
    
    def requestConfig(self):
        message = encode("ff",self.__macAddr)
        self.sendMessage(message)
        self.__awaitConfig()
        self.__sock.disconnect()
        self.__sock.close()
        sys.exit()
        
    def handleNewIncoming(self,busy):
        sessionMessage = self.__receiveHello(busy)
        message = self.__validateAfterHello(sessionMessage[3])
        match message[0]:
            case "20":
                #Data Message
                data = self.__recvMessage()
                dataType = Connection.dataType[message[2]]
                f = open(Connection.path + str(message[1]) + dataType , "wb")
                f.write(data)
                f.close()
                self.__sock.disconnect()
                self.__sock.close()
                sys.exit()
                           
            case "30":
                #Config Request
                self.__sendConfig()
                
            case "ff":
                #Event Message
                match message[3]:
                    case "01":
                        try:
                            Connection.globalConfig[1] = byteListToIp(message[4])
                        except:
                            raise

      
def decode(message):
    opcode = hex(message[0])
    match opcode: 
        case "02":
            data = struct.unpack("!h",message[1:])
            try:
                checkLength(message,(1,2))
            except:
                raise
            return (opcode,data)
        
        case "03":
            (timeslot,nextLevelAddrLen,ownLevelAddrLen) = struct.unpack("!qhh",message[1:14])
            listOfAddressesNL = struct.iter_unpack("4B",message[13:13+nextLevelAddrLen])
            try:
                checkLength(message,(1,8,2,nextLevelAddrLen))
            except:
                raise
            return(opcode,timeslot,nextLevelAddrLen,listOfAddressesNL)
        
        case "10":
            (nodeID,powerlevel,memory,nextOpcode) = struct.unpack("6ccc",message[1:])
            try:
                checkLength(message,(1,6,1,1,1))
            except:
                raise
            return (opcode,nodeID,powerlevel,memory,nextOpcode)
        
        case "20":
            (sourceID,timestamp,dataType,dataSize) = struct.unpack("!6cqci",message[1:21])
            try:
                checkLength(message,(1,6,8,1,4,dataSize))
            except:
                raise
            data = message[21:]
            return (opcode,sourceID,timestamp,dataType,dataSize,data) 
        
        case "30":
            try:
                checkLength(message,(1,6))
            except:
                raise
            (nodeID) = struct.unpack("!6c",message[1:])
            return(opcode,nodeID)
        
        case "e0":
            try:
                checkLength(message,(6,4,1,1))
            except:
                raise
            (nodeID,targetIP,power,memory) = struct.unpack("!6cicc",message[1:14])
            return(opcode,nodeID,targetIP,power,memory)
        
        case "f0":
            try:
                checkLength(message,(6,4,1,1))
            except:
                raise
            (nodeID) = struct.unpack("!6c")
            return (opcode,nodeID)
        
        case "ff":
            (nodeID,targetIP,eventType,dataLength) = struct.unpack("!6c4cc",message[1:13])
            try:
                checkLength(message,(1,6,4,1,dataLength))
            except:
                raise
            return (opcode,targetIP,eventType,message[2:])

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
            return(struct.pack("!c6ccc",bOpcode, powerlevel, memory, nextOpcode))
        case "20":
            (nodeID,timestamp,dataType,dataLen,sounddata) = data
            return(struct.pack("!c6cqci",bOpcode,nodeID,timestamp,dataType,dataLen) + sounddata)
        case "30":
            return(struct.pack("!cc", bOpcode, data))
        case "e0":
            (nodeID,ownIP,powerlevel,memory) = data
            return(struct.pack("!6c4ccc"),bOpcode,nodeID,ownIP,powerlevel,memory)
        case "f0":
            return(struct.pack("!6c",data))
        case "ff":
            try:
                (nodeID, eventID, eventType, additionals) = data
            except:
                (nodeID, eventID, eventType) = data
            return((struct.pack("!c6cic"), bOpcode, nodeID, eventID, eventType) + additionals)
       
        
            
if __name__ == "__main__":
    addrs = ["192.168.178.32","192.168.178.33","192.168.178.34"]
    print("Hello")
    bytes1 = ipListToBytes(addrs)
    #for byte in bytes:
    #    print(int.from_bytes(byte,"big"))
    ips = byteListToIp(bytes1)
    print(ips)
