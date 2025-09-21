#!/bin/bash

set -e

SYSTEMDDIR="/etc/systemd/system"
# FORCE_DEFAULTS="${FORCE_DEFAULTS:-n}"
MOONRAKER_ASVC=~/printer_data/moonraker.asvc

cd "$( dirname "${BASH_SOURCE[0]}")"

python3 -m venv .venv
.venv/bin/pip3 install -r requirements.txt

SRCDIR="$(pwd)"

SERVICE_FILE="${SYSTEMDDIR}/KlipperSlicer.service"
# [ -f $SERVICE_FILE ] && [ $FORCE_DEFAULTS = "n" ]

sudo /bin/sh -c "cat > ${SERVICE_FILE}" << EOF
#Systemd service file for KlipperSlicer
[Unit]
Description=Slicer integration with Klipper
After=network-online.target moonraker.service

[Install]
WantedBy=multi-user.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SRCDIR
ExecStart=$SRCDIR/.venv/bin/python3 main.py
Restart=always
RestartSec=10
EOF

sudo systemctl enable KlipperSlicer.service
sudo systemctl daemon-reload

if [ -f $MOONRAKER_ASVC ]; then
    echo "moonraker.asvc was found"
    if ! grep -q KlipperSlicer $MOONRAKER_ASVC; then
        echo "moonraker.asvc does not contain 'KlipperSlicer'! Adding it..."
        echo -e "\nKlipperSlicer" >> $MOONRAKER_ASVC
    fi
fi

sudo systemctl start KlipperSlicer
