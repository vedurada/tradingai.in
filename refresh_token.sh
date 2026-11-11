#!/usr/bin/env bash
# TradingAI — one-command Zerodha token refresh + full stack restart + checks.
# Paper trading only. Never prints request/access tokens or secrets.
#
# Usage:
#   sudo /opt/tradingai/refresh_token.sh <REQUEST_TOKEN>   # exchange + restart + verify
#   sudo /opt/tradingai/refresh_token.sh                   # uses /tmp/request_token.txt
#   sudo /opt/tradingai/refresh_token.sh --verify          # verify token + DB + API only
#   sudo /opt/tradingai/refresh_token.sh --check           # token check only (timer)
#
# Get the request_token from the Kite login redirect URL after logging in.
set -uo pipefail

PROJECT="/opt/tradingai"
LIB="$PROJECT/sma9_lib"
REQ_FILE="/tmp/request_token.txt"
EXCHANGE="$PROJECT/app/zerodha/token_exchange.py"

BASE_UNITS=(
  tradingai-sma3-scanner tradingai-sma9-scanner tradingai-sma20-scanner
  tradingai-sma3-high-scanner tradingai-sma9-high-scanner
  tradingai-sma20-high-scanner tradingai-no-sma-scanner
)
TRAIL_UNITS=(
  tradingai-sma3_trail-scanner tradingai-sma9_trail-scanner
  tradingai-sma20_trail-scanner tradingai-sma3_high_trail-scanner
  tradingai-sma9_high_trail-scanner tradingai-sma20_high_trail-scanner
  tradingai-no_sma_trail-scanner
)
ALL_UNITS=("${BASE_UNITS[@]}" "${TRAIL_UNITS[@]}" tradingai-api)

FAIL=0
ok()  { printf '  [OK]   %s\n' "$*"; }
bad() { printf '  [FAIL] %s\n' "$*"; FAIL=1; }
say() { printf '%s\n' "$*"; }

mode="run"
case "${1:-}" in
  --verify) mode="verify" ;;
  --check)  mode="check" ;;
  --help|-h) sed -n '2,14p' "$0"; exit 0 ;;
esac

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  say "ERROR: run this with sudo"
  exit 1
fi

token_check() {
  local out rc
  out=$(env PYTHONPATH="$PROJECT:$LIB" python3 - <<'PY' 2>&1
import sys
try:
    from kiteconnect import KiteConnect
    from zerodha_credentials import load_credentials
    c = load_credentials()
    k = KiteConnect(api_key=c["KITE_API_KEY"])
    k.set_access_token(c["KITE_ACCESS_TOKEN"])
    p = k.profile()
    print("TOKEN_OK user_id=%s user_name=%s" % (p.get("user_id"), p.get("user_name")))
except Exception as e:
    print("TOKEN_BAD %s: %s" % (type(e).__name__, str(e).strip().replace("\n", " ")[:160]))
    sys.exit(1)
PY
)
  rc=$?
  if [[ $rc -eq 0 ]]; then ok "$out"; else bad "$out"; fi
}

db_check() {
  local pairs=(
    "sma3:ubuntu" "sma9:ubuntu" "sma20:ubuntu"
    "sma3_high:sma3high" "sma9_high:sma9high" "sma20_high:sma20high"
    "no_sma:nosma"
    "sma3_trail:sma3trail" "sma9_trail:sma9trail" "sma20_trail:sma20trail"
    "sma3_high_trail:sma3trailhigh" "sma9_high_trail:sma9trailhigh"
    "sma20_high_trail:sma20trailhigh" "no_sma_trail:nosmatrail"
  )
  local pair db user out
  for pair in "${pairs[@]}"; do
    db=${pair%%:*}; user=${pair##*:}
    out=$(runuser -u "$user" -g ubuntu -- python3 -c "
import sqlite3
c = sqlite3.connect('/opt/tradingai/database/$db.db', timeout=5)
c.execute('BEGIN IMMEDIATE'); c.rollback(); c.close()
print('WRITABLE')
" 2>&1 | tail -1)
    if [[ "$out" == "WRITABLE" ]]; then
      ok "db $db writable"
    else
      bad "db $db: $out"
    fi
  done
}

api_check() {
  local keys=(
    sma3 sma9 sma20 sma3-high sma9-high sma20-high no-sma
    sma3-trail sma9-trail sma20-trail sma3-high-trail
    sma9-high-trail sma20-high-trail no-sma-trail
  )
  local k code
  for k in "${keys[@]}"; do
    code=$(curl -sk -o /dev/null -w '%{http_code}' \
      -H 'Host: tradingai.in' "https://127.0.0.1/api/$k/scanner-status")
    if [[ "$code" == "200" ]]; then ok "api/$k 200"; else bad "api/$k $code"; fi
  done
}

# --- exchange (run mode only) ---------------------------------------------
if [[ "$mode" == "run" ]]; then
  if [[ $# -ge 1 && "${1:-}" != --* ]]; then
    umask 077
    printf '%s' "$1" > "$REQ_FILE"
  fi
  if [[ ! -s "$REQ_FILE" ]]; then
    say "ERROR: no request token supplied."
    say "Log in to Kite, copy request_token from the redirect URL, then run:"
    say "  sudo $0 <REQUEST_TOKEN>"
    exit 1
  fi
  chmod 600 "$REQ_FILE"
  say "== exchanging request token =="
  if ! env PYTHONPATH="$LIB" python3 "$EXCHANGE"; then
    say "Token exchange FAILED. Services were NOT restarted."
    exit 1
  fi
fi

# --- token check -----------------------------------------------------------
say "== token check =="
token_check

if [[ "$mode" == "check" ]]; then
  if [[ $FAIL -eq 0 ]]; then say "RESULT: TOKEN VALID"; else say "RESULT: TOKEN INVALID"; fi
  exit $FAIL
fi

# --- restart (run mode only) ----------------------------------------------
if [[ "$mode" == "run" ]]; then
  say "== restarting all scanners + API =="
  if systemctl restart "${ALL_UNITS[@]}"; then
    ok "restart issued for ${#ALL_UNITS[@]} units"
  else
    bad "systemctl restart returned an error"
  fi
  say "== waiting for services to come up =="
  sleep 8
fi

# --- service state ---------------------------------------------------------
say "== service state =="
for u in "${ALL_UNITS[@]}"; do
  st=$(systemctl is-active "$u")
  if [[ "$st" == "active" ]]; then ok "$u active"; else bad "$u $st"; fi
done

# --- databases -------------------------------------------------------------
say "== database writability =="
db_check

# --- API -------------------------------------------------------------------
say "== API health =="
api_check

say "== summary =="
if [[ $FAIL -eq 0 ]]; then
  say "ALL CHECKS PASSED"
  say "Instrument load takes ~90s after restart; first scan at 09:15."
else
  say "SOME CHECKS FAILED — inspect logs in /opt/tradingai/logs/"
fi
exit $FAIL
