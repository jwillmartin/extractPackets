import Ieee1609Dot2
import Ieee1609Dot3Wsm
import J2735_202409
import os
from binascii import unhexlify
from contextlib import redirect_stderr, redirect_stdout

def getWSM(data: str):
    """Extract WSM unsecuredData from WSMP

    Parameters:
        data (str): The WSMP data to extract from.

    Returns:
        str: The extracted WSM unsecuredData. May return None if extraction fails (malformed packet).
    """
    wsm = None
    unsecuredData = None

    # Get WSMP info
    b = unhexlify(data.strip("\\n"))
    dot3 = Ieee1609Dot3Wsm.Ieee1609Dot3Wsm.ShortMsgNpdu
    dot3.from_uper(b)

    # Extract WSM (ShortMsgData) from WSMP
    try:
        wsm = dot3()['body'].hex()
    except Exception:
        return unsecuredData

    # Get WSM (Ieee1609Dot2Data) info
    dot2 = Ieee1609Dot2.Ieee1609Dot2.Ieee1609Dot2Data
    # Pycrate decoders print to stderr on CHOICE extension tag issues; silence here
    with open(os.devnull, 'w') as devnull, redirect_stderr(devnull), redirect_stdout(devnull):
        dot2.from_oer(unhexlify(wsm))

    # Extract unsecuredData from WSM
    try:
        unsecuredData = dot2()['content'][1].hex() # if wsm unsigned
    except Exception:
        unsecuredData = dot2()['content'][1]['tbsData']['payload']['data']['content'][1].hex() # if wsm signed

    return unsecuredData

def parseWSM(payload_src: str, msg_id: str):
    """Manually parse for the WSM unsecuredData.

    Parameters:
        data (str): The data to parse.

    Returns:
        str: The parsed WSM unsecured data. May return None if no payload is found.
    """
    # Initialize message frame
    MessageFrame = J2735_202409.MessageFrame.MessageFrame
    for search_start in range(len(payload_src)):
        idx = payload_src.find(msg_id, search_start)

        # Stop searching this row if DSRCmsgID not found or not enough data remaining
        if idx == -1 or idx > len(payload_src) - 16:
            break

        # Create payload buffer and strip newline in case ascii
        buf = payload_src[idx:].strip('\\n')

        # Validate frame size and skip known false-positive BSM PSID pattern
        if not isValidMsgSize(buf):
            # Advance past this occurrence and keep searching
            search_start = idx + 3
            continue
        if msg_id == "0020" and isBSMPSID(buf):
            # Advance past this occurrence and keep searching
            search_start = idx + 3
            continue

        # Final check to ensure message is valid
        try:
            # Silence on failure
            with open(os.devnull, 'w') as devnull, redirect_stderr(devnull), redirect_stdout(devnull):
                MessageFrame.from_uper(unhexlify(buf))
        except Exception:
            # Advance past this occurrence and keep searching quietly
            search_start = idx + 3
            continue
        return buf
    return None

def isValidMsgSize(line):
    """Checks actual message size against size specified in MessageFrame.
    Args:
        line (str): Full message under test.
    Returns:
        bool: Validity of message size.
    """
    tempFrame = line[6:]
    if (len(tempFrame) > 510):
        frameSize = 8
        encodedSize = int(line[5:8], 16) * 2
    else:
        frameSize = 6
        encodedSize = int(line[4:6], 16) * 2

    newFrame = line[frameSize:]
    if (encodedSize == len(newFrame)):
        return True
    elif (encodedSize < len(newFrame) - 150):
        # If the message is larger than expected, it may contain a certificate or digest hash
        if isSigned(newFrame):
            return True
    return False

def isSigned(frame):
    """Checks if the message is signed by looking for a certificate or digest hash.
    Returns:
        bool: Validity of signed message.
    """
    # Find all possible cert or digest hashes, by length
    length = len(frame)
    possibleCert = frame[frame.find("00030180"):]
    possibleDigest = frame[length-(76*2)+2:]

    # Extract all verified cert or digest hashes
    if (possibleCert[0:8] == "00030180"):
        fullCert = possibleCert[8:24]
        if fullCert:
            return True

    if ((possibleDigest[0:2] == possibleDigest[18:20]) and possibleDigest[18:20] == "80"):
        hashId = possibleDigest[2:18]
        if hashId:
            return True
    return False

def isBSMPSID(line):
    """Detect a known false-positive where PSID 0x0020 (PSM) is followed by the
    Element ID 0x0380 and DSRCmsgID 0x0014 (BSM), i.e., the pattern:
      0020 ... 0380 ... 0014

    We only flag this when the buffer starts with PSID 0x0020 and both 0x0380 and
    0x0014 appear within a small window (<= 5 bytes each) in the expected order.

    Args:
        line (str): Full hex-encoded message starting at a PSID.
    Returns:
        bool: True if the false-positive BSM pattern under PSID 0x0020 is detected.
    """
    # Constants (hex strings); offsets are expressed in bytes and then converted to hex chars.
    PSID_PSM = '0020'
    ELEMENT_ID = '0380'
    BSM_ID = '0014'
    MAX_BYTES_AFTER_PSID = 5   # 5 bytes = 10 hex chars
    MAX_BYTES_AFTER_ELEM = 5   # 5 bytes = 10 hex chars

    if not line or len(line) < 4:
        return False

    # Compute search bounds without creating substrings.
    psid_end = len(PSID_PSM)  # index right after PSID
    elem_search_end = psid_end + (MAX_BYTES_AFTER_PSID * 2) + len(ELEMENT_ID)
    elem_idx = line.find(ELEMENT_ID, psid_end, elem_search_end)
    if elem_idx == -1:
        return False

    start_after_elem = elem_idx + len(ELEMENT_ID)
    bsm_search_end = start_after_elem + (MAX_BYTES_AFTER_ELEM * 2) + len(BSM_ID)
    bsm_idx = line.find(BSM_ID, start_after_elem, bsm_search_end)
    if bsm_idx == -1:
        return False

    return True
