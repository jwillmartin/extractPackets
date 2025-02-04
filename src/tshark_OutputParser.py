import sys
from csv import reader, writer

def isValidMsgSize(testMsg, lenBytes):
    if (lenBytes > 255):
        msgFrame = LONG_FRAME
        frameSize = int(testMsg[1:msgFrame], 16)
        bytesSize = int(len(testMsg[msgFrame:]) / 2)
    else: 
        msgFrame = SHORT_FRAME
        frameSize = int(testMsg[:msgFrame], 16)
        bytesSize = int(len(testMsg[msgFrame:]) / 2)

    if (bytesSize == frameSize):
        return True
    else:
        print(frameSize, bytesSize)
        return False

def isValidPSID(msgID):
    for i in psid:
        if (msgID == psid[i]):
            print(msgID, psid[i])
            return True
    return False

inFile = sys.argv[1]
payloadType=sys.argv[3]
print("Payload Type: " + payloadType)
fileName = inFile.split(".")

with open(fileName[0]+'.csv') as read_obj, \
open(fileName[0]+'_payload.csv', 'w', newline='') as write_obj:
    csv_reader = reader(read_obj)
    csv_writer = writer(write_obj)

    msgID = {
        'map' : '0012',
        'spat': '0013',
        'bsm' : '0014',
        'psm' : '0020',
        'sdsm': '0029',
        'tim' : '001f',
        'req' : '00f0',
        'res' : '00f1',
        'mop' : '00f2',
        'mom' : '00f3',
        'tcr' : '00f4',
        'tcm' : '00f5'
    }

    psid = {
        'bsm':           '0020',
        'psm':           '0027',
        'intersection':  '8002',
        'travelerAlert': '8003',
        'sdsm':          '8010',
        'test':          'bfee'
    }

    SHORT_FRAME = 2
    LONG_FRAME =  4

    for row in csv_reader:
        index = {}
        smallerIndex = 10000

        #remove newlines for ascii
        if( payloadType == "ascii" ):
            row[1] = row[1].replace("\\n","")

        for k in msgID:
            if msgID[k] in row[1]:
                index[k] = row[1].find(msgID[k])
                if index[k] < smallerIndex:
                    smallerIndex = index[k]
                    msg = row[1][smallerIndex:]
                    testMsg = msg[4:]
                    lenBytes = len(testMsg)
                    # if (isValidMsgSize(testMsg, lenBytes) == False):
                    #     print(msgID[k]+testMsg)
                    #     continue
                    # else:
                    if (isValidPSID(msgID[k]) == False):
                        validMsg = msg
                        # print(validMsg)
                        csv_writer.writerow([row[0],validMsg])
                        break
                    else: continue
