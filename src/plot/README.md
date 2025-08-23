# Overview
The plotting scripts in this directory serve to plot data extracted using the [extract.sh](/src/extract.sh) script.
Coordinates are plotted to an OpenStreetMap.

If multiple logs exist, containing messages from the same region, you can optionally run the [mergeCSV.py](mergeCSV.py) script. 
This script will merge all selected CSV files of the same type. For example, all decoded BSMs from logs spanning multiple test runs would be merged and organized by timestamp into a single CSV. This can then be plotted to have one combined map of all BSMs. 
