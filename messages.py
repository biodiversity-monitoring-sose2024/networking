import struct

class WrongMessageLengthError(Exception):
    
    def __init__(self, expectedLength,gottenLength):
        super.__init__("Wrong message length (expected {} gotten {})!".format(str(expectedLength),str(gottenLength)))

ACK = bytes.fromhex("0x0000000101")
RST = bytes.fromhex("0x0000000100")

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
        "0x02": "!h",#Blocked/Busy: 2B(Expected time of business)
        "0x03": "!qhh",#Config response 8B(Next scheduled timeslot),2B(Next-Level-Address-Lengths),2B(Own-Level-Address-Length),Variable(NLA),Variable(OLA)
        "0x10": "!ccc",#Hello Message 1B(Powerlevel),1B(Memory),1B(NextOPCODE)
        "0x20": "!cqi",#Data Message 1B(NodeID), 8B(Timestamp), 4B(Size of Data), Variable(data) 
        "0x30": "!c",#Config Request 1B(NodeID)
        "0xff": "!cc" #Event 1B(nodeID), 1B(event type), variable(Additional data)
    }"""

def decode(message):
    opcode = hex(message[0])
    match opcode:
        case "0x02":
            data = struct.unpack("!h",message[1:])
            try:
                checkLength(message,(1,2))
            except:
                raise
            return data
        case "0x03":
            (timeslot,nextLevelAddrLen,ownLevelAddrLen) = struct.unpack("!qhh",message[1:14])
            listOfAddressesNL = struct.iter_unpack("4B",message[13:13+nextLevelAddrLen])
            listOfAddressesOL = struct.iter_unpack("4B",message[13:13+ownLevelAddrLen])
            try:
                checkLength(message,(1,8,2,2,nextLevelAddrLen,ownLevelAddrLen))
            except:
                raise
            return(timeslot,nextLevelAddrLen,ownLevelAddrLen,listOfAddressesNL,listOfAddressesOL)
        case "0x10":
            (powerlevel,memory,nextOpcode) = struct.unpack("3c",message[1:])
            try:
                checkLength(message,(1,1,1,1))
            except:
                raise
            return (powerlevel,memory,nextOpcode)
        case "0x20":
            (nodeID,timestamp,dataSize) = struct.unpack("!cqi",message[1:15])
            try:
                checkLength(message,(1,1,8,4,dataSize))
            except:
                raise
            data = message[15:]
            return (nodeID,timestamp,dataSize,data) 
        case "0x30":
            try:
                checkLength(message,(1,1))
            except:
                raise
            (nodeID) = struct.unpack("!c",message[1])
            return(nodeID)
        case "0xff":
            try:
                checkLength(message,(1,1))
            except:
                raise 
            (eventID) = struct.unpack("!c",message[1])
            return (eventID,message[2:])

def encode(opcode,data):
    bOpcode = bytes.fromhex(opcode)
    match opcode:
        case "0x02":
            return(struct.pack("!ch",bOpcode,data[1]))
        case "0x03":
            (timeslot,nlal,olal,nla,ola) = data
            header = struct.pack("!ccqhh",bOpcode,timeslot,nlal,olal)
            nlaB = ipListToBytes(nla)
            olaB = ipListToBytes(ola)
            return(header + nlaB , olaB)
        case "0x10":
            return(struct.pack("!cccc",bOpcode,data))
        case "0x20":
            (nodeID,timestamp,dataLen, sounddata) = data
            return(struct.pack("!ccqi",bOpcode,nodeID,timestamp,dataLen) + sounddata)
        case "0x30":
            return(struct.pack("!cc", bOpcode, data))
        case "0xff":
            (nodeID, eventID, additionals) = data
            return(struct.pack("!ccc"), bOpcode, nodeID, eventID + additionals)
        
        
            
if __name__ == "__main__":
    addrs = ["192.168.178.32","192.168.178.33","192.168.178.34"]
    print("Hello")
    bytes = ipListToBytes(addrs)
    #for byte in bytes:
    #    print(int.from_bytes(byte,"big"))
    ips = byteListToIp(bytes)
    print(ips)