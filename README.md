# Overview

These scripts decode and optionally plot SAE J2735 messages. Not every field is decoded, but desired fields can easily be added in the [decoder.py](/src/decoder.py) script. 
The scripts are meant to decode only one message type at a time from one .pcap file. However, they may be edited to decode every message type within a file.
Plotting scripts exist in the [plot](/src/plot/) directory.

Feel free to make your own changes!

## Prerequisites:

* wireshark
* tshark
* pycrate
* numpy
* pandas
* folium

Run the [install_dependencies.sh](/install/install_dependencies.sh) script to install all prerequisites.
```
cd install
./install_dependencies.sh
```

## Usage

1. Run the [extract](/src/extract/) script.
2. Run any of the [plot](/src/plot/) scripts.
