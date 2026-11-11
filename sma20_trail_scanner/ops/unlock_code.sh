#!/bin/bash
set -euo pipefail
DIR="/opt/tradingai/sma20_trail_scanner"
LIB="/opt/tradingai/sma20_trail_lib"
echo "Unlocking SMA20 Trail trail scanner code..."
sudo chattr -i "$DIR" "$LIB" 2>/dev/null || true
sudo find "$DIR" "$LIB" -type d -exec chattr -i {} + 2>/dev/null || true
sudo find "$DIR" "$LIB" -type f -exec chattr -i {} + 2>/dev/null || true
sudo chown -R sma20trail:ubuntu "$DIR" "$LIB"
sudo find "$DIR" "$LIB" -type d -exec chmod 755 {} +
sudo find "$DIR" "$LIB" -type f -exec chmod 644 {} +
echo "Unlocked. Files owned by sma20trail:ubuntu"
