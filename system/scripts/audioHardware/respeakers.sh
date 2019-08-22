#!/usr/bin/env bash

cd /home/pi

if [[ -d seeed-voicecard ]]; then
  rm -rf /home/pi/seeed-voicecard
fi

git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard
chmod +x ./install.sh
./install.sh
