# `sma20` — Base SMA scanner

> **Paper trading only.** This scanner never places a broker order. Fills are simulated in SQLite at the sampled option LTP.

## Identity

| Item | Value |
|---|---|
| Scanner key | `sma20` |
| Family | Base SMA scanner |
| Strategy id | `sma20_only` |
| Strategy type | `SMA20_BUY_ONLY` |
| Strategy version | `20.1.0` |
| Package VERSION file | `20.1.0-2026-11-12` |
| Service unit | `tradingai-sma20-scanner.service` |
| Service user / group | `sma20` / `ubuntu` |
| Database | `/opt/tradingai/database/sma20.db` |
| API namespace | `/api/sma20/` |
| Dashboard | https://tradingai.in/live/sma20/ |
| Code lock | yes — root:root 444 + `chattr +i` |

## Entry rule

Candles are 5-minute **option-premium** candles. `completed` = all
candles except the still-forming last one; `prev` = the last completed candle;
`SMA20` = mean of the last 20 completed closes.

```
condition_a = prev.close > SMA20
condition_b = forming.open > SMA20
signal      = condition_a AND condition_b
```

Both conditions must be true; there is **no separate LTP > SMA confirmation
gate**. The entry may fire on any 5-second poll while the signal holds. The
paper fill is `round(LTP, 2)`.

## Exit rule

Exit at the **close of the entry 5-minute candle** (`SAME_CANDLE_EXIT`).
There is no stop-loss and no carry-forward.

## Configuration

| Constant | Value |
|---|---|
| `STRATEGY_ID` | `sma20_only` |
| `STRATEGY_TYPE` | `SMA20_BUY_ONLY` |
| `STRATEGY_VERSION` | `20.1.0` |
| `SMA_PERIOD` | `20` |
| `CANDLE_MINUTES` | `5` |
| `POLL_SECONDS` | `5` |
| `POLL_OFFSET_SECONDS` | `0` |
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
| Entrypoint | `/opt/tradingai/sma20_scanner/app/live_sma20_scanner.py` |
| Strategy engine | `/opt/tradingai/sma20_scanner/app/sma20_engine.py` |
| Python path | `/opt/tradingai/sma20_lib` |
| DB env var | `SMA20_DB_PATH=/opt/tradingai/database/sma20.db` |
| Log | `/opt/tradingai/logs/live_sma20_scanner.log` |
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
systemctl status tradingai-sma20-scanner.service --no-pager

# live log
tail -f /opt/tradingai/logs/live_sma20_scanner.log

# API health (expect 200)
curl -sk -o /dev/null -w '%{http_code}\n' -H 'Host: tradingai.in' \
  https://127.0.0.1/api/sma20/scanner-status

# DB writability as the service user (expect OK)
sudo runuser -u sma20 -g ubuntu -- python3 -c \
  'import sqlite3;c=sqlite3.connect("/opt/tradingai/database/sma20.db");c.execute("BEGIN IMMEDIATE");c.rollback();print("OK")'

# restart
sudo systemctl restart tradingai-sma20-scanner.service
```

This is a **locked base scanner**. Apply changes only through the approved cycle:

```bash
sudo /opt/tradingai/sma20_scanner/ops/unlock_code.sh
# edit + test
sudo /opt/tradingai/sma20_scanner/ops/lock_code.sh
sudo systemctl restart tradingai-sma20-scanner.service
```

Integrity check: `sudo /opt/tradingai/sma20_scanner/ops/verify_integrity.sh` (also runs from a 15-minute systemd timer).

## Data

| Table | Purpose |
|---|---|
| `sma20_trades` | closed paper trades |
| `sma20_open_positions` | open CE/PE positions |
| `sma20_scan_state` | key/value runtime state |

`exit_reason` is `SAME_CANDLE_EXIT`. `pnl_points = exit_price - entry_price`.

## Timing

- Session: 09:15–15:30 IST (status reporting).
- Entries: **09:20:00 ≤ now < 15:15:00**.
- First possible entry candle: 09:20. Last entry candle: 15:10.
- Exits and trail stops are **not** gated and still run after 15:15.
- Muhurat/special sessions use the `MUHURAT_SESSIONS` override for the session, but the entry window stays 09:20–15:15.
