#!/bin/bash
set -euo pipefail
KEY="sma9_trail"
SERVICE_FILE="/etc/systemd/system/tradingai-sma9_trail-scanner.service"
echo "Installing SMA9 Trail trail scanner service..."
sudo cp "$DIR/ops/tradingai-sma9_trail-scanner.service" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable --now tradingai-sma9_trail-scanner
echo "Service installed and started."
