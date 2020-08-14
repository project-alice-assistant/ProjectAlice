#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root (use sudo)" 1>&2
  exit 1
fi

sudo -u "$(logname)" bash <<EOF
  git -C /home/"$(logname)"/ProjectAlice clean -dfx
  git -C /home/"$(logname)"/ProjectAlice checkout master
  git -C /home/"$(logname)"/ProjectAlice pull
EOF

apt-get update
apt-get dist-upgrade
apt-get clean
apt-get autoclean
apt-get autoremove -y

rm /boot/ProjectAlice.yaml
rm /boot/ProjectAlice.yaml.bak
cp /home/"$(logname)"/ProjectAlice/ProjectAlice.yaml /boot/ProjectAlice.yaml
rm /etc/wpa_supplicant/wpa_supplicant.conf
rm /etc/snips.toml
systemctl daemon-reload
systemctl enable ProjectAlice

apt-get install -y python3-pip
pip3 install PyYAML==5.3.1
pip3 install requests==2.21.0
pip3 install psutil==5.7.2
pip3 install toml==0.10.1

sudo -u "$(logname)" bash <<EOF
  history -c
EOF
