#!/bin/bash
set -euo pipefail
KEY="sma20_trail"
SERVICE_FILE="/etc/systemd/system/tradingai-sma20_trail-scanner.service"
echo "Installing SMA20 Trail trail scanner service..."
sudo cp "$DIR/ops/tradingai-sma20_trail-scanner.service" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable --now tradingai-sma20_trail-scanner
echo "Service installed and started."
