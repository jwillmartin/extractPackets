#!/usr/bin/env python3
import sys
import J2735_202409
import parser_helper
from binascii import unhexlify
from csv import reader, writer

if (len(sys.argv) < 2):
    raise ValueError("Incomplete Arguments")

# Declare Constants
IN_FILE = sys.argv[1]
FILE_NAME = IN_FILE.split(".")[0]
MESSAGE_ID = sys.argv[2]

def main():
    # Initialize message frame
    MessageFrame = J2735_202409.MessageFrame.MessageFrame

    with open(FILE_NAME + '.csv') as read_obj, open(FILE_NAME + '_payload.csv', 'w', newline='') as write_obj:
        csv_reader = reader(read_obj)
        csv_writer = writer(write_obj)

        for row in csv_reader:
            # Find payload start index
            payload_src = row[1]
            search_start = 0

            # Keep searching for MESSAGE_ID within payload_src until a valid
            # message is decoded or we run out of occurrences.
            while True:
                idx = payload_src.find(MESSAGE_ID, search_start)

                # Stop searching this row if DSRCmsgID not found or not enough data remaining
                if idx == -1 or idx > len(payload_src) - 6:
                    break

                # Create payload buffer and strip newline in case ascii
                buf = payload_src[idx:].strip('\\n')

                # Validate frame size and skip known false-positive BSM PSID pattern
                if not parser_helper.isValidMsgSize(buf):
                    # Advance past this occurrence and keep searching
                    search_start = idx + 4
                    continue
                if parser_helper.isBSMPSID(buf):
                    # Advance past this occurrence and keep searching
                    search_start = idx + 4
                    continue

                # Final check to ensure message is valid
                try:
                    MessageFrame.from_uper(unhexlify(buf))
                except Exception:
                    print("Failed to decode message: ", buf)
                    # Advance past this occurrence and keep searching
                    search_start = idx + 4
                    continue

                # If we reach here, we've found a valid message; write it and move to next row
                csv_writer.writerow([row[0], buf])
                break

if __name__=="__main__":
    main()
