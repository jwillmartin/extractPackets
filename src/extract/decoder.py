#!/usr/bin/env python
from binascii import unhexlify
import J2735_202409
import sys
import csv
import numpy
import datetime

def extract_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results

def convID(id, length):
    id = id.hex()
    i = 0
    if (length == 8):
        while(i<21):
            id = id[:i+2] + " " + id[i+2:]
            i += 3
    else:
        while(i<45):
            id = id[:i+2] + " " + id[i+2:]
            i += 3

    id = list(id.split(" "))

    for x in range(len(id)):
        inted = int(id[x], 16)
        id[x] = inted

    return id

def writeSpatHeader():
    columnHeaderString="packetTimestamp,intersectionID"
    columnHeaderString = columnHeaderString + ",phase" + ",state" + ",countdown\n"
    fout.write(columnHeaderString)

def writeMessageHeader(msgType):
    if (msgType == "BSM") :
        fout.write("packetTimestamp,bsm_id,secMark,latency,latitude,longitude,speed(m/s),heading,elevation(m),accel_long(m/s^2)\n")
    elif (msgType=="MAP"):
        fout.write("packetTimestamp,intersectionID,latitude,longitude,laneWidth,signalGroupID\n")
    elif (msgType=="SDSM"):
        fout.write("packetTimestamp,datetime,msgCnt,sourceId,latitude,longitude,heading,objectType,payload\n")
    elif (msgType=="TIM"):
        fout.write("packetTimestamp,msgCnt,packetId,timestamp,frametype,lat,long,content\n")
    elif (msgType=="Mobility Request"):
        fout.write("packetTimestamp,hostStaticId,hostBSMId,planId,strategy,planType,urgency,strategyParams,trajectoryStart,trajectory,expiration\n")
    elif (msgType=="Mobility Response"): 
        fout.write("packetTimestamp,hostStaticId,hostBSMId,planId,urgency,isAccepted\n")
    elif (msgType=="Mobility Path"): 
        fout.write("packetTimestamp,hostStaticId,hostBSMId,planId,location,trajectory\n")
    elif (msgType=="Mobility Operation"): 
        fout.write("packetTimestamp,hostStaticId,hostBSMId,planId,strategy,operationParams:\n")
    elif (msgType=="Traffic Control Request") :
        fout.write("packetTimestamp,reqid,reqseq,scale,bounds:\n")
    elif (msgType=="Traffic Control Message"): 
        fout.write("packetTimestamp,reqid,reqseq,msgtot,msgnum,id,updated,label,tcID,vclasses...,schedule...,detail...,geometry...\n")
    elif (msgType == "SPAT"):
        writeSpatHeader()


if (len(sys.argv) < 4) :
    print("Incomplete Arguments")
    exit(1)


fp1 = open(sys.argv[1],'r')
fout = open(sys.argv[2],'w')
msgType = sys.argv[3].strip(' \n')
msgid = sys.argv[4]

writeMessageHeader(msgType)


fp = csv.reader(fp1,delimiter=',')
list1 = list(fp)

latency_array = []
prevSpatTimestamp = 0


