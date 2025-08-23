#!/usr/bin/env python3
import sys
import parser_helper
from csv import reader, writer

IN_FILE = sys.argv[1]
FILE_NAME = IN_FILE.split(".")[0]
MESSAGE_ID = sys.argv[2]

def main():
    with open(FILE_NAME + '.csv') as read_obj, open(FILE_NAME + '_payload.csv', 'w', newline='') as write_obj:
        csv_reader = reader(read_obj)
        csv_writer = writer(write_obj)

        for row in csv_reader:
            payload_src = row[1]

            try:
                wsm = parser_helper.getWSM(payload_src)
                csv_writer.writerow([row[0], wsm])
            except Exception:
                # Search entire payload for message id
                unsecuredData = parser_helper.parseWSM(payload_src, MESSAGE_ID)
                if unsecuredData:
                    csv_writer.writerow([row[0], unsecuredData])

        # Done processing files
        read_obj.close()
        write_obj.close()

if __name__=="__main__":
    main()
