# TradingAI Paper Scanners — Master Documentation

Complete reference for the 14 BUY-only NIFTY option-premium paper scanners
running on the TradingAI VM.

> **Paper trading only.** No scanner can place a broker order. There is no
> `place_order` call, no order id, and no broker write path anywhere in this
> stack. Every fill is simulated in SQLite at the sampled option LTP.

---

## 1. What runs on the box

| # | Scanner key | Family | Entry logic | Exit logic |
|---|---|---|---|---|
| 1 | `sma3` | Base SMA | prev close > SMA3 **or** forming open > SMA3, and LTP > SMA3 | entry-candle close |
| 2 | `sma9` | Base SMA | prev close > SMA9 **or** forming open > SMA9, and LTP > SMA9 | entry-candle close |
| 3 | `sma20` | Base SMA | prev close > SMA20 **or** forming open > SMA20, and LTP > SMA20 | entry-candle close |
| 4 | `sma3_high` | HIGH | forming open > SMA3 **and** LTP > prev candle high **and** LTP > SMA3 | entry-candle close |
| 5 | `sma9_high` | HIGH | forming open > SMA9 **and** LTP > prev candle high **and** LTP > SMA9 | entry-candle close |
| 6 | `sma20_high` | HIGH | forming open > SMA20 **and** LTP > prev candle high **and** LTP > SMA20 | entry-candle close |
| 7 | `no_sma` | NO-SMA | LTP > previous completed candle high | entry-candle close |
| 8 | `sma3_trail` | Trail | inherits `sma3` | 5-pt trailing stop, else candle close |
| 9 | `sma9_trail` | Trail | inherits `sma9` | 5-pt trailing stop, else candle close |
| 10 | `sma20_trail` | Trail | inherits `sma20` | 5-pt trailing stop, else candle close |
| 11 | `sma3_high_trail` | Trail | inherits `sma3_high` | 5-pt trailing stop, else candle close |
| 12 | `sma9_high_trail` | Trail | inherits `sma9_high` | 5-pt trailing stop, else candle close |
| 13 | `sma20_high_trail` | Trail | inherits `sma20_high` | 5-pt trailing stop, else candle close |
| 14 | `no_sma_trail` | Trail | inherits `no_sma` | 5-pt trailing stop, else candle close |

Each scanner is a **fully independent stack**: own code directory, own Python
library directory, own SQLite database, own unprivileged service user, own
systemd unit, own API namespace and own dashboard page. Nothing is shared
except the host, the Kite credentials, the Flask API process and nginx.

---

## 2. Requirements

### 2.1 Host

| Item | Current value / requirement |
|---|---|
| OS | Ubuntu 22.04.5 LTS (systemd, `chattr`, `logrotate`) |
| Kernel | 6.8.x |
| CPU | 2 vCPU (AMD EPYC) |
| RAM | 956 MB — tight but sufficient for 14 Python processes |
| Swap | 2 GB swapfile (used as headroom, not steady state) |
| Disk | 45 GB, ~21 GB free |
| Python | 3.10.12 (`/usr/bin/python3`) |
| SQLite | 3.37.2 (library + CLI for inspection) |
| Network | outbound HTTPS to `api.kite.trade`; inbound HTTPS via nginx + Cloudflare |
| Database server | **none required** — MySQL/PostgreSQL are not used or installed for this stack |

### 2.2 Zerodha / Kite Connect

| Item | Detail |
|---|---|
| Product | Kite Connect (market data) |
| API key / secret | stored in `/opt/tradingai/.env.zerodha` (mode `640 ubuntu:ubuntu`) |
| Access token | **expires every day**; must be refreshed before 09:15 IST |
| Rate limits | quotes ≈ 1 request/second per API key; historical ≈ 3 requests/second per API key |
| Instruments | NIFTY options (nearest expiry), NIFTY spot quote |

Token refresh runbook: `/opt/tradingai/TOKEN_REFRESH.md`.
Automatic check: `tradingai-token-check.timer` at **08:45 IST, Mon–Fri**.

