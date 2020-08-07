#!/usr/bin/env bash

cd ~ || exit

if [[ -d "seeed-voicecard" ]]; then
  rm -rf seeed-voicecard
fi

git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard || exit
chmod +x ./install.sh
./install.sh --compat-kernel

sleep 1

systemctl enable seeed-voicecard
