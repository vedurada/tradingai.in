#!/usr/bin/env python3
"""Verify NO-SMA Trail trail scanner system."""
import json
import os
import sqlite3
import sys

BASE = "/opt/tradingai"
DB_PATH = os.environ.get("NO_SMA_TRAIL_DB_PATH", os.path.join(BASE, "database", "no_sma_trail.db"))

checks = []

def check(name, cond, detail=""):
    checks.append({"name": name, "pass": bool(cond), "detail": detail})

# DB exists
check("database_exists", os.path.exists(DB_PATH), DB_PATH)

# DB readable and has tables
try:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    conn.close()
    check("database_tables", len(tables) >= 3, str(tables))
except Exception as e:
    check("database_tables", False, str(e))

# Service active
import subprocess
try:
    out = subprocess.check_output(["systemctl", "is-active", "tradingai-no_sma_trail-scanner"], stderr=subprocess.STDOUT, text=True)
    check("service_active", "active" in out, out.strip())
except Exception as e:
    check("service_active", False, str(e))

passed = sum(1 for c in checks if c["pass"])
print(json.dumps({"overall_pass": passed == len(checks), "checks": checks}, indent=2))
sys.exit(0 if passed == len(checks) else 1)
