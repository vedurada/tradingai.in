#!/bin/bash
set -euo pipefail
KEY="sma9_high_trail"
DIR="/opt/tradingai/sma9_high_trail_scanner"
SERVICE="tradingai-sma9_high_trail-scanner"
echo "=== SMA9 HIGH Trail Trail Scanner Status ==="
echo "Service:"; systemctl is-active "$SERVICE" 2>&1 || true
echo "Enabled:"; systemctl is-enabled "$SERVICE" 2>&1 || true
echo "DB:"; ls -l /opt/tradingai/database/sma9_high_trail.db 2>&1 || true
echo "Recent trades:"; sqlite3 /opt/tradingai/database/sma9_high_trail.db "SELECT COUNT(*) FROM sma9_high_trail_trades WHERE dataset='LIVE';" 2>&1 || true
echo "Today:"; sqlite3 /opt/tradingai/database/sma9_high_trail.db "SELECT COUNT(*), COALESCE(SUM(pnl_points),0) FROM sma9_high_trail_trades WHERE dataset='LIVE' AND trade_date=$(date +%F);" 2>&1 || true
