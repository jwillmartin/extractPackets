#!/usr/bin/python3
from binascii import unhexlify
import J2735_201603_2023_06_22
import sys
import csv
import numpy
from datetime import datetime, timedelta, timezone


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
    columnHeaderString="packetTimestamp,intersectionID,moy,milliseconds,timestamp,unixTime,timeDiff\n"
    fout.write(columnHeaderString)

def writeMessageHeader(msgType):
    if (msgType == "BSM") :
        fout.write("packetTimestamp,bsmId,msgCnt,secMark,classification,keyType,role,timestamp,formattedTimestamp,timediff\n")
    elif (msgType=="MAP"):
        fout.write("packetTimestamp,intersectionID,latitude,longitude,laneWidth,signalGroupID\n")
    elif (msgType=="TIM"):
        fout.write("packetTimestamp,unixTimestamp,moy_timestamp_str,msgCnt,startTime,durationTime,timeDiff\n")
    elif (msgType=="PSM"):
        fout.write("packetTimestamp,msgCnt,secMark\n")
    elif (msgType=="SDSM"):
        fout.write("packetTimestamp,packet_datetime,sDSM_epoch,sDSM_datetime,msgCnt,sourceId,lat,long,heading, timeDiff\n")
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
        msg = J2735_201603_2023_06_22.DSRC.MessageFrame
        try:
            msg.from_uper(unhexlify(dt[1]))
        except:
            continue

        
        # SPAT
        if (msgid == "0013"):
            intersectionID = msg()['value'][1]['intersections'][0]['id']['id']
            moy = msg()['value'][1]['intersections'][0]['moy']
            millisec = msg()['value'][1]['intersections'][0]['timeStamp']

            # Packet year
            packet_datetime = datetime.fromtimestamp(float(dt[0]), tz=timezone.utc)
            year_from_packet = packet_datetime.year

            # Calculate the base datetime for the year
            baseDatetime = datetime(year_from_packet, 1, 1, tzinfo=timezone.utc)

            # Add the minutes and milliseconds to the base datetime
            timeStamp = baseDatetime + timedelta(minutes=moy, milliseconds=millisec)

            # Convert the timestamp to Unix time with fractional seconds
            unixTimestamp = timeStamp.timestamp()
            formattedTimestamp = f"{unixTimestamp:.5f}"

            # Calculate the time difference
            timeDiff = float(dt[0]) - unixTimestamp
            latency_array.append(timeDiff)

            spatString = str(dt[0]) + "," + str(intersectionID) + "," + str(moy) + "," + str(millisec) + "," + str(timeStamp) + "," + str(formattedTimestamp) + "," + str(timeDiff) + "\n"
            fout.write(spatString)

        # MAP
        elif (msgid == "0012"):
            intersectionID = msg()['value'][1]['intersections'][0]['id']['id']
            #if intersectionID == intersection:
            lat = msg()['value'][1]['intersections'][0]['refPoint']['lat']
            longstr = msg()['value'][1]['intersections'][0]['refPoint']['long']
            laneWidth = msg()['value'][1]['intersections'][0]['laneWidth']
            signalGroupID = msg()['value'][1]['intersections'][0]['laneSet'][0]['connectsTo'][0]['signalGroup']

            fout.write(str(dt[0])+','+str(intersectionID)+','+str(lat/10000000.0)+','+str(longstr/10000000.0)+','+str(laneWidth)+','+str(signalGroupID)+'\n')
        
        # BSM
        elif (msgid == "0014"):
            bsmId = msg()['value'][1]['coreData']['id'].hex()
            msgCnt = msg()['value'][1]['coreData']['msgCnt']
            secMark = msg()['value'][1]['coreData']['secMark']

            # Initialize optional fields to None in case not included
            classification = None
            keyType = None
            role = None

            # Safely check for partII
            partII_list = msg()['value'][1].get('partII')
            if partII_list and len(partII_list) > 0:
                partII_item = partII_list[0]
                partII_value = partII_item.get('partII-Value')
                if partII_value and len(partII_value) > 1 and isinstance(partII_value[1], dict):
                    extra_data = partII_value[1]
                    classification = extra_data.get('classification')
                    classDetails = extra_data.get('classDetails')
                    if classDetails:
                        keyType = classDetails.get('keyType')
                        role = classDetails.get('role')


            # Packet datetime
            packet_datetime = datetime.fromtimestamp(float(dt[0]), tz=timezone.utc)

            # Calculate the base datetime for the current minute
            baseMinute = datetime(packet_datetime.year, packet_datetime.month, packet_datetime.day, packet_datetime.hour, packet_datetime.minute, tzinfo=timezone.utc)

            # Add the secMark (milliseconds) to the base minute
            timeStamp = baseMinute + timedelta(milliseconds=secMark)

            # Convert to Unix time with fractional seconds
            unixTimestamp = timeStamp.timestamp()
            formattedTimestamp = f"{unixTimestamp:.5f}"

            # Calculate the time difference
            timeDiff = float(dt[0]) - unixTimestamp
            latency_array.append(timeDiff)

            bsmString = (f"{dt[0]},{bsmId},{msgCnt},{secMark},{classification},{keyType},{role},{timeStamp},{formattedTimestamp},{timeDiff}\n")
            fout.write(bsmString)

        # TIM
        elif (msgid == "001f"):
            msgCnt = msg()['value'][1]['msgCnt']
            startTime = msg()['value'][1]['dataFrames'][0]['startTime']
            durationTime = msg()['value'][1]['dataFrames'][0]['duratonTime']
            unixTimestamp = msg()['value'][1]['dataFrames'][0]['regions'][0]['name']

            packet_datetime = datetime.fromtimestamp(float(dt[0]), tz=timezone.utc)
            current_year = datetime.now(timezone.utc).year
            start_dt = datetime(current_year, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=startTime)
            moy_timestamp_str = start_dt.isoformat()

            # Calculate the time difference
            timeDiff = float(dt[0]) - float(unixTimestamp)
            latency_array.append(timeDiff)

            timString = (f"{dt[0]},{unixTimestamp},{moy_timestamp_str},{msgCnt},{startTime},{durationTime},{timeDiff}\n")
            fout.write(timString)

        # PSM
        elif (msgid =="0020"):
            msgCnt = msg()['value'][1]['msgCnt']
            secMark = msg()['value'][1]['secMark']

            # Packet datetime
            packet_datetime = datetime.fromtimestamp(float(dt[0]), tz=timezone.utc)

            # Calculate the base datetime for the current minute
            baseMinute = datetime(packet_datetime.year, packet_datetime.month, packet_datetime.day, packet_datetime.hour, packet_datetime.minute, tzinfo=timezone.utc)

            # Add the secMark (milliseconds) to the base minute
            timeStamp = baseMinute + timedelta(milliseconds=secMark)

            # Convert to Unix time with fractional seconds
            unixTimestamp = timeStamp.timestamp()
            formattedTimestamp = f"{unixTimestamp:.5f}"

            # Calculate the time difference
            timeDiff = float(dt[0]) - unixTimestamp
            latency_array.append(timeDiff)

            psmString = (f"{dt[0]},{msgCnt},{secMark},{timeStamp},{formattedTimestamp},{timeDiff}\n")
            fout.write(psmString)


        # SDSM
        elif (msgid == "0029"):
            msgCnt = msg()['value'][1]['msgCnt']
            sourceID = msg()['value'][1]['sourceID'].hex()
            refLat = msg()['value'][1]['refPos']['lat']/10000000.0
            refLong = msg()['value'][1]['refPos']['long']/10000000.0
            heading = msg()['value'][1]['objects'][0]['detObjCommon']['heading']
            year = msg()['value'][1]['sDSMTimeStamp']['year']
            month = msg()['value'][1]['sDSMTimeStamp']['month']
            day = msg()['value'][1]['sDSMTimeStamp']['day']
            hour = msg()['value'][1]['sDSMTimeStamp']['hour']
            min = msg()['value'][1]['sDSMTimeStamp']['minute']
            sec = msg()['value'][1]['sDSMTimeStamp']['second']

            # Convert milliseconds to float seconds
            fltSec = sec/1000.0
            
            # Create the datetime up to the minute, then add fractional seconds
            sDSM_datetime = (datetime(year, month, day, hour, min, 0, tzinfo=timezone.utc) 
                     + timedelta(seconds=fltSec))

            # Convert datetime to an epoch timestamp
            sDSM_epoch = sDSM_datetime.timestamp()
            packet_datetime = datetime.fromtimestamp(float(dt[0]), tz=timezone.utc)

            # Calculate the time difference
            timeDiff = float(dt[0]) - sDSM_epoch
            latency_array.append(timeDiff)

            fout.write(f"{dt[0]},{packet_datetime.isoformat()},{sDSM_epoch},{sDSM_datetime.isoformat()},{msgCnt},{sourceID},{refLat},{refLong},{heading},{timeDiff}\n")


        # Test Messages
        elif (msgid == "00f0") :
            hostStaticId = msg()['value'][1]['header']['hostStaticId']
            hostBSMId = msg()['value'][1]['header']['hostBSMId']
            planId = msg()['value'][1]['header']['planId']
            strategy = msg()['value'][1]['body']['strategy']
            planType = msg()['value'][1]['body']['planType']
            urgency = msg()['value'][1]['body']['urgency']
            strategyParams = msg()['value'][1]['body']['strategyParams']
            trajectoryStart = msg()['value'][1]['body']['trajectoryStart']
            trajectory = msg()['value'][1]['body']['trajectory']
            expiration = msg()['value'][1]['body']['expiration']

            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(strategy)+','+str(planType)+','+str(urgency)+''+str(strategyParams)+''+str(trajectoryStart)+''+str(trajectory)+''+str(expiration)+''+'\n')

        elif (msgid == "00f1") :
            hostStaticId = msg()['value'][1]['header']['hostStaticId']
            hostBSMId = msg()['value'][1]['header']['hostBSMId']
            planId = msg()['value'][1]['header']['planId']
            urgency = msg()['value'][1]['body']['urgency']
            isAccepted = msg()['value'][1]['body']['isAccepted']

            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(urgency)+','+str(isAccepted)+'\n')

        elif (msgid == "00f2") :
            hostStaticId = msg()['value'][1]['header']['hostStaticId']
            hostBSMId = msg()['value'][1]['header']['hostBSMId']
            planId = msg()['value'][1]['header']['planId']
            location = msg()['value'][1]['body']['location']
            trajectory = msg()['value'][1]['body']['trajectory']

            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(location)+','+str(trajectory)+'\n')

        elif (msgid == "00f3") :
            hostStaticId = msg()['value'][1]['header']['hostStaticId']
            hostBSMId = msg()['value'][1]['header']['hostBSMId']
            planId = msg()['value'][1]['header']['planId']
            strategy = msg()['value'][1]['body']['strategy']
            operationParams = msg()['value'][1]['body']['operationParams']
            
            fout.write(str(dt[0])+','+str(hostStaticId)+','+str(hostBSMId)+','+str(planId)+','+str(strategy)+','+str(operationParams)+'\n')

        elif (msgid == "00f4") :
            reqid = msg()['value'][1]['body'][1]['reqid']
            reqseq = msg()['value'][1]['body'][1]['reqseq']
            scale = msg()['value'][1]['body'][1]['scale']
            bounds = msg()['value'][1]['body'][1]['bounds']

            newReqId = str(convID(reqid, 8)).replace(",", " ")

            fout.write(str(dt[0])+','+newReqId+','+str(reqseq)+','+str(scale)+','+str(bounds)+','+str(dt[1])+'\n')
        
        elif (msgid == "00f5") :
            reqid = msg()['value'][1]['body'][1]['reqid']
            reqseq = msg()['value'][1]['body'][1]['reqseq']
            msgtot = msg()['value'][1]['body'][1]['msgtot']
            msgnum = msg()['value'][1]['body'][1]['msgnum']
            tcmId = msg()['value'][1]['body'][1]['id']
            updated = msg()['value'][1]['body'][1]['updated']
            label = msg()['value'][1]['body'][1]['package']['label']
            tcId = msg()['value'][1]['body'][1]['package']['tcids'][0]
            vclasses = msg()['value'][1]['body'][1]['params']['vclasses']
            schedule = msg()['value'][1]['body'][1]['params']['schedule']
            detail = msg()['value'][1]['body'][1]['params']['detail']
            geometry = msg()['value'][1]['body'][1]['geometry']

            newReqId = str(convID(reqid, 8)).replace(",", " ")
            newTcmId = str(convID(tcmId, 16)).replace(",", " ")
            newtcId = str(convID(tcId, 16)).replace(",", " ")

            fout.write(str(dt[0])+','+newReqId+','+str(reqseq)+','+str(msgtot)+','+str(msgnum)+','+newTcmId+','+str(updated)+','+str(label)+','+newtcId+','+str(vclasses)+','+str(schedule)+','+str(detail)+','+str(geometry)+','+str(dt[1])+'\n')
    
        else:
            sys.exit("Invalid message type\n")


if (msgid == "0014" or msgid == "0013" or msgid == "001f" or msgid == "0020" or msgid == "0029"): 
    print("\n---------- Performance Metrics ----------")
    latency_avg = numpy.average(latency_array)
    print("Latency Average: " + str(latency_avg))
    latency_std = numpy.std(latency_array)
    print("Latency Standard Deviation (Jitter): " + str(latency_std))
