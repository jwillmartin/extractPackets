#!/bin/sh

set -e
sudo apt-get update 

# Dependencies
dependencies="python3 \
    python3-pip
    wireshark \
    tshark \
    git"

# Required python packages
python_packages="pycrate \
    numpy \
    pandas \
    folium"

# Install dependencies, packages
sudo add-apt-repository ppa:wireshark-dev/stable
sudo apt-get install -y $dependencies
pip3 install $python_packages

# Install j2735_202409 package
git clone https://github.com/jwillmartin/j2735_202409.git
cd j2735_202409
pip3 install dist/j2735_202409-0.1.0-py3-none-any.whl
cd ..
rm -rf j2735_202409