for dt in list1:

    if (dt[1][0:4]==msgid):
        msg = J2735_202409.MessageFrame.MessageFrame
        try:
            msg.from_uper(unhexlify(dt[1]))
        except:
            continue

        payload = msg()
        if not payload or not isinstance(payload, dict) or 'value' not in payload:
            continue
        try:
            mval = payload['value'][1]
        except Exception:
            continue
        
        # SPAT
        if (msgid == "0013"):
            intersectionID = mval['intersections'][0]['id']['id']
            instersectionPhaseArray = mval['intersections'][0]['states']
            
            # used later when exact number or phases is known
            numPhases = 2 # use number of desired phases
            spatPhaseArray = [None] * numPhases

            for phase in range(len(instersectionPhaseArray)):
                currentPhase = mval['intersections'][0]['states'][phase].get('signalGroup')
                currentState = str(mval['intersections'][0]['states'][phase]['state-time-speed'][0]['eventState'])
                minEndTime = mval['intersections'][0]['states'][phase]['state-time-speed'][0]['timing']['minEndTime']
                maxEndTime = mval['intersections'][0]['states'][phase]['state-time-speed'][0]['timing']['maxEndTime']
                if (minEndTime == 36001):
                    timeEndSec = maxEndTime/6
                else:
                    timeEndSec = minEndTime/6

                spatString = str(dt[0]) + "," + str(intersectionID) + "," + str(currentPhase) + "," + str(currentState) + "," + str(timeEndSec) + "\n"
                fout.write(spatString)

        # MAP
        elif (msgid == "0012"):
            intersectionID = mval['intersections'][0]['id']['id']
            #if intersectionID == intersection:
            lat = mval['intersections'][0]['refPoint']['lat']
            longstr = mval['intersections'][0]['refPoint']['long']
            laneWidth = mval['intersections'][0]['laneWidth']
            signalGroupID = mval['intersections'][0]['laneSet'][0]['connectsTo'][0]['signalGroup']

            fout.write(str(dt[0])+','+str(intersectionID)+','+str(lat/10000000.0)+','+str(longstr/10000000.0)+','+str(laneWidth)+','+str(signalGroupID)+'\n')
        
        # BSM
        elif (msgid == "0014"):
            bsmId = mval['coreData']['id'].hex()
            lat= mval['coreData']['lat']
            longstr = mval['coreData']['long']
            speed = mval['coreData']['speed']
            elevation = mval['coreData']['elev']
            secMark = mval['coreData']['secMark']
            heading = mval['coreData']['heading']
            speed_converted = speed*0.02 #m/s
            accel_long = mval['coreData']['accelSet']['long']
            accel_long_converted = accel_long*0.01 #m^s^2
            
            packet_timestamp = datetime.datetime.fromtimestamp(int(float(dt[0])))
            roundDownMinTime = datetime.datetime(packet_timestamp.year,packet_timestamp.month,packet_timestamp.day,packet_timestamp.hour,packet_timestamp.minute).timestamp()
            packetSecondsAfterMin = (float(dt[0]) - roundDownMinTime)
            latency = packetSecondsAfterMin*1000 - secMark
            if (latency < 0) :
                #print("[!!!] Minute mismatch")
                latency = latency + 60000
            #print("latency: " + str(latency))
            
            latency_array.append(latency)
            
            fout.write(str(dt[0])+','+str(bsmId)+','+str(secMark)+','+str(latency)+','+str(lat/10000000.0)+','+str(longstr/10000000.0)+','+str(speed_converted)+','+str(heading)+','+str(accel_long_converted)+','+ str(elevation)+'\n')

        # SDSM
        elif (msgid == "0029"):
            dateTime = datetime.datetime.fromtimestamp(int(float(dt[0])), tz=datetime.timezone.utc)
            msgCnt = mval['msgCnt']
            sourceID = mval['sourceID'].hex()
            refLat = mval['refPos']['lat']/10000000.0
            refLong = mval['refPos']['long']/10000000.0
            heading = mval['objects'][0]['detObjCommon']['heading']
            objectType = mval['objects'][0]['detObjCommon']['objType']

            fout.write(str(dt[0]) + ',' + str(dateTime) + ',' + str(msgCnt) + ',' + str(sourceID) + ',' + str(refLat) + ',' + str(refLong) + ',' + str(heading) + ',' + str(objectType) + ',' + str(dt[1]) + '\n')

        # TIM
        elif (msgid == "001f"):
            msgCnt = mval['msgCnt']
            packetID = mval['packetID'].hex()
            timestamp = mval['timeStamp']
            frameType = mval['dataFrames'][0]['frameType']
            content = mval['dataFrames'][0]['content']
            lat = mval['dataFrames'][0]['regions'][0]['anchor']['lat']
            long = mval['dataFrames'][0]['regions'][0]['anchor']['long']

            fout.write(str(dt[0]) + ',' + str(msgCnt) + ',' + str(packetID) + ',' + str(timestamp) + ',' + str(frameType) + ',' + str(lat) + ',' + str(long) + ',' + str(content) + '\n')

        # Test Messages
        elif (msgid == "00f0") :
            hostStaticId = mval['header']['hostStaticId']
            hostBSMId = mval['header']['hostBSMId']
            planId = mval['header']['planId']
            strategy = mval['body']['strategy']
            planType = mval['body']['planType']
            urgency = mval['body']['urgency']
            strategyParams = mval['body']['strategyParams']
            trajectoryStart = mval['body']['trajectoryStart']
            trajectory = mval['body']['trajectory']
            expiration = mval['body']['expiration']

            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(strategy)+','+str(planType)+','+str(urgency)+''+str(strategyParams)+''+str(trajectoryStart)+''+str(trajectory)+''+str(expiration)+''+'\n')

        elif (msgid == "00f1") :
            hostStaticId = mval['header']['hostStaticId']
            hostBSMId = mval['header']['hostBSMId']
            planId = mval['header']['planId']
            urgency = mval['body']['urgency']
            isAccepted = mval['body']['isAccepted']

            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(urgency)+','+str(isAccepted)+'\n')

        elif (msgid == "00f2") :
            hostStaticId = mval['header']['hostStaticId']
            hostBSMId = mval['header']['hostBSMId']
            planId = mval['header']['planId']
            location = mval['body']['location']
            trajectory = mval['body']['trajectory']

            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(location)+','+str(trajectory)+'\n')

        elif (msgid == "00f3") :
            hostStaticId = mval['header']['hostStaticId']
            hostBSMId = mval['header']['hostBSMId']
            planId = mval['header']['planId']
            strategy = mval['body']['strategy']
            operationParams = mval['body']['operationParams']
            
            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(strategy)+','+str(operationParams)+'\n')

        elif (msgid == "00f4") :
            reqid = mval['body'][1]['reqid']
            reqseq = mval['body'][1]['reqseq']
            scale = mval['body'][1]['scale']
            bounds = mval['body'][1]['bounds']

            newReqId = str(convID(reqid, 8)).replace(",", " ")

            fout.write(str(dt[0])+','+newReqId+','+str(reqseq)+','+str(scale)+','+str(bounds)+','+str(dt[1])+'\n')
        
        elif (msgid == "00f5") :
            reqid = mval['body'][1]['reqid']
            reqseq = mval['body'][1]['reqseq']
            msgtot = mval['body'][1]['msgtot']
            msgnum = mval['body'][1]['msgnum']
            tcmId = mval['body'][1]['id']
            updated = mval['body'][1]['updated']
            label = mval['body'][1]['package']['label']
            tcId = mval['body'][1]['package']['tcids'][0]
            vclasses = mval['body'][1]['params']['vclasses']
            schedule = mval['body'][1]['params']['schedule']
            detail = mval['body'][1]['params']['detail']
            geometry = mval['body'][1]['geometry']

            newReqId = str(convID(reqid, 8)).replace(",", " ")
            newTcmId = str(convID(tcmId, 16)).replace(",", " ")
            newtcId = str(convID(tcId, 16)).replace(",", " ")

            fout.write(str(dt[0])+','+newReqId+','+str(reqseq)+','+str(msgtot)+','+str(msgnum)+','+newTcmId+','+str(updated)+','+str(label)+','+newtcId+','+str(vclasses)+','+str(schedule)+','+str(detail)+','+str(geometry)+','+str(dt[1])+'\n')
    
        else:
            sys.exit("Invalid message type\n")


if (msgid == "0014"): 
    print("")
    print("---------- Performance Metrics ----------")
    latency_avg = numpy.average(latency_array)
    print("Latency Average: " + str(latency_avg))
    latency_std = numpy.std(latency_array)
    print("Latency Standard Deviation (Jitter): " + str(latency_std))
