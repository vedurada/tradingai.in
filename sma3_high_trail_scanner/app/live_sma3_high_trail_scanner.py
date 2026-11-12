#!/usr/bin/env python3
"""SMA3 HIGH Trail live paper scanner - BUY ONLY with trailing-stop exit.

Entry: consumed from the base sma3_high scanner's live open position.
       The base scanner owns entry selection; this scanner copies the base
       trade (contract, price, timestamp, entry candle) exactly once and
       only owns the exit.
Exit: TRAILING STOP -- stop = peak - 5.0 pts, activates at +5.0 pts
      (breakeven at activation), ratchets up only.  Exit at the stop ONLY if
      the stop is above entry price (profitable lock).  Breakeven or loss
      stops are ignored -- the trade runs to candle close.
      Otherwise exit at the CLOSE of the entry 5-minute candle.

Polling is staggered by a small offset so scanners do not all request
historical candles on the same instant.

State is persisted in the dedicated database so a restart with an open
position resumes correctly.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sqlite3
import ssl
import sys
import time
import traceback
import urllib.request
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

BASE = "/opt/tradingai"
CODE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from app.sma3_high_trail_engine import (  # noqa: E402
    CANDLE_MINUTES,
    STRATEGY_ID,
    STRATEGY_TYPE,
    STRATEGY_VERSION,
    Evaluation,
    OptionStateMachine,
    Position,
    TRAIL,
    ACTIVATE,
    candle_end,
    evaluate_option,
    make_trade_id,
    normalize_candles,
)

IST = ZoneInfo("Asia/Kolkata")
DB_PATH = os.environ.get("SMA3_HIGH_TRAIL_DB_PATH", os.path.join(BASE, "database", "sma3_high_trail.db"))
LOG_PATH = os.path.join(BASE, "logs", "live_sma3_high_trail_scanner.log")

# Entry signals come from the base scanner's own live-status API.  Reading the
# base SQLite file directly is not possible for the trail service users because
# the WAL mode database rejects read-only opens from a different user.
BASE_STATUS_URL = "https://127.0.0.1/api/sma3-high/scanner-status"
BASE_STATUS_HOST = "tradingai.in"
BASE_STATUS_TIMEOUT = 3.0

MARKET_OPEN = dtime(9, 15)
MARKET_CLOSE = dtime(15, 30)
# New paper entries are allowed only inside this window (exits are not
# affected).  The 09:15 candle is never entered and the last entry candle is
# 15:10, so nothing is opened at or after 15:15.
ENTRY_START = dtime(9, 20)
ENTRY_END = dtime(15, 15)
MUHURAT_SESSIONS = {
    "2026-11-08": (dtime(14, 0), dtime(17, 0)),
}


def session_open_time(dt):
    return MUHURAT_SESSIONS.get(dt.date().isoformat(), (MARKET_OPEN, MARKET_CLOSE))[0]


def session_close_time(dt):
    return MUHURAT_SESSIONS.get(dt.date().isoformat(), (MARKET_OPEN, MARKET_CLOSE))[1]


POLL_SECONDS = 5
# Per-scanner phase offset (seconds) inside the 5s tick window.  Without this
# every scanner re-aligns to the same wall-clock boundary and they all hit the
# Kite historical/quote endpoints at the same instant, which triggers
# "Too many requests".  Each variant gets a distinct offset from VARIANTS.
POLL_OFFSET_SECONDS = 2.4
# Historical lookback: 1 day is enough on normal days (previous session is
# included).  If fewer than CANDLE_MIN_ROWS rows come back (e.g. Monday, when
# 1 day back is Sunday) widen once to the fallback window so SMA20 still has
# enough completed candles.  This keeps payloads small without changing logic.
CANDLE_LOOKBACK_DAYS = 1
CANDLE_LOOKBACK_DAYS_FALLBACK = 3
CANDLE_MIN_ROWS = 25
# Boundary re-fetch backoff.  A small random jitter de-synchronises the
# scanners that are waiting for the exchange to publish the new candle.
CANDLE_BACKOFF_BASE = 8
CANDLE_BACKOFF_JITTER = 4
CANDLE_BACKOFF_MAX = 90
INSTRUMENT = "NIFTY"
TIMEFRAME = "5m"
SCANNER_NAME = "SMA3 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY)"
STRATEGY_ID = STRATEGY_ID
STRATEGY_VERSION = STRATEGY_VERSION
STRATEGY_TYPE = STRATEGY_TYPE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def now_ist():
    return datetime.now(IST)


def floor_5m(dt):
    return dt.replace(minute=(dt.minute // CANDLE_MINUTES) * CANDLE_MINUTES,
                      second=0, microsecond=0)


def is_weekday(dt):
    if dt.date().isoformat() in MUHURAT_SESSIONS:
        return True
    return dt.weekday() < 5


def market_is_open(dt):
    if not is_weekday(dt):
        return False
    return session_open_time(dt) <= dt.time() < session_close_time(dt)


def entry_window_is_open(dt):
    """True only inside the 09:20:00-15:14:59 entry window.

    The session is 09:15-15:30, but new paper entries are allowed only from
    09:20 (so the 09:15 candle is never entered) and are blocked at 15:15
    (last entry candle is 15:10).  Exits are not affected.
    """
    if not market_is_open(dt):
        return False
    return ENTRY_START <= dt.time() < ENTRY_END


def market_close_dt(dt):
    return datetime.combine(dt.date(), session_close_time(dt), tzinfo=IST)


def sleep_to_next_tick():
    """Sleep until the next 5s tick for THIS scanner.

    Ticks are aligned to ``POLL_OFFSET_SECONDS + k*POLL_SECONDS`` so the 7
    trail scanners fire at different instants instead of all together.
    """
    now = now_ist()
    epoch = now.timestamp()
    target = (
        (int(epoch - POLL_OFFSET_SECONDS) // POLL_SECONDS) + 1
    ) * POLL_SECONDS + POLL_OFFSET_SECONDS
    time.sleep(max(0.2, target - epoch))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
TRADE_COLUMNS = (
    "trade_id, strategy_id, instrument, trade_date, option_type, strike, "
    "expiry, signal_timestamp, entry_timestamp, entry_price, exit_timestamp, "
    "exit_price, exit_reason, pnl_points, status, candle_open, "
    "candle_high, candle_low, candle_close, created_at, updated_at, dataset, "
    "prev_high, breakout, ltp_at_entry, entry_candle_start, "
    "entry_candle_end"
)


def db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = db_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sma3_high_trail_trades (
            trade_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL DEFAULT 'sma3_high_trail',
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
        CREATE INDEX IF NOT EXISTS idx_sma3_high_trail_trades_date ON sma3_high_trail_trades(trade_date);
        CREATE INDEX IF NOT EXISTS idx_sma3_high_trail_trades_option ON sma3_high_trail_trades(option_type);
        CREATE INDEX IF NOT EXISTS idx_sma3_high_trail_trades_status ON sma3_high_trail_trades(status);
        CREATE INDEX IF NOT EXISTS idx_sma3_high_trail_trades_dataset ON sma3_high_trail_trades(dataset);

        CREATE TABLE IF NOT EXISTS sma3_high_trail_open_positions (
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

        CREATE TABLE IF NOT EXISTS sma3_high_trail_scan_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sma3_high_trail_consumed_base_trades (
            base_trade_id TEXT PRIMARY KEY,
            option_type TEXT NOT NULL,
            consumed_at TEXT NOT NULL
        );
        """
    )
    # Idempotent migration: add be_locked to open_positions for existing DBs.
    try:
        cols = [r[1] for r in conn.execute(
            f"PRAGMA table_info(sma3_high_trail_open_positions)").fetchall()]
        if "be_locked" not in cols:
            conn.execute(
                f"ALTER TABLE sma3_high_trail_open_positions "
                "ADD COLUMN be_locked INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def save_trade(trade):
    cols = TRADE_COLUMNS.split(",")
    cols = [c.strip() for c in cols]
    placeholders = ",".join("?" for _ in cols)
    conn = db_conn()
    try:
        conn.execute(
            f"INSERT OR REPLACE INTO sma3_high_trail_trades ({','.join(cols)}) VALUES ({placeholders})",
            tuple(trade.get(c) for c in cols),
        )
        conn.commit()
    finally:
        conn.close()


def save_open_position(pos):
    conn = db_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO sma3_high_trail_open_positions
               (option_type, trade_id, strike, expiry, token, tradingsymbol,
                entry_timestamp, entry_candle_start, entry_candle_end,
                entry_price, prev_high, current_open, breakout, ltp_at_entry,
                hwm, stop, be_locked, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pos.option_type, pos.trade_id, pos.strike, pos.expiry, pos.token,
                pos.tradingsymbol, pos.entry_timestamp.isoformat(),
                pos.entry_candle_start.isoformat(), pos.entry_candle_end.isoformat(),
                pos.entry_price, pos.prev_high, pos.current_open,
                1 if pos.breakout else 0, pos.ltp_at_entry,
                pos.hwm, pos.stop, 1 if pos.be_locked else 0,
                now_ist().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_open_position(option_type):
    conn = db_conn()
    try:
        conn.execute("DELETE FROM sma3_high_trail_open_positions WHERE option_type = ?",
                     (option_type,))
        conn.commit()
    finally:
        conn.close()


def load_open_positions():
    conn = db_conn()
    try:
        rows = conn.execute(f"SELECT * FROM sma3_high_trail_open_positions").fetchall()
    finally:
        conn.close()
    result = {}
    for r in rows:
        d = dict(r)
        result[d["option_type"]] = Position(
            option_type=d["option_type"],
            trade_id=d["trade_id"],
            strike=d["strike"],
            expiry=d["expiry"],
            token=d["token"],
            tradingsymbol=d["tradingsymbol"],
            entry_timestamp=datetime.fromisoformat(d["entry_timestamp"]),
            entry_candle_start=datetime.fromisoformat(d["entry_candle_start"]),
            entry_candle_end=datetime.fromisoformat(d["entry_candle_end"]),
            entry_price=d["entry_price"],
            prev_high=d["prev_high"],
            current_open=d["current_open"],
            breakout=bool(d["breakout"]),
            ltp_at_entry=d["ltp_at_entry"],
            hwm=d["hwm"],
            stop=d["stop"],
            be_locked=bool(d["be_locked"]),
        )
    return result


def base_trade_consumed(base_trade_id):
    conn = db_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM sma3_high_trail_consumed_base_trades WHERE base_trade_id = ?",
            (base_trade_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_base_trade_consumed(base_trade_id, option_type):
    conn = db_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sma3_high_trail_consumed_base_trades "
            "(base_trade_id, option_type, consumed_at) VALUES (?,?,?)",
            (base_trade_id, option_type, now_ist().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def prune_consumed_base_trades(days=3):
    cutoff = (now_ist() - timedelta(days=days)).isoformat()
    conn = db_conn()
    try:
        conn.execute(
            "DELETE FROM sma3_high_trail_consumed_base_trades WHERE consumed_at < ?",
            (cutoff,),
        )
        conn.commit()
    finally:
        conn.close()


def save_scan_state(state):
    conn = db_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO sma3_high_trail_scan_state (key, value, updated_at) VALUES (?,?,?)",
            ("live_status", json.dumps(state, default=str), now_ist().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def today_stats(today):
    conn = db_conn()
    try:
        row = conn.execute(
            f"""SELECT COUNT(*) n, COALESCE(SUM(pnl_points),0) pnl,
                      COALESCE(SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END),0) wins,
                      COALESCE(SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END),0) losses
               FROM sma3_high_trail_trades WHERE dataset='LIVE' AND trade_date=?""",
            (today,),
        ).fetchone()
    finally:
        conn.close()
    return {
        "trades": row["n"],
        "pnl_points": round(row["pnl"], 2),
        "wins": row["wins"],
        "losses": row["losses"],
    }


# ---------------------------------------------------------------------------
# Base-scanner signal feed
# ---------------------------------------------------------------------------
class BaseSignalFeed:
    """Read the base scanner's live status through the local nginx API."""

    def __init__(self):
        self._ssl = ssl.create_default_context()
        self._ssl.check_hostname = False
        self._ssl.verify_mode = ssl.CERT_NONE
        self.last_error = None

    def fetch(self):
        req = urllib.request.Request(
            BASE_STATUS_URL, headers={"Host": BASE_STATUS_HOST})
        with urllib.request.urlopen(
                req, context=self._ssl, timeout=BASE_STATUS_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data.get("success"):
            raise RuntimeError(data.get("error") or "base status success=False")
        self.last_error = None
        return data


# ---------------------------------------------------------------------------
# Zerodha data feed
# ---------------------------------------------------------------------------
class KiteFeed:
    def __init__(self):
        from kiteconnect import KiteConnect

        creds = self._load_zerodha_credentials()
        self.kite = KiteConnect(api_key=creds["KITE_API_KEY"])
        self.kite.set_access_token(creds["KITE_ACCESS_TOKEN"])
        self._instruments = []
        self._instruments_date = None
        self._candles = {}

    def _load_zerodha_credentials(self):
        env_path = os.path.join(BASE, ".env.zerodha")
        creds = {}
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    creds[k.strip()] = v.strip()
        return creds

    def refresh_instruments(self):
        today = now_ist().date()
        if self._instruments_date == today and self._instruments:
            return
        instruments = self.kite.instruments("NFO")
        self._instruments = [
            i for i in instruments
            if i.get("name") == "NIFTY"
            and i.get("instrument_type") in ("CE", "PE")
            and i.get("segment") == "NFO-OPT"
        ]
        self._instruments_date = today
        logger.info("Loaded %d NIFTY option instruments", len(self._instruments))

    def nearest_expiry(self):
        self.refresh_instruments()
        today = now_ist().date()
        expiries = sorted({i["expiry"] for i in self._instruments
                           if i["expiry"] >= today})
        if not expiries:
            raise RuntimeError("No NIFTY option expiry available")
        return expiries[0]

    def find_contract(self, strike, expiry, option_type):
        self.refresh_instruments()
        matches = [
            i for i in self._instruments
            if i["strike"] == float(strike)
            and i["expiry"] == expiry
            and i["instrument_type"] == option_type
        ]
        if not matches:
            return None
        matches.sort(key=lambda i: (i["expiry"], i["instrument_token"]))
        return matches[0]

    def quote(self, symbols):
        return self.kite.quote(symbols)

    def _fetch_candles(self, token):
        now = now_ist()

        def _fetch(days):
            start = now - timedelta(days=days)
            start = start.replace(hour=9, minute=15, second=0, microsecond=0)
            raw = self.kite.historical_data(token, start, now, "5minute")
            return normalize_candles([
                {
                    "start": r["date"].astimezone(IST) if hasattr(r["date"], "astimezone") else r["date"],
                    "open": r["open"], "high": r["high"], "low": r["low"],
                    "close": r["close"], "volume": r.get("volume", 0),
                }
                for r in raw
            ])

        rows = _fetch(CANDLE_LOOKBACK_DAYS)
        if len(rows) < CANDLE_MIN_ROWS:
            # Weekend/holiday: widen once so SMA20 still has enough history.
            rows = _fetch(CANDLE_LOOKBACK_DAYS_FALLBACK)
        last_start = rows[-1]["start"] if rows else None
        self._candles[token] = (rows, now, last_start)
        return rows

    def candles(self, token, force=False):
        now = now_ist()
        cached = self._candles.get(token)
        if cached:
            rows, fetched_at, last_start = cached
            age = (now - fetched_at).total_seconds()
            current_start = floor_5m(now)
            if not force and age < CANDLE_BACKOFF_BASE:
                return rows
            if (not force and last_start == current_start
                    and age < CANDLE_BACKOFF_MAX + random.uniform(0, CANDLE_BACKOFF_JITTER)):
                return rows
        return self._fetch_candles(token)

    def candle_at(self, token, candle_start, retries=6):
        if token is None:
            return None
        target = candle_start.astimezone(IST)
        for attempt in range(retries):
            try:
                rows = self._fetch_candles(token)
            except Exception:
                rows = []
            for r in rows:
                if r["start"] == target:
                    return r
            if attempt < retries - 1:
                time.sleep(1.0)
        return None


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------
class TrailLiveScanner:
    def __init__(self, feed):
        self.feed = feed
        self.base_feed = BaseSignalFeed()
        self.base_status = {}
        self.base_ok = False
        self.states = {"CE": OptionStateMachine("CE"), "PE": OptionStateMachine("PE")}
        self.started_at = now_ist().isoformat()
        self.last_scan_at = None
        self.actual_interval_seconds = None
        self.contracts = {"CE": None, "PE": None}
        self.atm_strike = None
        self.expiry = None
        self.spot = None
        self.last_error = None
        self.last_candle_start = None

    def recover_open_positions(self):
        positions = load_open_positions()
        if not positions:
            return
        now = now_ist()
        for opt, pos in positions.items():
            logger.info("Recovered open %s position %s entry=%.2f candle=%s",
                        opt, pos.trade_id, pos.entry_price,
                        pos.entry_candle_start.isoformat())
            state = self.states[opt]
            state.restore(pos)
            if now >= pos.entry_candle_end:
                token = pos.token
                if token is None:
                    try:
                        exp = date.fromisoformat(str(pos.expiry))
                        contract = self.feed.find_contract(pos.strike, exp, opt)
                        token = contract["instrument_token"] if contract else None
                    except Exception:
                        token = None
                candle = self.feed.candle_at(token, pos.entry_candle_start)
                close_px = candle["close"] if candle else pos.entry_price
                reason = "SAME_CANDLE_EXIT" if candle else "SAME_CANDLE_EXIT_LTP_FALLBACK"
                trade = state.close(pos.entry_candle_end, close_px, reason,
                                    candle_high=candle["high"] if candle else None,
                                    candle_low=candle["low"] if candle else None)
                save_trade(trade)
                delete_open_position(opt)
                logger.info("Recovered %s position closed at %.2f pnl=%.2f",
                            opt, close_px, trade["pnl_points"])

    def _base_contract(self, opt):
        base = (self.base_status or {}).get("options", {}).get(opt) or {}
        token = base.get("token")
        symbol = base.get("tradingsymbol")
        if token is None or not symbol:
            return None
        return {
            "tradingsymbol": symbol,
            "instrument_token": int(token),
            "strike": base.get("strike"),
            "expiry": base.get("expiry"),
        }

    def _resolve_contract(self, opt):
        pos = self.states[opt].position
        if pos is not None and pos.token:
            return {"tradingsymbol": pos.tradingsymbol,
                    "instrument_token": pos.token,
                    "strike": pos.strike, "expiry": pos.expiry}
        return self._base_contract(opt) or self.contracts.get(opt)

    def adopt_base_positions(self, now):
        """Copy any new open base position into this trail scanner.

        The base trade id is recorded in ``consumed_base_trades`` so a trail
        stop exit never re-enters the same base trade while the base scanner
        is still holding it until candle close.
        """
        adopted = []
        options = (self.base_status or {}).get("options", {})
        for opt in ("CE", "PE"):
            state = self.states[opt]
            if state.position is not None:
                continue
            base_opt = options.get(opt) or {}
            base_pos = base_opt.get("position")
            if not base_pos:
                continue
            base_trade_id = base_pos.get("trade_id")
            if not base_trade_id or base_trade_consumed(base_trade_id):
                continue
            try:
                entry_ts = datetime.fromisoformat(base_pos["entry_timestamp"])
                candle_start = datetime.fromisoformat(base_pos["entry_candle_start"])
                candle_end_dt = datetime.fromisoformat(base_pos["entry_candle_end"])
                entry_price = float(base_pos["entry_price"])
                strike = float(base_pos["strike"])
                expiry = str(base_pos["expiry"])
                token = int(base_pos["token"])
                tradingsymbol = str(base_pos["tradingsymbol"])
            except Exception as exc:
                self.last_error = f"base position parse error ({opt}): {exc}"
                logger.error(self.last_error)
                continue
            if candle_start in state.entered_candles:
                mark_base_trade_consumed(base_trade_id, opt)
                continue
            if candle_end_dt.date() != now.date():
                # Never adopt a stale position from an earlier session.
                mark_base_trade_consumed(base_trade_id, opt)
                continue
            pos = Position(
                option_type=opt,
                trade_id=make_trade_id("NIFTY", strike, opt, candle_start),
                strike=strike,
                expiry=expiry,
                token=token,
                tradingsymbol=tradingsymbol,
                entry_timestamp=entry_ts,
                entry_candle_start=candle_start,
                entry_candle_end=candle_end_dt,
                entry_price=entry_price,
                prev_high=float(base_pos.get("prev_high") or 0.0),
                current_open=float(base_pos.get("current_open") or 0.0),
                breakout=bool(base_pos.get("breakout")),
                ltp_at_entry=float(base_pos.get("ltp_at_entry") or entry_price),
                hwm=entry_price,
                stop=None,
            )
            state.restore(pos)
            save_open_position(pos)
            mark_base_trade_consumed(base_trade_id, opt)
            adopted.append((opt, base_trade_id))
            logger.info(
                "ADOPT base %s trade=%s entry=%.2f candle=%s",
                opt, base_trade_id, entry_price, candle_start.isoformat())
        return adopted

    def refresh_contracts(self, spot, force=False):
        atm = float(round(spot / 50) * 50)
        if (not force and self.atm_strike == atm and self.expiry is not None
                and self.expiry >= now_ist().date()):
            return
        expiry = self.feed.nearest_expiry()
        self.atm_strike = atm
        self.expiry = expiry
        for opt in ("CE", "PE"):
            self.contracts[opt] = self.feed.find_contract(atm, expiry, opt)
        logger.info("ATM contract set: strike=%s expiry=%s CE=%s PE=%s",
                    atm, expiry,
                    (self.contracts["CE"] or {}).get("tradingsymbol"),
                    (self.contracts["PE"] or {}).get("tradingsymbol"))

    def scan(self):
        now = now_ist()
        if self.last_scan_at:
            try:
                self.actual_interval_seconds = round(
                    (now - datetime.fromisoformat(self.last_scan_at)).total_seconds(), 2)
            except Exception:
                pass
        self.last_scan_at = now.isoformat()
        errors = []
        allow_entries = entry_window_is_open(now)

        current_candle = floor_5m(now)
        self.last_candle_start = current_candle

        # --- base scanner status: the single source of entry signals -----
        self.base_ok = False
        try:
            self.base_status = self.base_feed.fetch()
            self.base_ok = True
        except Exception as exc:
            self.base_feed.last_error = str(exc)
            errors.append(f"base status error: {exc}")
            logger.error(errors[-1])

        adopted = []
        if allow_entries and self.base_ok:
            try:
                adopted = self.adopt_base_positions(now)
            except Exception as exc:
                errors.append(f"base adopt error: {exc}")
                logger.error(errors[-1])

        # Build ONE batch: NIFTY spot + both option legs when already known.
        symbols = ["NSE:NIFTY 50"]
        symbol_for = {}
        for opt in ("CE", "PE"):
            contract = self._resolve_contract(opt)
            if contract:
                sym = f"NFO:{contract['tradingsymbol']}"
                symbols.append(sym)
                symbol_for[opt] = (sym, contract)

        quotes = {}
        try:
            quotes = self.feed.quote(symbols)
            self.spot = float(quotes["NSE:NIFTY 50"]["last_price"])
        except Exception as exc:
            # Batched call failed; retry spot alone so the scanner keeps going.
            try:
                nifty = self.feed.quote(["NSE:NIFTY 50"])
                self.spot = float(nifty["NSE:NIFTY 50"]["last_price"])
                quotes = {"NSE:NIFTY 50": nifty["NSE:NIFTY 50"]}
                errors.append(f"batched quote failed, retried spot: {exc}")
                logger.error(errors[-1])
            except Exception as exc2:
                self.last_error = f"spot/contract error: {exc2}"
                logger.error(self.last_error)
                return self._status(now, {}, errors=[self.last_error])

        self.refresh_contracts(self.spot, force=self.atm_strike is None)

        # Fetch option quotes only when the contract was not in the batch
        # (first scan, ATM shift, expiry rollover, or a newly adopted leg).
        missing = []
        for opt in ("CE", "PE"):
            contract = self._resolve_contract(opt)
            if not contract:
                symbol_for.pop(opt, None)
                continue
            sym = f"NFO:{contract['tradingsymbol']}"
            symbol_for[opt] = (sym, contract)
            if sym not in quotes and sym not in missing:
                missing.append(sym)
        if missing:
            try:
                quotes.update(self.feed.quote(missing))
            except Exception as exc:
                errors.append(f"option quote error: {exc}")
                logger.error(errors[-1])

        option_status = {}
        for opt in ("CE", "PE"):
            state = self.states[opt]
            pos = state.position
            sym_contract = symbol_for.get(opt)
            if not sym_contract:
                option_status[opt] = {"error": "contract not found"}
                continue
            sym, contract = sym_contract
            ltp = None
            try:
                ltp = float(quotes[sym]["last_price"])
            except Exception:
                errors.append(f"{opt} LTP unavailable")

            token = int(contract["instrument_token"])
            strike = float(contract["strike"])
            expiry = contract["expiry"]
            if isinstance(expiry, date) and not isinstance(expiry, datetime):
                expiry_str = expiry.isoformat()
            else:
                expiry_str = str(expiry)

            # --- trail exit check (before candle-close exit) ---
            if pos is not None:
                stop_hit = state.update_trail(ltp)
                if stop_hit is not None:
                    # Exit price is the actual sampled LTP at the breach.
                    exit_px = round(float(ltp), 2)
                    trade = state.close(pos.entry_candle_end, exit_px,
                                        "TRAIL_STOP_EXIT")
                    save_trade(trade)
                    delete_open_position(opt)
                    logger.info(
                        "TRAIL EXIT %s %s strike=%s entry=%.2f exit=%.2f pnl=%.2f (stop=%.2f)",
                        opt, pos.tradingsymbol, pos.strike, pos.entry_price,
                        exit_px, trade["pnl_points"], pos.stop)
                elif state.needs_exit(now):
                    candle = None
                    try:
                        candle = self.feed.candle_at(token, pos.entry_candle_start)
                    except Exception as exc:
                        errors.append(f"{opt} exit candle error: {exc}")
                        logger.error(errors[-1])
                    if candle is not None:
                        close_px = candle["close"]
                        reason = "SAME_CANDLE_EXIT"
                    else:
                        close_px = ltp if ltp is not None else pos.entry_price
                        reason = "SAME_CANDLE_EXIT_LTP_FALLBACK"
                        errors.append(f"{opt} exit candle unavailable; used LTP")
                    trade = state.close(pos.entry_candle_end, close_px, reason,
                                        candle_high=candle["high"] if candle else None,
                                        candle_low=candle["low"] if candle else None)
                    save_trade(trade)
                    delete_open_position(opt)
                    logger.info(
                        "EXIT %s %s strike=%s entry=%.2f exit=%.2f pnl=%.2f reason=%s",
                        opt, pos.tradingsymbol, pos.strike, pos.entry_price,
                        close_px, trade["pnl_points"], reason)

            base_opt = (self.base_status or {}).get("options", {}).get(opt) or {}
            base_pos = base_opt.get("position")
            option_status[opt] = {
                "tradingsymbol": contract["tradingsymbol"],
                "token": token,
                "strike": strike,
                "expiry": expiry_str,
                "ltp": ltp,
                "sma": (base_opt.get("sma3") or base_opt.get("sma9")
                        or base_opt.get("sma20") or base_opt.get("sma")),
                "prev_close": base_opt.get("prev_close"),
                "prev_high": base_opt.get("prev_high"),
                "current_open": base_opt.get("current_open"),
                "condition_a": base_opt.get("condition_a"),
                "condition_b": base_opt.get("condition_b"),
                "condition_c": base_opt.get("condition_c"),
                "qualified": base_opt.get("qualified"),
                "confirmation": base_opt.get("confirmation"),
                "breakout": base_opt.get("breakout"),
                "signal": base_opt.get("signal"),
                "ready": base_opt.get("ready"),
                "forming_is_current": base_opt.get("forming_is_current"),
                "reason": base_opt.get("reason"),
                "base_scanner": "sma3_high",
                "base_status_ok": self.base_ok,
                "base_trade_id": (base_pos or {}).get("trade_id"),
                "base_has_position": base_pos is not None,
                "entry_made": any(a[0] == opt for a in adopted),
                "position": state.position.as_dict() if state.position else None,
            }

        return self._status(now, option_status, errors=errors)

    def _status(self, now, options, errors=None):
        today = now.date().isoformat()
        return {
            "scanner_id": STRATEGY_ID,
            "scanner_name": SCANNER_NAME,
            "scanner_version": STRATEGY_VERSION,
            "strategy_type": STRATEGY_TYPE,
            "instrument": INSTRUMENT,
            "timeframe": TIMEFRAME,
            "running": True,
            "market_open": market_is_open(now),
            "started_at": self.started_at,
            "last_scan_at": self.last_scan_at,
            "poll_seconds": POLL_SECONDS,
            "actual_interval_seconds": self.actual_interval_seconds,
            "spot": self.spot,
            "atm_strike": self.atm_strike,
            "expiry": self.expiry.isoformat() if hasattr(self.expiry, "isoformat") else self.expiry,
            "options": options,
            "today": today_stats(today),
            "base_scanner": "sma3_high",
            "base_status_ok": self.base_ok,
            "base_status_error": self.base_feed.last_error,
            "errors": errors or [],
            "last_error": self.last_error,
        }


def main():
    logger.info("SMA3 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY) starting (poll=%ss, db=%s)", POLL_SECONDS, DB_PATH)
    init_db()
    try:
        prune_consumed_base_trades()
    except Exception as exc:
        logger.error("consumed-trade prune failed: %s", exc)
    try:
        feed = KiteFeed()
        feed.refresh_instruments()
    except Exception as exc:
        logger.error("Failed to initialise Kite feed: %s", exc)
        traceback.print_exc()
        return 1

    scanner = TrailLiveScanner(feed)
    try:
        scanner.recover_open_positions()
    except Exception as exc:
        logger.error("Open-position recovery failed: %s", exc)
        traceback.print_exc()

    logger.info("SMA3 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY) ready")
    try:
        while True:
            now = now_ist()
            try:
                if not is_weekday(now):
                    state = scanner.scan()
                    state["errors"] = list(state.get("errors", [])) + ["weekend"]
                    save_scan_state(state)
                elif now.time() < session_open_time(now):
                    save_scan_state(scanner._status(now, {}, errors=["pre-market"]))
                elif now.time() >= session_close_time(now) and not any(
                        s.position for s in scanner.states.values()):
                    save_scan_state(scanner._status(now, {}, errors=["market closed"]))
                else:
                    state = scanner.scan()
                    save_scan_state(state)
            except Exception as exc:
                scanner.last_error = f"scan loop error: {exc}"
                logger.error(scanner.last_error)
                traceback.print_exc()
                try:
                    save_scan_state(scanner._status(now, {}, errors=[scanner.last_error]))
                except Exception:
                    pass
            sleep_to_next_tick()
    except KeyboardInterrupt:
        logger.info("SMA3 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY) stopping (SIGINT)")
    finally:
        logger.info("SMA3 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY) stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
