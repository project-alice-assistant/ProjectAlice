#!/usr/bin/env bash

sudo -u pi bash <<EOF
    /home/pi/snipsLedControl/venv/bin/pip3 uninstall -y gpiozero
    /home/pi/snipsLedControl/venv/bin/pip3 uninstall -y RPi.GPIO
    /home/pi/snipsLedControl/venv/bin/pip3 --no-cache-dir install respeaker
EOF
