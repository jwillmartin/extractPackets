#!/usr/bin/env python3
import sys
from csv import reader, writer

inFile = sys.argv[1]
payloadType=sys.argv[3]
print("Payload Type: " + payloadType)
fileName = inFile.split(".")

with open(fileName[0]+'.csv') as read_obj, \
open(fileName[0]+'_payload.csv', 'w', newline='') as write_obj:
    csv_reader = reader(read_obj)
    csv_writer = writer(write_obj)

    substr = {
        'map': '0012',
        'spat':'0013',
        'bsm': '0014',
        'tim': '001f',
        'psm': '0020',
        'sdsm': '0029',
        'req': '00f0',
        'res': '00f1',
        'mop': '00f2',
        'mom': '00f3',
        'tcr': '00f4',
        'tcm': '00f5'
    }

    for row in csv_reader:
        index = {}
        smallerIndex = 10000
        
        #remove newlines for ascii
        if( payloadType == "ascii" ):
            row[1] = row[1].replace("\\n","")
        
        for k in substr:
            if substr[k] in row[1]:
                index[k] = row[1].find(substr[k])
                if index[k] < smallerIndex:
                    smallerIndex = index[k]
                    msg = row[1][smallerIndex:]
                    csv_writer.writerow([row[0],msg])
