#!/bin/bash
set -euo pipefail
KEY="sma3_high_trail"
SERVICE_FILE="/etc/systemd/system/tradingai-sma3_high_trail-scanner.service"
echo "Installing SMA3 HIGH Trail trail scanner service..."
sudo cp "$DIR/ops/tradingai-sma3_high_trail-scanner.service" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable --now tradingai-sma3_high_trail-scanner
echo "Service installed and started."
