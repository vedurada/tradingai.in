# SMA20 Trail Trail Scanner

## Overview

SMA20 Trail Trail is a BUY-only paper trading scanner for ATM NIFTY CE/PE options
that uses a **SMA20 qualified (prev close > SMA20 OR current open > SMA20) AND LTP > SMA20 entry rule** combined with a **5-point trailing stop exit**.

## Entry Logic



## Exit Logic (Trailing Stop)

- Stop is **inactive** until the option trades **+5 points** above entry
- At activation, stop is set at **entry price** (breakeven)
- Thereafter, stop = `high_water_mark - 5`, ratcheting up only
- **Exit at stop only if stop is above entry price** (profitable lock)
- Breakeven or loss stops are **ignored** — trade runs to candle close
- Otherwise, exit at the entry 5-minute candle close

## Strategy Parameters

| Parameter | Value |
|-----------|-------|
| Trade ID Prefix | S20T- |
| Service User | sma20trail |
| Database | sma20_trail.db |
| Systemd Service | tradingai-sma20-trail-scanner |
| API Namespace | /api/sma20-trail/ |
| Dashboard | https://tradingai.in/live/sma20-trail/ |
| Poll Interval | 5 seconds |
| Timeframe | 5-minute candles |
| Lot Size | 65 |
| Strategy ID | sma20_trail_scanner |
| Version | 1.0.0 |

## File Structure

```
sma20_trail_scanner/
├── app/
│   ├── __init__.py
│   ├── live_sma20_trail_scanner_scanner.py
│   ├── sma20_trail_scanner_engine.py
│   └── sma20_trail_scanner_db_setup.py
├── ops/
│   ├── tradingai-sma20_trail_scanner-scanner.service
│   ├── lock_code.sh
│   ├── unlock_code.sh
│   ├── status.sh
│   ├── install_integrity_timer.sh
│   ├── verify_integrity.sh
│   ├── verify_system.py
│   └── verify_dashboard.py
├── tests/
│   └── test_sma20_trail_scanner_engine.py
├── docs/
│   └── SECURITY_AND_OPERATIONS.md
├── MANIFEST.sha256
├── VERSION
└── README.md
```

## API Endpoints

All endpoints under `/api/sma20-trail/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| /signals | GET | Paginated trade signals |
| /trades | GET | Alias for signals |
| /daily-summary | GET | Daily P&L summary |
| /scanner-status | GET | Scanner health + live evaluation |
| /live-status | GET | Raw scanner heartbeat (5s refresh) |
| /recent-trades | GET | Recent trades |
| /today | GET | Today's LIVE paper trades |
| /legacy-audit | GET | Legacy audit stub |
| /open-positions | GET | Open positions |

## Deployment

```bash
# Install service
sudo cp ops/tradingai-sma20_trail_scanner-scanner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tradingai-sma20_trail_scanner-scanner

# Lock code (production)
sudo bash ops/lock_code.sh

# Verify
python3 ops/verify_system.py
python3 ops/verify_dashboard.py
```

## Read-Only Guarantee

This scanner is **paper trading only**. No `place_order` or `order_id`
references exist in the code. It never places real broker orders.

## Exit Reasons

- `SAME_CANDLE_EXIT` — Exit at entry candle close (fallback)
- `TRAIL_STOP_EXIT` — Exit at trailing stop (profitable lock only)
- `SAME_CANDLE_EXIT_LTP_FALLBACK` — Exit candle unavailable, used LTP