### 2.3 Python packages

**Runtime third-party dependency (all 14 scanners):**

```
kiteconnect==5.2.2
```

`kiteconnect` is imported lazily inside the broker connection method. The
scanner process starts without it, but cannot load instruments or quotes.

Transitive dependencies are already present in the system Python 3.10
`dist-packages`:

| Package | Installed |
|---|---|
| requests | 2.32.5 |
| six | 1.16.0 |
| pyOpenSSL | 21.0.0 |
| python-dateutil | 2.9.0.post0 |
| twisted | 22.1.0 |
| service_identity | present |
| autobahn | 19.11.2 |

**Standard library only** for all strategy logic: `json`, `logging`, `os`,
`sqlite3`, `sys`, `time`, `traceback`, `random`, `datetime`, `zoneinfo`,
`collections`, `csv`, `dataclasses`, `hashlib`, `subprocess`, `typing`.

**Isolation model:** each unit sets `PYTHONPATH=/opt/tradingai/<key>_lib`.
That directory is searched first, then the system `dist-packages`. Each lib
directory is a full 328 MB site-packages copy (≈4.6 GB total for 14); at
runtime only `kiteconnect` (and its system-wide deps) is actually used. The
extra packages (pytest, pandas, numpy, flask, gunicorn, groq, playwright, …)
are leftovers from the build environment and are not imported by scanners.

Canonical requirements file: [`docs/requirements.txt`](requirements.txt).

### 2.4 Services and routing

| Component | Detail |
|---|---|
| API | `tradingai-api.service` — gunicorn, 2 workers × 4 threads, `127.0.0.1:8000`, Flask `app.api.app:app` |
| Reverse proxy | nginx `tradingai.in`, TLS via Let's Encrypt, Cloudflare origin lock, `/api/` → gunicorn |
| Dashboards | static files under `/opt/tradingai/frontend/live/<slug>/` |
| Process supervision | systemd, `Restart=always`, `RestartSec=5` (scanners) / `10` (API) |

---

## 3. Basic configuration (common to all scanners)

### 3.1 Market and timing

| Constant | Value | Meaning |
|---|---|---|
| `IST` | `Asia/Kolkata` | all timestamps |
| `MARKET_OPEN` | `09:15` | session open (status reporting) |
| `MARKET_CLOSE` | `15:30` | session close (status reporting) |
| `ENTRY_START` | `09:20` | first allowed entry |
| `ENTRY_END` | `15:15` | entry cutoff (exclusive) |
| `POLL_SECONDS` | `5` | decision cadence |
| `CANDLE_MINUTES` | `5` | candle size |
| `MUHURAT_SESSIONS` | date → (open, close) | special-session override |

Entry window rule:

```python
ENTRY_START <= now.time() < ENTRY_END
```

Consequences:

- The **09:15 candle is never entered**.
- The **last entry candle is 15:10** (exits at 15:15).
- Nothing opens at or after **15:15:00**.
- **Exits and trail stops are not gated** — open positions still exit normally
  after 15:15.
- The window is fixed wall-clock, so on a special session (e.g. 14:00–17:00)
  entries are still limited to 09:20–15:15.

`market_is_open()` remains 09:15–15:30 and is used only for status/IDLE
reporting, not for entry permission.

### 3.2 Contract selection

| Item | Value |
|---|---|
| Underlying | `NIFTY` |
| Timeframe | `5m` |
| ATM strike | `round(spot / 50) * 50` (50-point step) |
| Expiry | nearest NIFTY expiry ≥ today |
| Option types | CE and PE evaluated independently, both BUY-only |
| Lot size (reference) | 65 |

All logic is based on the **option premium candles/LTP**, never on the NIFTY
index price. The index is used only to select the ATM strike.

### 3.3 Credentials

