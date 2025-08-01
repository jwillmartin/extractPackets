## Overview
These scripts decode and optionally plot SAE J2735 messages. Not every field is decoded, but desired fields can easily be added in the [decoder.py](/src/decoder.py) script. 
The scripts are meant to decode only one message type at a time from one .pcap file. However, they may be edited to decode every message type within a file.
Plotting scripts exist in the [plot](/src/plot/) directory.

Feel free to make your own changes!

## Prerequisites:
* wireshark
* tshark
```
sudo add-apt-repository ppa:wireshark-dev/stable
sudo apt-get update
sudo apt-get -y install wireshark tshark
```
* pycrate
* numpy
* pandas
* folium
```
pip3 install pycrate numpy pandas folium
```

# Usage
1. Run the [extract](/src/extract/) script.
2. Run any of the [plot](/src/plot/) scripts.
