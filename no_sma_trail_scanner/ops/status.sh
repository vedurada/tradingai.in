#!/bin/bash
set -euo pipefail
KEY="no_sma_trail"
DIR="/opt/tradingai/no_sma_trail_scanner"
SERVICE="tradingai-no_sma_trail-scanner"
echo "=== NO-SMA Trail Trail Scanner Status ==="
echo "Service:"; systemctl is-active "$SERVICE" 2>&1 || true
echo "Enabled:"; systemctl is-enabled "$SERVICE" 2>&1 || true
echo "DB:"; ls -l /opt/tradingai/database/no_sma_trail.db 2>&1 || true
echo "Recent trades:"; sqlite3 /opt/tradingai/database/no_sma_trail.db "SELECT COUNT(*) FROM no_sma_trail_trades WHERE dataset='LIVE';" 2>&1 || true
echo "Today:"; sqlite3 /opt/tradingai/database/no_sma_trail.db "SELECT COUNT(*), COALESCE(SUM(pnl_points),0) FROM no_sma_trail_trades WHERE dataset='LIVE' AND trade_date=$(date +%F);" 2>&1 || true
