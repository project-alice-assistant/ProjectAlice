#!/usr/bin/env bash

cd ~ || exit

if [[ -d "mimic" ]]; then
  rm -rf mimic
fi

git clone https://github.com/MycroftAI/mimic.git
cd mimic || exit
./dependencies.sh --prefix="/usr/local"
./autogen.sh
./configure --prefix="/usr/local"
make
/sbin/ldconfig
make check

sleep 1
