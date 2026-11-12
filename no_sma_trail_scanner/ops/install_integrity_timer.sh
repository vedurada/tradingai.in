#!/bin/bash
set -euo pipefail
KEY="no_sma_trail"
SERVICE_FILE="/etc/systemd/system/tradingai-no_sma_trail-scanner.service"
echo "Installing NO-SMA Trail trail scanner service..."
sudo cp "$DIR/ops/tradingai-no_sma_trail-scanner.service" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable --now tradingai-no_sma_trail-scanner
echo "Service installed and started."