| File | Purpose |
|---|---|
| `/opt/tradingai/.env.zerodha` | `ZERODHA_MODE`, `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_ACCESS_TOKEN`, `REDIRECT_URL` |
| `/opt/tradingai/zerodha_credentials.py` | loader used by token exchange and scanners |
| `/opt/tradingai/refresh_token.sh` | exchange + persist + restart + verify |
| `/opt/tradingai/premarket_token_check.sh` | read-only 08:45 validity check |

Never commit `.env.zerodha`, `zerodha_credentials.py`, or any token to git.

### 3.4 Per-scanner environment (systemd)

Every scanner unit sets:

```ini
Environment=<KEY>_DB_PATH=/opt/tradingai/database/<key>.db
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=PYTHONPATH=/opt/tradingai/<key>_lib
```

and runs:

```ini
ExecStart=/usr/bin/python3 /opt/tradingai/<key>_scanner/app/live_<key>_scanner.py
Restart=always
RestartSec=5
StandardOutput=append:/opt/tradingai/logs/live_<key>_scanner.log
```

### 3.5 Paths

| Item | Path |
|---|---|
| Code | `/opt/tradingai/<key>_scanner/` |
| Live entrypoint | `/opt/tradingai/<key>_scanner/app/live_<key>_scanner.py` |
| Strategy engine | `/opt/tradingai/<key>_scanner/app/<key>_engine.py` |
| Python libs | `/opt/tradingai/<key>_lib/` |
| Database | `/opt/tradingai/database/<key>.db` |
| Log | `/opt/tradingai/logs/live_<key>_scanner.log` |
| Pre-patch backups | `/opt/tradingai/backups/` |
| Dashboard files | `/opt/tradingai/frontend/live/<slug>/` |
| API routes | `/opt/tradingai/app/api/app.py` |

---

## 4. Scanner configuration matrix

`off` = `POLL_OFFSET_SECONDS`, the per-scanner phase offset inside the 5-second
tick. It staggers Kite quote/historical calls so the scanners do not all hit
the API at the same instant.

| Key | Strategy id | Strategy type | Ver | SMA | Trail / activate | off | User | systemd unit |
|---|---|---|---|---|---|---|---|---|
| `sma3` | `sma3_only` | `SMA3_BUY_ONLY` | 3.0.0 | 3 | — | 0 | `sma3` | `tradingai-sma3-scanner` |
| `sma9` | `sma9_only` | `SMA9_BUY_ONLY` | 2.0.0 | 9 | — | 0 | `sma9` | `tradingai-sma9-scanner` |
| `sma20` | `sma20_only` | `SMA20_BUY_ONLY` | 20.0.0 | 20 | — | 0 | `sma20` | `tradingai-sma20-scanner` |
| `sma3_high` | `sma3_high` | `SMA3_HIGH_BUY_ONLY` | 1.0.0 | 3 | — | 1.2 | `sma3high` | `tradingai-sma3-high-scanner` |
| `sma9_high` | `sma9_high` | `SMA9_HIGH_BUY_ONLY` | 1.0.0 | 9 | — | 2.4 | `sma9high` | `tradingai-sma9-high-scanner` |
| `sma20_high` | `sma20_high` | `SMA20_HIGH_BUY_ONLY` | 1.0.0 | 20 | — | 3.6 | `sma20high` | `tradingai-sma20-high-scanner` |
| `no_sma` | `no_sma` | `NO_SMA_BUY_ONLY` | 1.0.0 | — | — | 0 | `nosma` | `tradingai-no-sma-scanner` |
| `sma3_trail` | `sma3_trail` | `SMA_BUY_ONLY` | 1.0.0 | 3 | 5.0 / 5.0 | 0.6 | `sma3trail` | `tradingai-sma3_trail-scanner` |
| `sma9_trail` | `sma9_trail` | `SMA_BUY_ONLY` | 1.0.0 | 9 | 5.0 / 5.0 | 1.2 | `sma9trail` | `tradingai-sma9_trail-scanner` |
| `sma20_trail` | `sma20_trail` | `SMA_BUY_ONLY` | 1.0.0 | 20 | 5.0 / 5.0 | 1.8 | `sma20trail` | `tradingai-sma20_trail-scanner` |
| `sma3_high_trail` | `sma3_high_trail` | `SMA_HIGH_BUY_ONLY` | 1.0.0 | 3 | 5.0 / 5.0 | 2.4 | `sma3trailhigh` | `tradingai-sma3_high_trail-scanner` |
| `sma9_high_trail` | `sma9_high_trail` | `SMA_HIGH_BUY_ONLY` | 1.0.0 | 9 | 5.0 / 5.0 | 3.0 | `sma9trailhigh` | `tradingai-sma9_high_trail-scanner` |
| `sma20_high_trail` | `sma20_high_trail` | `SMA_HIGH_BUY_ONLY` | 1.0.0 | 20 | 5.0 / 5.0 | 3.6 | `sma20trailhigh` | `tradingai-sma20_high_trail-scanner` |
| `no_sma_trail` | `no_sma_trail` | `PREV_HIGH_BUY_ONLY` | 1.0.0 | — | 5.0 / 5.0 | 4.2 | `nosmatrail` | `tradingai-no_sma_trail-scanner` |

