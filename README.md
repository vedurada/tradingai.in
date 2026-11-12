# TradingAI Trail Scanners

## Overview

This repository contains **7 independent trailing-stop paper trading scanners**
for ATM NIFTY CE/PE options. Each scanner is a complete, self-contained copy
with its own code, database, service user, systemd unit, API namespace, and
dashboard.

Entries are **consumed from the corresponding base scanner's live open
position** (same contract, price and entry candle) through the local base
status API. A trail scanner owns only the exit.

## Trail Exit Rule (all scanners)

- Stop is **inactive** until the option trades **+5 points** above entry
- At activation, stop is set at **entry price** (breakeven)
- Thereafter, stop = `high_water_mark - 5`, ratcheting up only
- **One-time breakeven lock:** once profit reaches **+6 points**, the stop is
  set to `entry + 2` exactly once; the normal trail then continues ratcheting
  from the locked stop
- **Exit at stop only if stop is above entry price** (profitable lock)
- Breakeven or loss stops are **ignored** — trade runs to candle close
- Otherwise, exit at the entry 5-minute candle close

## Scanners

| Branch | Scanner | Entry Rule | User | Database | API Namespace | Dashboard |
|--------|---------|-----------|------|----------|---------------|-----------|
| `sma3-trail` | SMA3 Trail | consumes base `sma3` position | sma3trail | sma3_trail.db | /api/sma3-trail/ | /live/sma3-trail/ |
| `sma9-trail` | SMA9 Trail | consumes base `sma9` position | sma9trail | sma9_trail.db | /api/sma9-trail/ | /live/sma9-trail/ |
| `sma20-trail` | SMA20 Trail | consumes base `sma20` position | sma20trail | sma20_trail.db | /api/sma20-trail/ | /live/sma20-trail/ |
| `sma3-high-trail` | SMA3 HIGH Trail | consumes base `sma3_high` position | sma3trailhigh | sma3_high_trail.db | /api/sma3-high-trail/ | /live/sma3-high-trail/ |
| `sma9-high-trail` | SMA9 HIGH Trail | consumes base `sma9_high` position | sma9trailhigh | sma9_high_trail.db | /api/sma9-high-trail/ | /live/sma9-high-trail/ |
| `sma20-high-trail` | SMA20 HIGH Trail | consumes base `sma20_high` position | sma20trailhigh | sma20_high_trail.db | /api/sma20-high-trail/ | /live/sma20-high-trail/ |
| `no-sma-trail` | NO-SMA Trail | consumes base `no_sma` position | nosmatrail | no_sma_trail.db | /api/no-sma-trail/ | /live/no-sma-trail/ |

## Shared Files

- `trail_api_blocks.py` — Flask API route blocks for all 7 scanners
- `trail_nginx_redirects.conf` — Nginx redirect rules for /live/*-trail URLs
- `.gitignore` — Excludes secrets, databases, and runtime state

## Per-Scanner Branch

Each branch contains a complete scanner tree:

```
<scanner>/
├── app/
│   ├── __init__.py
│   ├── live_<scanner>_scanner.py
│   ├── <scanner>_engine.py
│   └── <scanner>_db_setup.py
├── ops/
│   ├── tradingai-<scanner>-scanner.service
│   ├── lock_code.sh
│   ├── unlock_code.sh
│   ├── status.sh
│   ├── install_integrity_timer.sh
│   ├── verify_integrity.sh
│   ├── verify_system.py
│   └── verify_dashboard.py
├── tests/
│   └── test_<scanner>_engine.py
├── docs/
│   └── SECURITY_AND_OPERATIONS.md
├── MANIFEST.sha256
├── VERSION
└── README.md
```

## Read-Only Guarantee

All scanners are **paper trading only**. No `place_order` or `order_id`
references exist. They never place real broker orders.

## Live Deployment

Scanners are deployed at `/opt/tradingai/` on the production server and run
as systemd services. Dashboards are served at `https://tradingai.in/live/*-trail/`.

## Simulated Historical Performance

Based on 252 recorded LIVE trades (Nov 6–9, 2026) replayed against actual
1-minute Kite candles:

| Scanner | Actual (pts) | Trailing 5 (pts) | Δ (pts) |
|---------|-------------|------------------|---------|
| SMA3 | −185.90 | **+251.35** | +437.25 |
| SMA9 | +36.45 | **+236.55** | +200.10 |
| SMA20 | −81.75 | **+89.00** | +170.75 |
| SMA3 HIGH | +13.45 | **+114.25** | +100.80 |
| SMA9 HIGH | +2.65 | **+83.15** | +80.50 |
| SMA20 HIGH | −10.70 | **+76.45** | +87.15 |
| NO-SMA | −38.25 | **+49.80** | +88.05 |
| **ALL** | **−264.05** | **+900.55** | **+1,164.60** |
