#!/usr/bin/env bash

sudo -u pi bash <<EOF
    /home/pi/snipsLedControl/venv/bin/pip3 uninstall -y gpiozero
    /home/pi/snipsLedControl/venv/bin/pip3 uninstall -y RPi.GPIO
EOF

apt-get install -y python-mraa
