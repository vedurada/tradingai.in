# sma3_high_trail — Trail Scanner

**Paper trading only.** No broker order is ever placed. Fills are simulated in
SQLite at the sampled option LTP.

BUY-only ATM NIFTY CE/PE. Entry is inherited unchanged from the base
`sma3_high` scanner; exit uses a 5-point trailing stop.

- Strategy id: `sma3_high_trail`
- Entry: prev close > SMA3 **and** LTP > prev candle high **and** LTP > SMA3
- Exit: 5-pt trailing stop (activates at +5, stop = peak − 5); otherwise at the
  close of the entry 5-minute candle
- Service: `tradingai-sma3_high_trail-scanner.service` (user `sma3trailhigh`)
- Database: `/opt/tradingai/database/sma3_high_trail.db`
- API: `/api/sma3-high-trail/`
- Dashboard: https://tradingai.in/live/sma3-high-trail/
- Log: `/opt/tradingai/logs/live_sma3_high_trail_scanner.log`
- Python path: `/opt/tradingai/sma3_high_trail_lib`
- Dependencies: Python 3.10 + `kiteconnect==5.2.2`
  (see `/opt/tradingai/docs/requirements.txt`)
- Full documentation: `/opt/tradingai/docs/scanners/sma3_high_trail.md`

## Configuration

| Constant | Value |
|---|---|
| `STRATEGY_ID` | `sma3_high_trail` |
| `SMA_PERIOD` | `3` |
| `ENTRY_TYPE` | `sma_high` |
| `CANDLE_MINUTES` | `5` |
| `POLL_SECONDS` | `5` |
| `POLL_OFFSET_SECONDS` | `2.4` |
| `TRAIL` | `5.0` |
| `ACTIVATE` | `5.0` |
| `ENTRY_START` | `09:20` |
| `ENTRY_END` | `15:15` (exclusive) |
| ATM step | `round(spot / 50) * 50` |
| Expiry | nearest NIFTY expiry ≥ today |
| Lot size (reference) | `65` |

## Exit rule

```
hwm = max(hwm, LTP)
if hwm - entry >= 5.0:
    stop = entry
    stop = max(stop, hwm - 5.0)
if stop > entry and LTP <= stop:
    exit at round(LTP, 2)      # TRAIL_STOP_EXIT
else:
    exit at entry-candle close # SAME_CANDLE_EXIT
```

No stop-loss. Breakeven/losing stops are ignored. Exit price is the actual
sampled LTP at the breach.

## Operations

```bash
systemctl status tradingai-sma3_high_trail-scanner.service --no-pager
tail -f /opt/tradingai/logs/live_sma3_high_trail_scanner.log
curl -sk -o /dev/null -w '%{http_code}\n' -H 'Host: tradingai.in' \
  https://127.0.0.1/api/sma3-high-trail/scanner-status
sudo runuser -u sma3trailhigh -g ubuntu -- python3 -c \
  'import sqlite3;c=sqlite3.connect("/opt/tradingai/database/sma3_high_trail.db");c.execute("BEGIN IMMEDIATE");c.rollback();print("OK")'
sudo systemctl restart tradingai-sma3_high_trail-scanner.service
```

## Data

Tables: `sma3_high_trail_trades`, `sma3_high_trail_open_positions` (includes `hwm`, `stop`),
`sma3_high_trail_scan_state`.

## Timing

Session 09:15–15:30 IST; entries only 09:20:00–15:14:59 (last entry candle
15:10). Exits and trail stops still run after 15:15.
