#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root (use sudo)" 1>&2
  exit 1
fi

sudo -u "$(logname)" bash <<EOF
  cp -r /home/"$(logname)"/ProjectAlice/venv /home/"$(logname)"/venv
  git -C /home/"$(logname)"/ProjectAlice clean -dfx
  git -C /home/"$(logname)"/ProjectAlice checkout master
  git -C /home/"$(logname)"/ProjectAlice pull
  mv /home/"$(logname)"/venv /home/"$(logname)"/ProjectAlice/venv

  cp -r /home/"$(logname)"/hermesLedControl/venv /home/"$(logname)"/venv
  git -C /home/"$(logname)"/hermesLedControl clean -dfx
  git -C /home/"$(logname)"/hermesLedControl checkout master
  git -C /home/"$(logname)"/hermesLedControl pull
  mv /home/"$(logname)"/venv /home/"$(logname)"/hermesLedControl/venv
EOF

apt-get clean
apt-get autoclean
apt-get autoremove -y

rm /boot/ProjectAliceSatellite.yaml
rm /boot/ProjectAliceSatellite.yaml.bak
cp /home/"$(logname)"/ProjectAlice/ProjectAliceSatellite.yaml /boot/ProjectAliceSatellite.yaml
rm /etc/wpa_supplicant/wpa_supplicant.conf
rm /etc/snips.toml
cp /home/"$(logname)"/ProjectAlice/system/snips/snips.toml /etc/snips.toml
rm /etc/systemd/system/hermesledcontrol.service
systemctl daemon-reload
systemctl enable ProjectAlice

sudo -u "$(logname)" bash <<EOF
  history -c
EOF