DB path is always `/opt/tradingai/database/<key>.db`.
API namespace is always `/api/<slug>/` (slug = key with `_` → `-`).
Dashboard is always `https://tradingai.in/live/<slug>/`.

---

## 5. Strategy rules in detail

Candles are 5-minute option-premium candles. `completed` = all candles except
the still-forming last one. `prev` = last completed candle. `SMA_N` = mean of
the last *N* completed closes.

### 5.1 Base SMA (`sma3`, `sma9`, `sma20`)

```
qualified    = (prev.close > SMA_N) OR (forming.open > SMA_N)
confirmation = LTP > SMA_N
signal       = qualified AND confirmation
entry        = paper BUY at round(LTP, 2)
exit         = at the close of the entry candle (SAME_CANDLE_EXIT)
```

Entry may fire on any 5-second poll while the signal holds. No stop-loss.

### 5.2 HIGH (`sma3_high`, `sma9_high`, `sma20_high`)

```
condition_a  = forming.open > SMA_N
condition_b  = LTP > prev.high
confirmation = LTP > SMA_N
signal       = condition_a AND condition_b AND confirmation
entry        = paper BUY at round(LTP, 2)
exit         = at the close of the entry candle
```

This is the strict variant: the current candle must open above the SMA, the
live premium must break the previous candle high, and it must also be above
the SMA. No stop-loss.

### 5.3 NO-SMA (`no_sma`)

```
signal = LTP > prev.high
entry  = paper BUY at round(LTP, 2)
exit   = at the close of the entry candle
```

No moving average anywhere. No stop-loss.

### 5.4 Trail (`*_trail`)

Entry is inherited unchanged from the corresponding base scanner
(`sma` / `sma_high` / `prev_high`).

Exit is evaluated before the candle-close exit, on every poll:

```
hwm  = max(hwm, LTP)
if hwm - entry >= ACTIVATE (5.0):
    stop = entry            # first activation: breakeven
    stop = max(stop, hwm - TRAIL)   # ratchet up only
if stop is not None and stop > entry and LTP <= stop:
    exit at round(LTP, 2)   # actual sampled LTP at breach
    reason = TRAIL_STOP_EXIT
else:
    exit at the close of the entry candle
```

- `TRAIL = 5.0`, `ACTIVATE = 5.0`.
- There is **no stop-loss**. A breakeven or losing stop is ignored; the trade
  runs to candle close.
- Exit price is the **actual LTP sampled at the breach**, not the idealized
  stop level (models slippage).
- `hwm` and `stop` are persisted in the open-position row, so a restart
  resumes the trail correctly.

---

## 6. Data model (SQLite)

Each database has three tables, prefixed with the scanner key:

