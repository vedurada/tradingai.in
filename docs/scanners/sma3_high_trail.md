# `sma3_high_trail` — Trail variant of the HIGH scanner

> **Paper trading only.** This scanner never places a broker order. Fills are simulated in SQLite at the sampled option LTP.

## Identity

| Item | Value |
|---|---|
| Scanner key | `sma3_high_trail` |
| Family | Trail variant of the HIGH scanner |
| Strategy id | `sma3_high_trail` |
| Strategy type | `SMA_HIGH_BUY_ONLY` |
| Strategy version | `1.0.0` |
| Package VERSION file | `1.0.0` |
| Service unit | `tradingai-sma3_high_trail-scanner.service` |
| Service user / group | `sma3trailhigh` / `ubuntu` |
| Database | `/opt/tradingai/database/sma3_high_trail.db` |
| API namespace | `/api/sma3-high-trail/` |
| Dashboard | https://tradingai.in/live/sma3-high-trail/ |
| Code lock | no — normal writable source |

## Entry rule

Entry is inherited unchanged from the base scanner `sma3_high`.

Candles are 5-minute **option-premium** candles. `completed` = all
candles except the still-forming last one; `prev` = the last completed candle;
`SMA3` = mean of the last 3 completed closes.

```
condition_a  = forming.open > SMA3
condition_b  = LTP > prev.high
confirmation = LTP > SMA3
signal       = condition_a AND condition_b AND confirmation
```

The entry may fire on any 5-second poll while all three conditions hold. The
paper fill is `round(LTP, 2)`.

The entry logic is identical to `sma3_high`; only the exit differs.

## Exit rule

Exit is checked on every poll, **before** the candle-close exit:

```
hwm = max(hwm, LTP)
if hwm - entry >= ACTIVATE (5.0):
    stop = entry                      # first activation = breakeven
    stop = max(stop, hwm - TRAIL)     # ratchet up only
if stop is not None and stop > entry and LTP <= stop:
    exit at round(LTP, 2)             # actual sampled LTP at breach
    reason = TRAIL_STOP_EXIT
else:
    exit at the close of the entry candle
```

- `TRAIL = 5.0`, `ACTIVATE = 5.0`.
- There is **no stop-loss**. A breakeven or losing stop is ignored; the trade
  runs to candle close.
- The exit price is the actual LTP sampled at the breach, not the idealized
  stop level.
- `hwm` and `stop` are persisted in `open_positions`, so a restart resumes the
  trail correctly.

## Configuration

| Constant | Value |
|---|---|
| `STRATEGY_ID` | `sma3_high_trail` |
| `STRATEGY_TYPE` | `SMA_HIGH_BUY_ONLY` |
| `STRATEGY_VERSION` | `1.0.0` |
| `SMA_PERIOD` | `3` |
| `CANDLE_MINUTES` | `5` |
| `POLL_SECONDS` | `5` |
| `POLL_OFFSET_SECONDS` | `2.4` |
| `TRAIL` | `5.0` points |
| `ACTIVATE` | `5.0` points |
| `ENTRY_TYPE` | `sma_high` |
| `ENTRY_START` | `09:20` |
| `ENTRY_END` | `15:15` (exclusive) |
| Market session | `09:15`–`15:30` (status only) |
| ATM step | `round(spot / 50) * 50` |
| Expiry | nearest NIFTY expiry ≥ today |
| Instrument / timeframe | `NIFTY` / `5m` |
| Lot size (reference) | `65` |

## Runtime

| Item | Value |
|---|---|
| Entrypoint | `/opt/tradingai/sma3_high_trail_scanner/app/live_sma3_high_trail_scanner.py` |
| Strategy engine | `/opt/tradingai/sma3_high_trail_scanner/app/sma3_high_trail_engine.py` |
| Python path | `/opt/tradingai/sma3_high_trail_lib` |
| DB env var | `SMA3_HIGH_TRAIL_DB_PATH=/opt/tradingai/database/sma3_high_trail.db` |
| Log | `/opt/tradingai/logs/live_sma3_high_trail_scanner.log` |
| Working directory | `/opt/tradingai` |
| Restart policy | `Restart=always`, `RestartSec=5` |
| Bytecode | `PYTHONDONTWRITEBYTECODE=1` |

## Dependencies

- Python 3.10 (system `/usr/bin/python3`).
- Third-party: `kiteconnect==5.2.2` (lazy import inside the broker connection).
- Transitive runtime deps from system dist-packages: `requests`, `six`, `pyOpenSSL`, `python-dateutil`, `twisted`, `service_identity`, `autobahn`.
- Standard library only for strategy/state: `json`, `logging`, `os`, `sqlite3`, `sys`, `time`, `traceback`, `random`, `datetime`, `zoneinfo`, `collections`, `csv`, `dataclasses`, `hashlib`, `subprocess`, `typing`.
- No database server, no pandas/numpy, no web framework in the scanner process.
- Canonical list: `/opt/tradingai/docs/requirements.txt`.

## Operations

```bash
# service state
systemctl status tradingai-sma3_high_trail-scanner.service --no-pager

# live log
tail -f /opt/tradingai/logs/live_sma3_high_trail_scanner.log

# API health (expect 200)
curl -sk -o /dev/null -w '%{http_code}\n' -H 'Host: tradingai.in' \
  https://127.0.0.1/api/sma3-high-trail/scanner-status

# DB writability as the service user (expect OK)
sudo runuser -u sma3trailhigh -g ubuntu -- python3 -c \
  'import sqlite3;c=sqlite3.connect("/opt/tradingai/database/sma3_high_trail.db");c.execute("BEGIN IMMEDIATE");c.rollback();print("OK")'

# restart
sudo systemctl restart tradingai-sma3_high_trail-scanner.service
```

This trail scanner is **not locked**. Edit the source, verify it compiles, then restart the unit. Keep it in sync with the corresponding base scanner's entry logic.

## Data

| Table | Purpose |
|---|---|
| `sma3_high_trail_trades` | closed paper trades |
| `sma3_high_trail_open_positions` | open CE/PE positions, including `hwm` and `stop` |
| `sma3_high_trail_scan_state` | key/value runtime state |

`exit_reason` is `SAME_CANDLE_EXIT` or `TRAIL_STOP_EXIT`. `pnl_points = exit_price - entry_price`.

## Timing

- Session: 09:15–15:30 IST (status reporting).
- Entries: **09:20:00 ≤ now < 15:15:00**.
- First possible entry candle: 09:20. Last entry candle: 15:10.
- Exits and trail stops are **not** gated and still run after 15:15.
- Muhurat/special sessions use the `MUHURAT_SESSIONS` override for the session, but the entry window stays 09:20–15:15.
