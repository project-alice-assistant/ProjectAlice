#!/usr/bin/env bash

cd ~ || exit

if [[ -d "seeed-voicecard" ]]; then
  rm -rf seeed-voicecard
fi

# git clone https://github.com/respeaker/seeed-voicecard.git
# use alt repo that works with latest kernel without downgrading
git clone https://github.com/HinTak/seeed-voicecard.git
cd seeed-voicecard || exit
git checkout v5.5
git pull
chmod +x ./install.sh
./install.sh --compat-kernel

sleep 1