| Table | Purpose |
|---|---|
| `<key>_trades` | closed trades (one row per paper round trip) |
| `<key>_open_positions` | live open position(s), keyed by option type (CE/PE) |
| `<key>_scan_state` | key/value runtime state |

Common `trades` columns: `trade_id`, `strategy_id`, `instrument`,
`trade_date`, `option_type`, `strike`, `expiry`, `signal_timestamp`,
`entry_timestamp`, `entry_price`, `exit_timestamp`, `exit_price`,
`exit_reason`, `pnl_points`, `status`, `candle_open/high/low/close`,
`created_at`, `updated_at`, `dataset`, `ltp_at_entry`, `entry_candle_start`,
`entry_candle_end`.

Family-specific columns:

| Family | Extra columns |
|---|---|
| Base SMA | `sma{n}_value` (`sma3_value` / `sma9_value` / `sma20_value`), `prev_close`, `condition_a`, `condition_b` |
| HIGH | `sma_value`, `prev_high`, `condition_a`, `condition_b` |
| NO-SMA | `prev_high`, `breakout` |
| Trail | `prev_high`, `breakout`, and `hwm`, `stop` in `open_positions` |

`exit_reason` is `SAME_CANDLE_EXIT` or `TRAIL_STOP_EXIT`.
`pnl_points = exit_price - entry_price` (BUY-only, one lot notional is not
applied).

Database ownership must be `<service-user>:ubuntu` with mode `664`; the
service user must be able to `BEGIN IMMEDIATE`.

---

## 7. API and dashboards

### 7.1 API

All 14 namespaces expose the same 9 read-only endpoints:

```
GET /api/<slug>/signals
GET /api/<slug>/trades
GET /api/<slug>/daily-summary
GET /api/<slug>/scanner-status
GET /api/<slug>/live-status
GET /api/<slug>/recent-trades
GET /api/<slug>/today
GET /api/<slug>/legacy-audit
GET /api/<slug>/open-positions
```

`<slug>` values: `sma3`, `sma9`, `sma20`, `sma3-high`, `sma9-high`,
`sma20-high`, `no-sma`, `sma3-trail`, `sma9-trail`, `sma20-trail`,
`sma3-high-trail`, `sma9-high-trail`, `sma20-high-trail`, `no-sma-trail`.

Quick health check:

```bash
curl -sk -H 'Host: tradingai.in' \
  https://127.0.0.1/api/sma3/scanner-status
```

### 7.2 Dashboards

| Scanner | Dashboard |
|---|---|
| sma3 | https://tradingai.in/live/sma3/ |
| sma9 | https://tradingai.in/live/sma9/ |
| sma20 | https://tradingai.in/live/sma20/ |
| sma3_high | https://tradingai.in/live/sma3-high/ |
| sma9_high | https://tradingai.in/live/sma9-high/ |
| sma20_high | https://tradingai.in/live/sma20-high/ |
| no_sma | https://tradingai.in/live/no-sma/ |
| sma3_trail | https://tradingai.in/live/sma3-trail/ |
| sma9_trail | https://tradingai.in/live/sma9-trail/ |
| sma20_trail | https://tradingai.in/live/sma20-trail/ |
| sma3_high_trail | https://tradingai.in/live/sma3-high-trail/ |
| sma9_high_trail | https://tradingai.in/live/sma9-high-trail/ |
| sma20_high_trail | https://tradingai.in/live/sma20-high-trail/ |
| no_sma_trail | https://tradingai.in/live/no-sma-trail/ |

The trail dashboards are also reachable from the **TRAIL** button on
`https://tradingai.in/live/scalp/`.

---

## 8. Operations runbook

### 8.1 Daily pre-open

