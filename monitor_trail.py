#!/usr/bin/env python3
"""Monitor all 7 trail scanners during live market hours.

Checks each scanner's /scanner-status API and logs key metrics.
Run this during market hours to track performance.
"""

import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
BASE = "https://tradingai.in"

SCANNERS = [
    ("sma3-trail", "SMA3 Trail"),
    ("sma9-trail", "SMA9 Trail"),
    ("sma20-trail", "SMA20 Trail"),
    ("sma3-high-trail", "SMA3 HIGH Trail"),
    ("sma9-high-trail", "SMA9 HIGH Trail"),
    ("sma20-high-trail", "SMA20 HIGH Trail"),
    ("no-sma-trail", "NO-SMA Trail"),
]


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"success": False, "error": str(e)}


def monitor():
    now = datetime.now(IST)
    print(f"\n{'='*70}")
    print(f"Trail Scanner Monitor — {now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"{'='*70}")

    total_trades = 0
    total_pnl = 0.0
    active_count = 0

    for urlkey, label in SCANNERS:
        data = fetch(f"{BASE}/api/{urlkey}/scanner-status")
        if not data.get("success"):
            print(f"\n{label:20s} | ERROR: {data.get('error', 'unknown')}")
            continue

        status = data.get("status", "UNKNOWN")
        trades = data.get("total_trades", 0)
        pnl = data.get("total_pnl", 0)
        today = data.get("today", {})
        today_pnl = today.get("pnl_points", 0) if today else 0
        today_trades = today.get("count", 0) if today else 0
        wins = data.get("wins", 0)
        losses = data.get("losses", 0)
        win_rate = data.get("win_rate", 0)
        spot = data.get("spot")
        atm = data.get("atm_strike")
        errors = data.get("errors", [])
        last_scan = data.get("last_scan_at", "")
        last_scan_age = data.get("last_scan_age_seconds")

        total_trades += trades
        total_pnl += pnl
        if status == "ACTIVE":
            active_count += 1

        # Position info
        options = data.get("options", {})
        pos_info = ""
        for opt in ("CE", "PE"):
            pos = options.get(opt, {}).get("position")
            if pos:
                hwm = pos.get("hwm", 0)
                stop = pos.get("stop", 0)
                entry = pos.get("entry_price", 0)
                pos_info += f" {opt}:entry={entry} hwm={hwm} stop={stop} "

        status_emoji = "●" if status == "ACTIVE" else ("○" if status == "STOPPED" else "○")
        print(f"\n{label:20s} | {status_emoji} {status:12s} | trades={trades:3d} | pnl={pnl:8.2f} | today={today_pnl:8.2f} ({today_trades}) | W/L={wins}/{losses} | WR={win_rate:5.1f}% | spot={spot} ATM={atm}")
        if pos_info:
            print(f"{'':20s}   positions:{pos_info}")
        if errors:
            print(f"{'':20s}   errors: {errors[:2]}")
        if last_scan_age is not None and last_scan_age > 15:
            print(f"{'':20s}   WARNING: last scan {last_scan_age:.0f}s ago")

    print(f"\n{'='*70}")
    print(f"TOTAL: active={active_count}/7 | trades={total_trades} | pnl={total_pnl:8.2f} pts | ₹/lot={round(total_pnl*65)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    monitor()
