#!/usr/bin/env python3
"""Database setup for SMA9 Trail trail scanner."""

import os
import sqlite3

BASE = "/opt/tradingai"
DB_PATH = os.environ.get("SMA9_TRAIL_DB_PATH", os.path.join(BASE, "database", "sma9_trail.db"))


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sma9_trail_trades (
            trade_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL DEFAULT 'sma9_trail',
            instrument TEXT NOT NULL DEFAULT 'NIFTY',
            trade_date TEXT NOT NULL,
            option_type TEXT NOT NULL CHECK(option_type IN ('CE','PE')),
            strike REAL NOT NULL,
            expiry TEXT NOT NULL,
            signal_timestamp TEXT NOT NULL,
            entry_timestamp TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_timestamp TEXT NOT NULL,
            exit_price REAL NOT NULL,
            exit_reason TEXT NOT NULL DEFAULT 'SAME_CANDLE_EXIT',
            pnl_points REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'CLOSED',
            candle_open REAL,
            candle_high REAL,
            candle_low REAL,
            candle_close REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            dataset TEXT NOT NULL DEFAULT 'LIVE',
            prev_high REAL,
            breakout INTEGER,
            ltp_at_entry REAL,
            entry_candle_start TEXT,
            entry_candle_end TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sma9_trail_trades_date ON sma9_trail_trades(trade_date);
        CREATE INDEX IF NOT EXISTS idx_sma9_trail_trades_option ON sma9_trail_trades(option_type);
        CREATE INDEX IF NOT EXISTS idx_sma9_trail_trades_status ON sma9_trail_trades(status);
        CREATE INDEX IF NOT EXISTS idx_sma9_trail_trades_dataset ON sma9_trail_trades(dataset);

        CREATE TABLE IF NOT EXISTS sma9_trail_open_positions (
            option_type TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL,
            strike REAL NOT NULL,
            expiry TEXT NOT NULL,
            token INTEGER,
            tradingsymbol TEXT,
            entry_timestamp TEXT NOT NULL,
            entry_candle_start TEXT NOT NULL,
            entry_candle_end TEXT NOT NULL,
            entry_price REAL NOT NULL,
            prev_high REAL,
            current_open REAL,
            breakout INTEGER,
            ltp_at_entry REAL,
            hwm REAL,
            stop REAL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sma9_trail_scan_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sma9_trail_consumed_base_trades (
            base_trade_id TEXT PRIMARY KEY,
            option_type TEXT NOT NULL,
            consumed_at TEXT NOT NULL
        );
        """
    )
    # Idempotent migration: add be_locked to open_positions for existing DBs.
    try:
        cols = [r[1] for r in conn.execute(
            f"PRAGMA table_info(sma9_trail_open_positions)").fetchall()]
        if "be_locked" not in cols:
            conn.execute(
                f"ALTER TABLE sma9_trail_open_positions "
                "ADD COLUMN be_locked INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("sma9_trail database initialized at sma9_trail.db")
