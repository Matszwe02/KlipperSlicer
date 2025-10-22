#!/bin/bash

set -e

SYSTEMDDIR="/etc/systemd/system"
MOONRAKER_ASVC=~/printer_data/moonraker.asvc

read -p "Select slicer:
  1: OrcaSlicer (matszwe02/orcaslicer-arm for arm64, lsiodev/orcaslicer for x86)
  2: I will set up slicer later
[1]: " SLICER_SELECTION
SLICER_SELECTION=${SLICER_SELECTION:-1}

read -p "Do you want to set up the web interface? [Y/n]: " WEB_INTERFACE_SETUP
WEB_INTERFACE_SETUP=${WEB_INTERFACE_SETUP:-y}


cd "$( dirname "${BASH_SOURCE[0]}")"

python3 -m venv .venv
.venv/bin/pip3 install -r requirements.txt

SRCDIR="$(pwd)"

SERVICE_FILE="${SYSTEMDDIR}/KlipperSlicer.service"

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

if [ "$SLICER_SELECTION" = "1" ]; then

    echo "Proceeding with OrcaSlicer installation..."
    
    if ! command -v docker &> /dev/null
    then
        echo "Installing docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh && sleep 10 && sh get-docker.sh
        sudo usermod -aG docker "$USER"
        rm get-docker.sh
        echo "Docker installed. You may have to reboot before running OrcaSlicer"
    fi
    docker compose down --remove-orphans
    if [ $(uname -m) = 'aarch64' ]; then
        docker compose -f compose.yml up -d
    elif [ $(uname -m) = 'x86_64' ]; then
        docker compose -f compose_x86.yml up -d
        echo "Change \"/opt/orca-slicer/bin/orca-slicer\" in config to \"orcaslicer\" as this image uses different executable "
    else
        echo "Unsupported architecture: $(uname -m)."
        exit 1
    fi

fi

if [[ "$WEB_INTERFACE_SETUP" =~ ^[Yy]$ ]]; then
    echo "Setting up web interface..."

    rm -rf ~/mainsail
    mkdir ~/mainsail
    cd ~/mainsail
    wget https://github.com/Matszwe02/mainsail/releases/download/v2.14.0/mainsail.zip || exit 1
    unzip mainsail.zip || exit 1

    if ! grep -q "slicer" /etc/nginx/conf.d/upstreams.conf;
    then
        echo "Configuring nginx upstreams..."
        cat << EOF | sudo tee -a /etc/nginx/conf.d/upstreams.conf
upstream slicer {
    ip_hash;
    server 127.0.0.1:3000;
}
EOF
    fi

    if ! grep -q "klipper-slicer" /etc/nginx/sites-available/mainsail;
    then
        echo "Configuring nginx sites-available..."
        sudo sed -i '$s/\}//' /etc/nginx/sites-available/mainsail
        cat << EOF | sudo tee -a /etc/nginx/sites-available/mainsail

    location /klipper-slicer/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
EOF
    fi
    echo "Restarting nginx..."
    sudo service nginx restart
fi
