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
    else:
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

    # Only consider buffers that start with PSID 0x0020.
    if line[:4] != PSID_PSM:
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
