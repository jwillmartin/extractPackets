#!/usr/bin/env python
from binascii import unhexlify
import J2735_202409
import sys
import csv
import numpy
import datetime

def get_unix(packet_unix_ts: float, moy: int, ms_of_minute: int) -> float:
    """Construct payload unix timestamp (UTC seconds) using minute-of-year and millisecond-of-minute.

    Assumes the 'current year' is the year of the packet capture timestamp.
    Handles leap seconds by allowing ms_of_minute in [0..60999].
    """
    # Determine the year from the packet's capture time (UTC)
    dt = datetime.datetime.fromtimestamp(packet_unix_ts, tz=datetime.timezone.utc)
    year_start = datetime.datetime(dt.year, 1, 1, tzinfo=datetime.timezone.utc)
    base = year_start.timestamp()
    # Convert minute-of-year to seconds and add millisecond-of-minute
    return base + (int(moy) * 60.0) + (int(ms_of_minute) / 1000.0)

def compute_message_rate(timestamps, expected_rate_hz: float = 10.0):
    """Compute basic message interval statistics and rate in Hz.

    Args:
        timestamps: iterable of unix timestamps (float seconds), unsorted ok.
        expected_rate_hz: expected nominal message rate for loss estimation.

    Returns:
        dict with keys: count, avg_ms, std_ms, min_ms, max_ms, rate_hz,
        expected_count, loss_pct.
        Empty dict if fewer than 2 usable intervals.
    """
    try:
        ts = sorted(float(t) for t in timestamps if t is not None)
    except Exception:
        return {}
    if len(ts) < 2:
        return {}
    deltas = [b - a for a, b in zip(ts, ts[1:]) if (b - a) > 0]
    if not deltas:
        return {}
    deltas_ms = [d * 1000.0 for d in deltas]
    avg_ms = float(numpy.average(deltas_ms))
    std_ms = float(numpy.std(deltas_ms))
    min_ms = float(min(deltas_ms))
    max_ms = float(max(deltas_ms))
    rate_hz = 1000.0 / avg_ms if avg_ms > 0 else 0.0
    # Estimate packet loss vs expected rate
    elapsed = ts[-1] - ts[0]
    expected_count = int(round(elapsed * expected_rate_hz)) + 1 if elapsed > 0 and expected_rate_hz > 0 else len(ts)
    expected_count = max(expected_count, len(ts))  # never report fewer expected than observed
    missing = max(0, expected_count - len(ts))
    loss_pct = (missing / expected_count) * 100.0 if expected_count > 0 else 0.0
    return {
        'count': len(ts),
        'avg_ms': avg_ms,
        'std_ms': std_ms,
        'min_ms': min_ms,
        'max_ms': max_ms,
        'rate_hz': rate_hz,
        'expected_count': expected_count,
        'loss_pct': loss_pct,
    }

def compute_latency_stats(latencies_ms):
    """Compute latency stats from a list of millisecond values."""
    try:
        vals = [float(x) for x in latencies_ms if x is not None]
    except Exception:
        return {}
    if not vals:
        return {}
    return {
        'avg_ms': float(numpy.average(vals)),
        'std_ms': float(numpy.std(vals)),
        'min_ms': float(min(vals)),
        'max_ms': float(max(vals)),
        'count': len(vals),
    }

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
    columnHeaderString="packetTimestamp,moy,dsecond,time_delta_ms,intersectionID\n"
    # columnHeaderString = columnHeaderString + ",phase" + ",state" + ",countdown\n"
    fout.write(columnHeaderString)

