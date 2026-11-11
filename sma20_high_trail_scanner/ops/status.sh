#!/bin/bash
set -euo pipefail
KEY="sma20_high_trail"
DIR="/opt/tradingai/sma20_high_trail_scanner"
SERVICE="tradingai-sma20_high_trail-scanner"
echo "=== SMA20 HIGH Trail Trail Scanner Status ==="
echo "Service:"; systemctl is-active "$SERVICE" 2>&1 || true
echo "Enabled:"; systemctl is-enabled "$SERVICE" 2>&1 || true
echo "DB:"; ls -l /opt/tradingai/database/sma20_high_trail.db 2>&1 || true
echo "Recent trades:"; sqlite3 /opt/tradingai/database/sma20_high_trail.db "SELECT COUNT(*) FROM sma20_high_trail_trades WHERE dataset='LIVE';" 2>&1 || true
echo "Today:"; sqlite3 /opt/tradingai/database/sma20_high_trail.db "SELECT COUNT(*), COALESCE(SUM(pnl_points),0) FROM sma20_high_trail_trades WHERE dataset='LIVE' AND trade_date=$(date +%F);" 2>&1 || true
