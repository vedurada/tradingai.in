#!/usr/bin/env bash
# Pre-market reminder: check the Zerodha token and record a clear status.
# Read-only. Does not exchange tokens or restart anything.
set -uo pipefail

LOG="/opt/tradingai/logs/token_check.log"
STATUS="/opt/tradingai/logs/token_status.txt"
ts=$(date '+%Y-%m-%d %H:%M:%S %Z')

mkdir -p /opt/tradingai/logs
out=$(/opt/tradingai/refresh_token.sh --check 2>&1)
rc=$?

if [[ $rc -eq 0 ]]; then
  printf '%s TOKEN_VALID\n' "$ts" | tee -a "$LOG" > "$STATUS"
else
  {
    printf '%s TOKEN_INVALID — run: sudo /opt/tradingai/refresh_token.sh <REQUEST_TOKEN>\n' "$ts"
    printf '%s\n' "$out" | tail -5
  } | tee -a "$LOG" > "$STATUS"
fi
exit 0
