#!/usr/bin/env bash

sudo -u "$(logname)" bash <<EOF
    /home/pi/HermesLedControl/venv/bin/pip3 uninstall -y gpiozero
    /home/pi/HermesLedControl/venv/bin/pip3 uninstall -y RPi.GPIO
EOF

apt-get install -y python-mraa
