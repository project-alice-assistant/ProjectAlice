#!/usr/bin/env bash

cd ~

if [[ -d "seeed-voicecard" ]]; then
  rm -rf seeed-voicecard
fi

git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard
chmod +x ./install.sh
./install.sh

rm -rf seeed-voicecard

sleep 1
systemctl start seeed-voicecard
sleep 1
systemctl stop seeed-voicecard && systemctl disable seeed-voicecard