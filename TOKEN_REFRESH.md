# Zerodha token refresh — morning runbook

Zerodha Kite access tokens do **not** survive to the next trading day. If the
token is not refreshed before 09:15, every scanner stays `active` but logs
`Incorrect api_key or access_token` and makes **zero trades** (this happened on
2026-11-10).

## One command (before 09:15)

1. Log in to Kite and copy the `request_token` from the redirect URL.
2. Run:

```bash
sudo /opt/tradingai/refresh_token.sh <REQUEST_TOKEN>
```

That single command:

- exchanges and verifies the token (value never printed),
- atomically persists it to `/opt/tradingai/.env.zerodha`,
- restarts all 7 base scanners, all 7 trail scanners, and the API,
- checks every service is `active`,
- checks all 14 databases are writable as their service users,
- checks all 14 scanner-status APIs return `200`.

If the exchange fails, it stops and does **not** restart the services.

## Other modes

```bash
sudo /opt/tradingai/refresh_token.sh --verify   # token + DB + API checks, no restart
sudo /opt/tradingai/refresh_token.sh --check    # token check only
```

If you prefer not to pass the token on the command line, write it to
`/tmp/request_token.txt` and run the script with no argument. The file is
removed after a successful exchange.

## Automatic reminder

A systemd timer runs `premarket_token_check.sh` at **08:45 IST, Mon–Fri** and
records the result in:

```bash
cat /opt/tradingai/logs/token_status.txt
tail -20 /opt/tradingai/logs/token_check.log
```

If it says `TOKEN_INVALID`, run the one-command refresh above. The check is
read-only: it never exchanges a token or restarts anything.

Check the timer:

```bash
systemctl list-timers tradingai-token-check.timer
```

## Manual fallback

```bash
echo '<REQUEST_TOKEN>' | sudo tee /tmp/request_token.txt >/dev/null
sudo chmod 600 /tmp/request_token.txt
sudo env PYTHONPATH=/opt/tradingai/sma9_lib \
  python3 /opt/tradingai/app/zerodha/token_exchange.py
sudo systemctl restart \
  tradingai-sma3-scanner tradingai-sma9-scanner tradingai-sma20-scanner \
  tradingai-sma3-high-scanner tradingai-sma9-high-scanner \
  tradingai-sma20-high-scanner tradingai-no-sma-scanner \
  tradingai-sma3_trail-scanner tradingai-sma9_trail-scanner \
  tradingai-sma20_trail-scanner tradingai-sma3_high_trail-scanner \
  tradingai-sma9_high_trail-scanner tradingai-sma20_high_trail-scanner \
  tradingai-no_sma_trail-scanner tradingai-api
```