def writeMessageHeader(msgType):
    if (msgType == "BSM") :
        fout.write("packetTimestamp,bsm_id,secMark,latency,latitude,longitude,speed(m/s),heading,elevation(m),accel_long(m/s^2)\n")
    elif (msgType=="MAP"):
        fout.write("packetTimestamp,intersectionID,latitude,longitude,payload\n")
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
latency_samples = []  # (packet_ts, latency_ms) for per-second aggregation
prevSpatTimestamp = 0
spat_timestamps = []  # collect timestamps (prefer payload time; fallback to packet time)
spat_latencies_ms = []  # collect per-message latency based on time_delta_ms
spat_latency_samples = []  # (packet_ts, latency_ms) for per-second aggregation
seen_payloads = set()  # track unique payload hex strings
duplicate_payloads = []  # list of (packetTimestamp, payloadHex)
payload_counts = {}  # payloadHex -> count
duplicates_unique = set()  # set of payloadHex that appeared 2+ times


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

        # Duplicate detection (by exact payload hex string)
        try:
            payload_hex = dt[1]
            # maintain occurrence count
            cnt = payload_counts.get(payload_hex, 0) + 1
            payload_counts[payload_hex] = cnt
            if cnt == 1:
                seen_payloads.add(payload_hex)
            else:
                duplicate_payloads.append((dt[0], payload_hex))
                if cnt == 2:
                    # mark as uniquely duplicated when first duplicate observed
                    duplicates_unique.add(payload_hex)
        except Exception:
            pass
        
        # SPAT
        if (msgid == "0013"):
            moy = mval['timeStamp']
            intersectionID = mval['intersections'][0]['id']['id']
            # intersectionPhaseArray = mval['intersections'][0]['states']
            dsecond = mval['intersections'][0]['timeStamp']

            # # used later when exact number or phases is known
            # numPhases = 2 # use number of desired phases
            # spatPhaseArray = [None] * numPhases

            # Compute packet->payload time delta (ms). If unavailable, leave blank.
            time_delta_ms = ''
            payload_unix = None
            try:
                # Some encoders may use 'unavailable'; skip in that case
                if moy is not None and dsecond is not None:
                    # J2735 MinuteOfTheYear often uses 0..527040 with 65535 as unavailable.
                    if int(moy) != 65535:
                        unix = float(dt[0])
                        payload_unix = get_unix(unix, int(moy), int(dsecond))
                        time_delta_ms = int(round((unix - payload_unix) * 1000.0))
            except Exception:
                # Keep blank if anything goes wrong
                time_delta_ms = ''
                payload_unix = None

            # for phase in range(len(intersectionPhaseArray)):
            #     currentPhase = mval['intersections'][0]['states'][phase].get('signalGroup')
            #     currentState = str(mval['intersections'][0]['states'][phase]['state-time-speed'][0]['eventState'])
            #     minEndTime = mval['intersections'][0]['states'][phase]['state-time-speed'][0]['timing']['minEndTime']
            #     maxEndTime = mval['intersections'][0]['states'][phase]['state-time-speed'][0]['timing']['maxEndTime']
            #     if (minEndTime == 36001):
            #         timeEndSec = maxEndTime/6
            #     else:
            #         timeEndSec = minEndTime/6

            spatString = str(dt[0] + "," + str(moy) + "," + str(dsecond) + "," + str(time_delta_ms) + "," + str(intersectionID) + "\n") # + "," + str(currentPhase) + "," + str(currentState) + "," + str(timeEndSec) + "\n")
            fout.write(spatString)
            # Track timestamp for message interval stats
            try:
                spat_timestamps.append(float(payload_unix) if payload_unix is not None else float(dt[0]))
            except Exception:
                # If both fail, skip adding
                pass
            # Track latency based on computed delta
            try:
                if time_delta_ms != '':
                    spat_latencies_ms.append(float(time_delta_ms))
                    # use packet capture timestamp for per-second grouping
                    spat_latency_samples.append((float(dt[0]), float(time_delta_ms)))
            except Exception:
                pass

        # MAP
        elif (msgid == "0012"):
            intersectionID = mval['intersections'][0]['id']['id']
            lat = mval['intersections'][0]['refPoint']['lat']
            long = mval['intersections'][0]['refPoint']['long']

            fout.write(str(dt[0])+','+str(intersectionID)+','+str(lat/10000000.0)+','+str(long/10000000.0)+','+str(dt[1])+'\n')

        # BSM
        elif (msgid == "0014"):
            bsmId = mval['coreData']['id'].hex()
            lat = mval['coreData']['lat']
            long = mval['coreData']['long']
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
            try:
                latency_samples.append((float(dt[0]), float(latency)))
            except Exception:
                pass
            
            fout.write(str(dt[0])+','+str(bsmId)+','+str(secMark)+','+str(latency)+','+str(lat/10000000.0)+','+str(long/10000000.0)+','+str(speed_converted)+','+str(heading)+','+str(accel_long_converted)+','+ str(elevation)+'\n')

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

# BSM Performance Metrics
if (msgid == "0014"): 
    print("")
    print("---------- Performance Metrics ----------")
    # Per-second aggregation (expect ~10 payloads per second)
    if latency_array:
        latency_avg = numpy.average(latency_array)
        latency_std = numpy.std(latency_array)
        print("Latency Average: " + str(latency_avg))
        print("Latency Standard Deviation (Jitter): " + str(latency_std))
    else:
        print("No latency samples available.")

# SPAT message interval rate summary
if (msgid == "0013"):
    stats = compute_message_rate(spat_timestamps, expected_rate_hz=10.0)
    if stats:
        print("")
        print("---------- SPAT Message Interval ----------")
        print(f"Count: {stats['count']}")
        print(f"Avg interval: {stats['avg_ms']:.1f} ms")
        print(f"Std dev: {stats['std_ms']:.1f} ms")
        print(f"Min/Max: {stats['min_ms']:.1f}/{stats['max_ms']:.1f} ms")
        print(f"Estimated rate: {stats['rate_hz']:.3f} Hz (expected 10.000 Hz)")
        print(f"Packet loss: {stats['loss_pct']:.2f}%")
        # Latency stats derived from time_delta_ms
        lat_stats = compute_latency_stats(spat_latencies_ms)
        if lat_stats:
            print("")
            print("---------- SPAT Latency (packet - payload) ----------")
            print(f"Samples: {lat_stats['count']}")
            print(f"Latency avg: {lat_stats['avg_ms']:.1f} ms")
            print(f"Latency std dev: {lat_stats['std_ms']:.1f} ms")
            print(f"Latency min/max: {lat_stats['min_ms']:.1f}/{lat_stats['max_ms']:.1f} ms")
    else:
        print("")
        print("---------- SPAT Message Interval ----------")
        print("Insufficient data to compute interval rate.")

# Write duplicate payloads log (if any)
if duplicate_payloads:
    try:
        out_name = sys.argv[2]
        base_name = out_name[:-4] if out_name.endswith('.csv') else out_name
        # Also write a summary by payload hex for those with count >= 2
        dup_log = f"{base_name}_duplicates_summary.csv"
        unique_dupe_count = len(duplicates_unique) if duplicates_unique else len([k for k, v in payload_counts.items() if v > 1])
        with open(dup_log, 'w') as sf:
            sf.write("payloadHex,count\n")
            for phex, cnt in payload_counts.items():
                if cnt > 1:
                    sf.write(f"{phex},{cnt}\n")

        print(f"Duplicate payloads logged to {dup_log} ({len(duplicate_payloads)} duplicates, {unique_dupe_count} unique payloads duplicated);")
    except Exception as e:
        print(f"Failed to write duplicate payload log: {e}")