```bash
# 1. Token validity (read-only)
cat /opt/tradingai/logs/token_status.txt
systemctl list-timers tradingai-token-check.timer

# 2. If TOKEN_INVALID, refresh before 09:15
sudo /opt/tradingai/refresh_token.sh <REQUEST_TOKEN>

# 3. All 14 scanners + API active
systemctl is-active tradingai-api \
  tradingai-sma3-scanner tradingai-sma9-scanner tradingai-sma20-scanner \
  tradingai-sma3-high-scanner tradingai-sma9-high-scanner \
  tradingai-sma20-high-scanner tradingai-no-sma-scanner \
  tradingai-sma3_trail-scanner tradingai-sma9_trail-scanner \
  tradingai-sma20_trail-scanner tradingai-sma3_high_trail-scanner \
  tradingai-sma9_high_trail-scanner tradingai-sma20_high_trail-scanner \
  tradingai-no_sma_trail-scanner

# 4. Instrument load completed ("ready" in each log)
for f in /opt/tradingai/logs/live_*scanner.log; do
  printf '%-40s %s\n' "$(basename "$f")" "$(grep 'ready$' "$f" | tail -1)"
done
```

### 8.2 Restart

Restart scanners in staggered waves (3 s apart) so 14 instrument downloads do
not hit Kite at once:

```bash
for u in tradingai-sma3-scanner tradingai-sma9-scanner \
         tradingai-sma20-scanner tradingai-sma3-high-scanner \
         tradingai-sma9-high-scanner tradingai-sma20-high-scanner \
         tradingai-no-sma-scanner tradingai-sma3_trail-scanner \
         tradingai-sma9_trail-scanner tradingai-sma20_trail-scanner \
         tradingai-sma3_high_trail-scanner tradingai-sma9_high_trail-scanner \
         tradingai-sma20_high_trail-scanner tradingai-no_sma_trail-scanner; do
  sudo systemctl restart "$u"
  sleep 3
done
```

### 8.3 Health checks

```bash
# service state / restart count
systemctl show tradingai-sma3-scanner -p ActiveState -p NRestarts

# errors (auth, rate limit, DB, TLS, tracebacks)
sudo journalctl --since '09:15' --no-pager \
  | grep -iE 'Incorrect api_key|Too many requests|readonly database|SSLEOF|Traceback'

# all 14 APIs return 200
for k in sma3 sma9 sma20 sma3-high sma9-high sma20-high no-sma \
         sma3-trail sma9-trail sma20-trail sma3-high-trail \
         sma9-high-trail sma20-high-trail no-sma-trail; do
  printf '%s=%s ' "$k" "$(curl -sk -o /dev/null -w '%{http_code}' \
    -H 'Host: tradingai.in' "https://127.0.0.1/api/$k/scanner-status")"
done; echo

# DB writability as the service user
sudo runuser -u sma3 -g ubuntu -- python3 -c \
  'import sqlite3;c=sqlite3.connect("/opt/tradingai/database/sma3.db");c.execute("BEGIN IMMEDIATE");c.rollback();print("OK")'
```

### 8.4 Log rotation

Logrotate uses `copytruncate`; the copied file must be readable by the
rotating user. Files are `root:ubuntu 660`, and the logrotate stanza includes
`su ubuntu ubuntu`. After changing log ownership run:

```bash
sudo chown root:ubuntu /opt/tradingai/logs/*.log
```

### 8.5 Code locks (base scanners only)

The seven base scanners are protected: `root:root`, mode `444`, `chattr +i`,
with a SHA256 manifest and a 15-minute integrity timer.

```bash
# verify
sudo /opt/tradingai/sma3_scanner/ops/verify_integrity.sh

# approved change cycle
sudo /opt/tradingai/sma3_scanner/ops/unlock_code.sh
# edit + test
sudo /opt/tradingai/sma3_scanner/ops/lock_code.sh   # rebuilds manifest + relocks
sudo systemctl restart tradingai-sma3-scanner
```

The seven trail scanners are **not** locked (normal `user:ubuntu 644` files);
edit and restart normally.

### 8.6 Rate-limit hygiene

- Base plain scanners (`sma3`, `sma9`, `sma20`, `no_sma`): **2 quote calls per
  tick** — one spot-only refresh for ATM selection, plus one batched
  spot+CE+PE quote. Offset 0.
