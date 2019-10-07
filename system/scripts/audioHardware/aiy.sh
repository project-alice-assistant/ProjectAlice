#!/usr/bin/env bash

# Code from google:
# https://github.com/google/aiyprojects-raspbian/blob/voicekit/scripts/install-alsa-config.sh
# https://github.com/google/aiyprojects-raspbian/blob/voicekit/scripts/configure-driver.sh

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 1>&2
   exit 1
fi

set -e

sed -i \
  -e "s/^dtparam=audio=on/#\0/" \
  -e "s/^#\(dtparam=i2s=on\)/\1/" \
  /boot/config.txt
grep -q "dtoverlay=i2s-mmap" /boot/config.txt || \
  echo "dtoverlay=i2s-mmap" >> /boot/config.txt
grep -q "dtoverlay=googlevoicehat-soundcard" /boot/config.txt || \
  echo "dtoverlay=googlevoicehat-soundcard" >> /boot/config.txt
grep -q "dtparam=i2s=on" /boot/config.txt || \
  echo "dtparam=i2s=on" >> /boot/config.txt

set -o errexit

cd "$(dirname "${BASH_SOURCE[0]}")/.."

asoundrc=/home/pi/.asoundrc
global_asoundrc=/etc/asound.conf

for rcfile in "$asoundrc" "$global_asoundrc"; do
  if [[ -f "$rcfile" ]] ; then
    echo "Renaming $rcfile to $rcfile.bak..."
    sudo mv "$rcfile" "$rcfile.bak"
  fi
done

sudo cp /home/pi/ProjectAlice/system/asounds/aiy.conf "$global_asoundrc"
echo "Installed voiceHAT ALSA config at $global_asoundrc"
