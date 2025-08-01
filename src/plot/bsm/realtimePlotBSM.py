#!/usr/bin/python3
"""
Realtime BSM decoder + live map plot
------------------------------------
Listens for UDP-encapsulated J2735 hex frames, decodes BasicSafetyMessage
lat/long and streams those points onto a map window as they arrive.
"""

import J2735_201603_2023_06_22          as j2735
import socket, argparse, asyncio, json
from binascii import unhexlify
from collections import deque

# ---------- plotting setup --------------------------------------------------
import matplotlib.pyplot as plt
import numpy as np

try:
    import cartopy.crs as ccrs
    _USE_CARTOPY = True
except ModuleNotFoundError:
    _USE_CARTOPY = False
    print("Cartopy not found - falling back to simple scatter plot")

plt.ion()
if _USE_CARTOPY:
    _CRS = ccrs.PlateCarree()
    _fig = plt.figure(figsize=(7, 7))
    _ax  = _fig.add_subplot(1, 1, 1, projection=_CRS)
    _ax.coastlines()
    _scat = _ax.scatter([], [], 10, c="red", transform=_CRS)
else:
    _fig, _ax = plt.subplots(figsize=(7, 7))
    _ax.set_xlabel("Longitude"); _ax.set_ylabel("Latitude")
    _ax.grid(True)
    _scat = _ax.scatter([], [], 10, c="red")

_lats, _lons = deque(maxlen=50), deque(maxlen=50)   # keep last 50 points


def _update_plot(new_lat, new_lon):
    """Append new point, redraw scatter and auto-scale view."""
    _lats.append(new_lat)
    _lons.append(new_lon)

    xy = np.column_stack((_lons, _lats))
    _scat.set_offsets(xy)

    # Expand view a little around recent points
    pad = 0.002
    _ax.set_xlim(min(_lons) - pad, max(_lons) + pad)
    _ax.set_ylim(min(_lats) - pad, max(_lats) + pad)

    plt.pause(0.001)   # allow GUI to refresh

# ---------- original helpers (unchanged) ------------------------------------

def check_message(line: str) -> bool:
    temp_frame = line[6:]
    frame_size = 8 if len(temp_frame) > 510 else 6
    encoded_size = int(line[5:8], 16) * 2 if frame_size == 8 else int(line[4:6], 16) * 2
    new_frame = line[frame_size:]
    valid = encoded_size == len(new_frame)
    print("Valid message." if valid else "Not a valid message, continuing.")
    return valid


def convert_bytes(obj):
    if isinstance(obj, dict):
        return {k: convert_bytes(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_bytes(v) for v in obj]
    if isinstance(obj, bytes):
        return obj.hex()
    return obj


# ---------- modified parse - now extracts lat/long and calls _update_plot ----
_counter = 0
_MSG_IDS  = {"0014"}               # extend if you want more PSIDs


def parse(data: str, seq):
    global _counter
    for mid in _MSG_IDS:
        idx = data.find(mid)
        if idx == -1:
            continue

        frame = data[idx:].strip()
        if not check_message(frame):
            return

        try:
            seq.from_uper(unhexlify(frame))
        except Exception:
            return

        msg = convert_bytes(seq())
        core = msg["value"][1]["coreData"]
        raw_lat = core["lat"]
        raw_lon = core["long"]

        # Ignore "invalid" sentinel values 900000001 / 1800000001
        if abs(raw_lat) > 900000000 or abs(raw_lon) > 1800000000:
            return

        lat = raw_lat / 1e7
        lon = raw_lon / 1e7
        _update_plot(lat, lon)

        _counter += 1
        print(f"\nMessage {_counter}")
        print(json.dumps(msg, indent=2))


# ---------- async listener ---------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Decode J2735 messages from UDP and plot lat/long live")
    parser.add_argument("--ip",   type=str, default="127.0.0.1", help="Local IP to bind")
    parser.add_argument("--port", type=int, default=5398,        help="UDP port")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.ip, args.port))

    seq = j2735.DSRC.MessageFrame
    print("Listening - press Ctrl+C to exit")

    loop = asyncio.get_running_loop()
    while True:
        data, _ = await loop.run_in_executor(None, sock.recvfrom, 10000)
        parse(data.hex(), seq)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting …")
