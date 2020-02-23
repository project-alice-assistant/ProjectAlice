#!/usr/bin/env bash

sudo -u pi bash <<EOF
    /home/pi/hermesLedControl/venv/bin/pip3 uninstall -y gpiozero
    /home/pi/hermesLedControl/venv/bin/pip3 uninstall -y RPi.GPIO
    /home/pi/hermesLedControl/venv/bin/pip3 --no-cache-dir install respeaker
EOF