- Base HIGH scanners: same **2-call** pattern, offsets 1.2 / 2.4 / 3.6 s.
- Trail scanners: **1 batched spot+CE+PE quote per tick** (extra calls only on
  a failed batch or a newly missing contract), offsets 0.6–4.2 s.
- Historical candles are fetched only when a new 5-minute candle appears (or
  at exit), never on every poll.
- Kite limits: quotes ≈1 req/s, historical ≈3 req/s per API key.
- If `Too many requests` appears in logs, check for overlapping restarts or a
  runaway historical fetch before changing offsets.

---

## 9. Safety guarantees

- **Paper only.** No broker order path exists. Verify with:

  ```bash
  sudo grep -rn 'place_order\|order_id' /opt/tradingai/*_scanner/app/ \
    && echo 'FOUND — investigate' || echo 'clean: no broker orders'
  ```

- **BUY only.** CE and PE are long-only; there is no short/sell-to-open path.
- **No stop-loss** in any variant; risk is bounded by the candle-close exit or
  the profitable trailing stop.
- **Secrets** live only in `/opt/tradingai/.env.zerodha` and the local git
  config; they are never committed.
- **State survives restarts** via `open_positions` and `scan_state`, including
  trail `hwm`/`stop`.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Incorrect api_key or access_token`, zero trades | daily token expired | `sudo /opt/tradingai/refresh_token.sh <REQUEST_TOKEN>` |
| `Too many requests` | quote/historical burst, overlapping restarts | stagger restarts; check offsets; wait for the 1 s / 3 s window |
| `attempt to write a readonly database` | DB ownership/mode after redeploy | `chown <user>:ubuntu <db> && chmod 664 <db>` |
| `SSLEOFError` / `UNEXPECTED_EOF_WHILE_READING` during startup | transient Kite TLS reset | self-heals via `Restart=always` (~5 s); no action unless repeated |
| Service active but no entries | outside 09:20–15:15, no signal, or market closed | check `scanner-status`, `live-status`, and log reason strings |
| API 502/503 | gunicorn down or restarting | `systemctl status tradingai-api`, `journalctl -u tradingai-api` |
| Dashboard blank / iframe blocked | missing `X-Frame-Options: SAMEORIGIN` | check nginx security-headers snippet |
| Integrity timer failing | code changed without relock | `unlock_code.sh` → change → `lock_code.sh` |

---

## 11. Source sync and GitHub

| Item | Location |
|---|---|
| GitHub repo | `trail_build/out` (branches: `main` + 7 trail branches) |
| Trail branches | `sma3-trail`, `sma9-trail`, `sma20-trail`, `sma3-high-trail`, `sma9-high-trail`, `sma20-high-trail`, `no-sma-trail` |
| Local base sources | `/Users/satya/sma9_work/high_build/` (+ `out_nosma/`, `sma3_scanner/`) |
| Local trail sources | `/Users/satya/sma9_work/trail_build/out/<key>_scanner/app/` |
| Trail template | `/Users/satya/sma9_work/trail_build/build_trail.py` (keeps the 09:20–15:15 window) |
| Base HIGH/NO-SMA builders | `high_build/build_high.py`, `high_build/build_nosma.py` |
| Local mirror of this doc | `/Users/satya/sma9_work/docs_build/` |

The base seven scanners do not have their own GitHub branches; their sources
are kept in sync locally and on the VM. The entry-window change is present in
all 14 deployed files and in the trail build template.

---

## 12. Document map

| Document | Covers |
|---|---|
| `SCANNERS.md` (this file) | everything: requirements, dependencies, common config, matrix, operations |
| `docs/requirements.txt` | canonical Python requirements |
| `docs/scanners/<key>.md` | per-scanner entry/exit rules, constants, runtime, commands |
| `/opt/tradingai/TOKEN_REFRESH.md` | daily Kite token runbook |
| `<key>_scanner/docs/SECURITY_AND_OPERATIONS.md` | base-scanner lock policy (base 7 only) |
