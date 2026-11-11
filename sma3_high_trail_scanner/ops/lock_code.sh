#!/bin/bash
set -euo pipefail
DIR="/opt/tradingai/sma3_high_trail_scanner"
LIB="/opt/tradingai/sma3_high_trail_lib"
echo "Locking SMA3 HIGH Trail trail scanner code..."
sudo chown -R root:root "$DIR" "$LIB"
sudo find "$DIR" "$LIB" -type d -exec chmod 755 {} +
sudo find "$DIR" "$LIB" -type f -exec chmod 644 {} +
sudo find "$DIR" "$LIB" -type f -name "*.py" -exec chmod 755 {} +
sudo chattr +i "$DIR" "$LIB" 2>/dev/null || true
sudo find "$DIR" "$LIB" -type d -exec chattr +i {} + 2>/dev/null || true
sudo find "$DIR" "$LIB" -type f -exec chattr +i {} + 2>/dev/null || true
# Manifest
MANIFEST="$DIR/MANIFEST.sha256"
sudo find "$DIR" "$LIB" -type f \( -name "*.py" -o -name "*.html" -o -name "*.service" -o -name "*.sh" \) | sort | xargs sha256sum | sudo tee "$MANIFEST" > /dev/null
sudo chmod 644 "$MANIFEST"
echo "Locked. Manifest: $MANIFEST"
