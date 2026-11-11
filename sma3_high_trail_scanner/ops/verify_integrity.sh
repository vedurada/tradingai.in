#!/bin/bash
set -euo pipefail
DIR="/opt/tradingai/sma3_high_trail_scanner"
echo "Verifying SMA3 HIGH Trail trail scanner code integrity..."
MANIFEST="$DIR/MANIFEST.sha256"
if [ ! -f "$MANIFEST" ]; then
    echo "No manifest found. Run lock_code.sh first."
    exit 1
fi
cd "$DIR"
sha256sum -c "$MANIFEST" --quiet 2>&1 || { echo "INTEGRITY CHECK FAILED"; exit 1; }
echo "Integrity OK."
