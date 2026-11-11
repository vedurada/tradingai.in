#!/usr/bin/env python3
"""Verify SMA3 HIGH Trail trail dashboard API endpoints."""
import sys
import urllib.request
import json

BASE = "https://tradingai.in"
ENDPOINTS = [
    f"/api/sma3-high-trail/scanner-status",
    f"/api/sma3-high-trail/today",
]

errors = []
for ep in ENDPOINTS:
    try:
        with urllib.request.urlopen(BASE + ep, timeout=15) as r:
            data = json.loads(r.read())
            if not data.get("success"):
                errors.append(f"{ep}: success=False")
    except Exception as e:
        errors.append(f"{ep}: {e}")

if errors:
    print("FAIL:");
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print("All SMA3 HIGH Trail trail dashboard endpoints OK")
