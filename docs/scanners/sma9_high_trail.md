# `sma9_high_trail` — Trail variant of the HIGH scanner

> **Paper trading only.** This scanner never places a broker order. Fills are simulated in SQLite at the sampled option LTP.

## Identity

| Item | Value |
|---|---|
| Scanner key | `sma9_high_trail` |
| Family | Trail variant of the HIGH scanner |
| Strategy id | `sma9_high_trail` |
| Strategy type | `SMA_HIGH_BUY_ONLY` |
| Strategy version | `2.0.0` |
| Package VERSION file | `2.0.0` |
| Service unit | `tradingai-sma9_high_trail-scanner.service` |
| Service user / group | `sma9trailhigh` / `ubuntu` |
| Database | `/opt/tradingai/database/sma9_high_trail.db` |
| API namespace | `/api/sma9-high-trail/` |
| Dashboard | https://tradingai.in/live/sma9-high-trail/ |
| Code lock | no — normal writable source |

## Entry rule

Entry signals are **consumed from the base scanner `sma9_high`**. The trail scanner polls the base scanner's local status API every tick and, when the base has a new open position, copies that trade exactly once: same option type, strike, expiry, token, entry price, entry timestamp and entry candle.

```
GET https://127.0.0.1/api/sma9-high/scanner-status
Host: tradingai.in
```

A consumed base trade id is recorded in `sma9_high_trail_consumed_base_trades`, so a trail-stop exit never re-enters the same base trade while the base scanner is still holding it to candle close. The base scanner's own entry rule (shown below) is the single source of truth:

Candles are 5-minute **option-premium** candles. `completed` = all
candles except the still-forming last one; `prev` = the last completed candle;
`SMA9` = mean of the last 9 completed closes.

```
condition_a = prev.close > SMA9
condition_c = forming.open > SMA9
condition_b = LTP > prev.high
signal      = condition_a AND condition_c AND condition_b
```

All three conditions must be true; there is **no separate LTP > SMA
confirmation gate**. The entry may fire on any 5-second poll while the signal
holds. The paper fill is `round(LTP, 2)`.

Only the exit differs from the base scanner.

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
| `STRATEGY_ID` | `sma9_high_trail` |
| `STRATEGY_TYPE` | `SMA_HIGH_BUY_ONLY` |
| `STRATEGY_VERSION` | `2.0.0` |
| `SMA_PERIOD` | `9` |
| `CANDLE_MINUTES` | `5` |
| `POLL_SECONDS` | `5` |
| `POLL_OFFSET_SECONDS` | `3.0` |
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
| Entrypoint | `/opt/tradingai/sma9_high_trail_scanner/app/live_sma9_high_trail_scanner.py` |
| Strategy engine | `/opt/tradingai/sma9_high_trail_scanner/app/sma9_high_trail_engine.py` |
| Python path | `/opt/tradingai/sma9_high_trail_lib` |
| DB env var | `SMA9_HIGH_TRAIL_DB_PATH=/opt/tradingai/database/sma9_high_trail.db` |
| Log | `/opt/tradingai/logs/live_sma9_high_trail_scanner.log` |
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
systemctl status tradingai-sma9_high_trail-scanner.service --no-pager

# live log
tail -f /opt/tradingai/logs/live_sma9_high_trail_scanner.log

# API health (expect 200)
curl -sk -o /dev/null -w '%{http_code}\n' -H 'Host: tradingai.in' \
  https://127.0.0.1/api/sma9-high-trail/scanner-status

# DB writability as the service user (expect OK)
sudo runuser -u sma9trailhigh -g ubuntu -- python3 -c \
  'import sqlite3;c=sqlite3.connect("/opt/tradingai/database/sma9_high_trail.db");c.execute("BEGIN IMMEDIATE");c.rollback();print("OK")'

# restart
sudo systemctl restart tradingai-sma9_high_trail-scanner.service
```

This trail scanner is **not locked**. Edit the source, verify it compiles, then restart the unit. Its entries come from the base scanner's status API, so it stays aligned with the base rule automatically.

## Data

| Table | Purpose |
|---|---|
| `sma9_high_trail_trades` | closed paper trades |
| `sma9_high_trail_open_positions` | open CE/PE positions, including `hwm` and `stop` |
| `sma9_high_trail_scan_state` | key/value runtime state |
| `sma9_high_trail_consumed_base_trades` | base trade ids already consumed (prevents re-entry of the same base trade) |

`exit_reason` is `SAME_CANDLE_EXIT` or `TRAIL_STOP_EXIT`. `pnl_points = exit_price - entry_price`.

## Timing

- Session: 09:15–15:30 IST (status reporting).
- Entries: **09:20:00 ≤ now < 15:15:00**.
- First possible entry candle: 09:20. Last entry candle: 15:10.
- Exits and trail stops are **not** gated and still run after 15:15.
- Muhurat/special sessions use the `MUHURAT_SESSIONS` override for the session, but the entry window stays 09:20–15:15.
