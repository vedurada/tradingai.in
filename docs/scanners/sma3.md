# `sma3` — Base SMA scanner

> **Paper trading only.** This scanner never places a broker order. Fills are simulated in SQLite at the sampled option LTP.

## Identity

| Item | Value |
|---|---|
| Scanner key | `sma3` |
| Family | Base SMA scanner |
| Strategy id | `sma3_only` |
| Strategy type | `SMA3_BUY_ONLY` |
| Strategy version | `3.1.0` |
| Package VERSION file | `3.1.0-2026-11-12` |
| Service unit | `tradingai-sma3-scanner.service` |
| Service user / group | `sma3` / `ubuntu` |
| Database | `/opt/tradingai/database/sma3.db` |
| API namespace | `/api/sma3/` |
| Dashboard | https://tradingai.in/live/sma3/ |
| Code lock | yes — root:root 444 + `chattr +i` |

## Entry rule

Candles are 5-minute **option-premium** candles. `completed` = all
candles except the still-forming last one; `prev` = the last completed candle;
`SMA3` = mean of the last 3 completed closes.

```
condition_a = prev.close > SMA3
condition_b = forming.open > SMA3
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
| `STRATEGY_ID` | `sma3_only` |
| `STRATEGY_TYPE` | `SMA3_BUY_ONLY` |
| `STRATEGY_VERSION` | `3.1.0` |
| `SMA_PERIOD` | `3` |
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
| Entrypoint | `/opt/tradingai/sma3_scanner/app/live_sma3_scanner.py` |
| Strategy engine | `/opt/tradingai/sma3_scanner/app/sma3_engine.py` |
| Python path | `/opt/tradingai/sma3_lib` |
| DB env var | `SMA3_DB_PATH=/opt/tradingai/database/sma3.db` |
| Log | `/opt/tradingai/logs/live_sma3_scanner.log` |
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
systemctl status tradingai-sma3-scanner.service --no-pager

# live log
tail -f /opt/tradingai/logs/live_sma3_scanner.log

# API health (expect 200)
curl -sk -o /dev/null -w '%{http_code}\n' -H 'Host: tradingai.in' \
  https://127.0.0.1/api/sma3/scanner-status

# DB writability as the service user (expect OK)
sudo runuser -u sma3 -g ubuntu -- python3 -c \
  'import sqlite3;c=sqlite3.connect("/opt/tradingai/database/sma3.db");c.execute("BEGIN IMMEDIATE");c.rollback();print("OK")'

# restart
sudo systemctl restart tradingai-sma3-scanner.service
```

This is a **locked base scanner**. Apply changes only through the approved cycle:

```bash
sudo /opt/tradingai/sma3_scanner/ops/unlock_code.sh
# edit + test
sudo /opt/tradingai/sma3_scanner/ops/lock_code.sh
sudo systemctl restart tradingai-sma3-scanner.service
```

Integrity check: `sudo /opt/tradingai/sma3_scanner/ops/verify_integrity.sh` (also runs from a 15-minute systemd timer).

## Data

| Table | Purpose |
|---|---|
| `sma3_trades` | closed paper trades |
| `sma3_open_positions` | open CE/PE positions |
| `sma3_scan_state` | key/value runtime state |

`exit_reason` is `SAME_CANDLE_EXIT`. `pnl_points = exit_price - entry_price`.

## Timing

- Session: 09:15–15:30 IST (status reporting).
- Entries: **09:20:00 ≤ now < 15:15:00**.
- First possible entry candle: 09:20. Last entry candle: 15:10.
- Exits and trail stops are **not** gated and still run after 15:15.
- Muhurat/special sessions use the `MUHURAT_SESSIONS` override for the session, but the entry window stays 09:20–15:15.
