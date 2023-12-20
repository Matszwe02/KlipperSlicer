#!/bin/bash

SYSTEMDDIR="/etc/systemd/system"
FORCE_DEFAULTS="${FORCE_DEFAULTS:-n}"
MOONRAKER_ASVC=~/printer_data/moonraker.asvc

sudo apt-get update
sudo apt-get install  -y \
git \
build-essential \
autoconf \
cmake \
libglu1-mesa-dev \
libgtk-3-dev \
libdbus-1-dev \

# Deps:
#  libcairo2
#  libgtk2.0-0
#  libpangoxft-1.0-0
#  libpangocairo-1.0-0



pip install watchdog

mkdir slicer_data
mkdir slicer_data/gcodes
cp slicer/* slicer_data/slicer/


SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"
LAUNCH_CMD="python ${SRCDIR}/slicer.py"
if [ -z "$LOG_PATH" ]
then
    CMD="${LAUNCH_CMD}"
else
    CMD="${LAUNCH_CMD} -l ${LOG_PATH}"

fi
# Create systemd service file
SERVICE_FILE="${SYSTEMDDIR}/KlipperSlicer.service"
[ -f $SERVICE_FILE ] && [ $FORCE_DEFAULTS = "n" ]
# report_status "Installing system start script..."
sudo /bin/sh -c "cat > ${SERVICE_FILE}" << EOF
#Systemd service file for KlipperSlicer
[Unit]
Description=PrusaSlicer/SuperSlicer/Slic3r integration with Klipper
After=network-online.target moonraker.service

[Install]
WantedBy=multi-user.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SRCDIR
ExecStart=$CMD
Restart=always
RestartSec=10
EOF
# Use systemctl to enable the klipper systemd service script
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


