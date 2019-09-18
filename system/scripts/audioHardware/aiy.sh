#!/usr/bin/env bash

cd ~

if [[ -d "aiyprojects-raspbian" ]]; then
    rm -rf aiyprojects-raspbian
fi

git clone https://github.com/google/aiyprojects-raspbian.git
cd aiyprojects-raspbian
git checkout voicekit
scripts/configure-driver.sh
scripts/install-alsa-config.sh