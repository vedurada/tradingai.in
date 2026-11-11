#!/bin/bash
set -euo pipefail
KEY="sma3_trail"
DIR="/opt/tradingai/sma3_trail_scanner"
SERVICE="tradingai-sma3_trail-scanner"
echo "=== SMA3 Trail Trail Scanner Status ==="
echo "Service:"; systemctl is-active "$SERVICE" 2>&1 || true
echo "Enabled:"; systemctl is-enabled "$SERVICE" 2>&1 || true
echo "DB:"; ls -l /opt/tradingai/database/sma3_trail.db 2>&1 || true
echo "Recent trades:"; sqlite3 /opt/tradingai/database/sma3_trail.db "SELECT COUNT(*) FROM sma3_trail_trades WHERE dataset='LIVE';" 2>&1 || true
echo "Today:"; sqlite3 /opt/tradingai/database/sma3_trail.db "SELECT COUNT(*), COALESCE(SUM(pnl_points),0) FROM sma3_trail_trades WHERE dataset='LIVE' AND trade_date=$(date +%F);" 2>&1 || true
