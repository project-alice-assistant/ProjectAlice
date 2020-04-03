#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root (use sudo)" 1>&2
  exit 1
fi

set -e

sed -i \
  -e "s/^#dtparam=audio=on/dtparam=audio=on/" \
  /boot/config.txt

grep -q "dtparam=audio=on" /boot/config.txt ||
  echo "dtparam=audio=on" >>/boot/config.txt
