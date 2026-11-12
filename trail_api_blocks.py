# ============================================================================
# SMA3_TRAIL trail API
# ============================================================================

SMA3_TRAIL_DB_PATH = os.path.join(BASE, "database", "sma3_trail.db")


def get_sma3_trail_conn():
    """Per-request connection to the dedicated sma3_trail trail database."""
    conn = sqlite3.connect(SMA3_TRAIL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
    except Exception:
        pass
    return conn


def _sma3_trail_live_state():
    try:
        conn = get_sma3_trail_conn()
        row = conn.execute(
            "SELECT value, updated_at FROM sma3_trail_scan_state WHERE key='live_status'"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        state = json.loads(row["value"])
        state["_state_updated_at"] = row["updated_at"]
        return state
    except Exception:
        return {}


def _sma3_trail_scanner_health(state):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    last = state.get("last_scan_at")
    age = None
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
        except Exception:
            age = None
    market_open = bool(state.get("market_open"))
    if last is None:
        status = "NOT_RUNNING"
    elif market_open and age is not None and age <= 15:
        status = "ACTIVE"
    elif market_open and age is not None and age > 15:
        status = "STALE"
    elif not market_open and age is not None and age <= 120:
        status = "IDLE_MARKET_CLOSED"
    else:
        status = "STOPPED"
    return status, age


@app.route("/api/sma3-trail/signals", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_trail_signals():
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        option_type = request.args.get("option_type")
        trade_date = request.args.get("trade_date")
        dataset = request.args.get("dataset")
        conn = get_sma3_trail_conn()
        query = "SELECT * FROM sma3_trail_trades WHERE 1=1"
        params = []
        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.upper())
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "signals": [dict(r) for r in rows],
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma3-trail/trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_trail_trades():
    return api_sma3_trail_signals()


@app.route("/api/sma3-trail/daily-summary", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_trail_daily_summary():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma3_trail_conn()
        query = """
            SELECT trade_date as date,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(pnl_points) as total_pnl_points,
                   ROUND(AVG(pnl_points), 2) as avg_pnl
            FROM sma3_trail_trades
        """
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        query += " GROUP BY trade_date ORDER BY trade_date DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        daily = [dict(r) for r in rows]
        for d in daily:
            d["win_rate"] = round(d["wins"] / d["total_trades"] * 100, 2) if d["total_trades"] > 0 else 0
        return jsonify({"success": True, "daily": daily, "dataset": dataset or "ALL"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma3-trail/scanner-status", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_trail_scanner_status():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma3_trail_conn()
        query = (
            "SELECT COUNT(*) as total_trades, SUM(pnl_points) as total_pnl, "
            "SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins, "
            "SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses "
            "FROM sma3_trail_trades"
        )
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        row = conn.execute(query, params).fetchone()
        conn.close()
        total = row["total_trades"] or 0
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        total_pnl = row["total_pnl"] or 0
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        state = _sma3_trail_live_state()
        status, age = _sma3_trail_scanner_health(state)
        return jsonify({
            "success": True,
            "scanner_id": "sma3_trail",
            "scanner_name": "SMA3 Trail - ATM Option Strike + Trail Exit (BUY ONLY)",
            "scanner_version": "2.0.0",
            "strategy_type": "SMA_BUY_ONLY",
            "instrument": "NIFTY",
            "timeframe": "5m",
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "status": status,
            "last_scan_at": state.get("last_scan_at"),
            "last_scan_age_seconds": round(age, 1) if age is not None else None,
            "poll_seconds": state.get("poll_seconds", 5),
            "actual_interval_seconds": state.get("actual_interval_seconds"),
            "market_open": state.get("market_open"),
            "spot": state.get("spot"),
            "atm_strike": state.get("atm_strike"),
            "expiry": state.get("expiry"),
            "options": state.get("options", {}),
            "today": state.get("today", {}),
            "errors": state.get("errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma3-trail/live-status", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma3_trail_live_status():
    state = _sma3_trail_live_state()
    if not state:
        return jsonify({
            "success": False,
            "status": "NOT_RUNNING",
            "error": "No scanner heartbeat found",
            "poll_seconds": 5,
        }), 200
    status, age = _sma3_trail_scanner_health(state)
    state["status"] = status
    state["last_scan_age_seconds"] = round(age, 1) if age is not None else None
    state["server_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    return jsonify({"success": True, "data": state})


@app.route("/api/sma3-trail/recent-trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_trail_recent_trades():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        dataset = request.args.get("dataset")
        trade_date = request.args.get("trade_date")
        conn = get_sma3_trail_conn()
        query = "SELECT * FROM sma3_trail_trades WHERE 1=1"
        params = []
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
            "dataset": dataset or "ALL",
            "trade_date": trade_date,
        })
    except Exception as e:
        return jsonify({"success": False, "trades": [], "error": str(e)}), 500


@app.route("/api/sma3-trail/today", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma3_trail_today():
    try:
        today = request.args.get("trade_date") or datetime.now(
            ZoneInfo("Asia/Kolkata")).date().isoformat()
        conn = get_sma3_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma3_trail_trades WHERE dataset='LIVE' AND trade_date=? "
            "ORDER BY signal_timestamp DESC",
            (today,),
        ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        pnl = round(sum(t["pnl_points"] or 0 for t in trades), 2)
        wins = sum(1 for t in trades if (t["pnl_points"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl_points"] or 0) < 0)
        return jsonify({
            "success": True,
            "trade_date": today,
            "trades": trades,
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl_points": pnl,
            "is_today": True,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []}), 500


@app.route("/api/sma3-trail/legacy-audit", methods=["GET"])
@limiter.limit("60 per minute")
def api_sma3_trail_legacy_audit():
    return jsonify({
        "success": True,
        "total_audited": 0,
        "compliant": 0,
        "discrepant": 0,
        "compliance_rate_pct": 0,
        "by_option_type": [],
        "discrepancy_reason_groups": [],
        "rows": [],
    })


@app.route("/api/sma3-trail/open-positions", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma3_trail_open_positions():
    try:
        conn = get_sma3_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma3_trail_open_positions ORDER BY entry_timestamp"
        ).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "positions": [dict(r) for r in rows],
            "count": len(rows),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []}), 500


# ============================================================================
# SMA9_TRAIL trail API
# ============================================================================

SMA9_TRAIL_DB_PATH = os.path.join(BASE, "database", "sma9_trail.db")


def get_sma9_trail_conn():
    """Per-request connection to the dedicated sma9_trail trail database."""
    conn = sqlite3.connect(SMA9_TRAIL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
    except Exception:
        pass
    return conn


def _sma9_trail_live_state():
    try:
        conn = get_sma9_trail_conn()
        row = conn.execute(
            "SELECT value, updated_at FROM sma9_trail_scan_state WHERE key='live_status'"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        state = json.loads(row["value"])
        state["_state_updated_at"] = row["updated_at"]
        return state
    except Exception:
        return {}


def _sma9_trail_scanner_health(state):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    last = state.get("last_scan_at")
    age = None
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
        except Exception:
            age = None
    market_open = bool(state.get("market_open"))
    if last is None:
        status = "NOT_RUNNING"
    elif market_open and age is not None and age <= 15:
        status = "ACTIVE"
    elif market_open and age is not None and age > 15:
        status = "STALE"
    elif not market_open and age is not None and age <= 120:
        status = "IDLE_MARKET_CLOSED"
    else:
        status = "STOPPED"
    return status, age


@app.route("/api/sma9-trail/signals", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_trail_signals():
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        option_type = request.args.get("option_type")
        trade_date = request.args.get("trade_date")
        dataset = request.args.get("dataset")
        conn = get_sma9_trail_conn()
        query = "SELECT * FROM sma9_trail_trades WHERE 1=1"
        params = []
        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.upper())
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "signals": [dict(r) for r in rows],
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma9-trail/trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_trail_trades():
    return api_sma9_trail_signals()


@app.route("/api/sma9-trail/daily-summary", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_trail_daily_summary():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma9_trail_conn()
        query = """
            SELECT trade_date as date,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(pnl_points) as total_pnl_points,
                   ROUND(AVG(pnl_points), 2) as avg_pnl
            FROM sma9_trail_trades
        """
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        query += " GROUP BY trade_date ORDER BY trade_date DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        daily = [dict(r) for r in rows]
        for d in daily:
            d["win_rate"] = round(d["wins"] / d["total_trades"] * 100, 2) if d["total_trades"] > 0 else 0
        return jsonify({"success": True, "daily": daily, "dataset": dataset or "ALL"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma9-trail/scanner-status", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_trail_scanner_status():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma9_trail_conn()
        query = (
            "SELECT COUNT(*) as total_trades, SUM(pnl_points) as total_pnl, "
            "SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins, "
            "SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses "
            "FROM sma9_trail_trades"
        )
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        row = conn.execute(query, params).fetchone()
        conn.close()
        total = row["total_trades"] or 0
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        total_pnl = row["total_pnl"] or 0
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        state = _sma9_trail_live_state()
        status, age = _sma9_trail_scanner_health(state)
        return jsonify({
            "success": True,
            "scanner_id": "sma9_trail",
            "scanner_name": "SMA9 Trail - ATM Option Strike + Trail Exit (BUY ONLY)",
            "scanner_version": "2.0.0",
            "strategy_type": "SMA_BUY_ONLY",
            "instrument": "NIFTY",
            "timeframe": "5m",
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "status": status,
            "last_scan_at": state.get("last_scan_at"),
            "last_scan_age_seconds": round(age, 1) if age is not None else None,
            "poll_seconds": state.get("poll_seconds", 5),
            "actual_interval_seconds": state.get("actual_interval_seconds"),
            "market_open": state.get("market_open"),
            "spot": state.get("spot"),
            "atm_strike": state.get("atm_strike"),
            "expiry": state.get("expiry"),
            "options": state.get("options", {}),
            "today": state.get("today", {}),
            "errors": state.get("errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma9-trail/live-status", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma9_trail_live_status():
    state = _sma9_trail_live_state()
    if not state:
        return jsonify({
            "success": False,
            "status": "NOT_RUNNING",
            "error": "No scanner heartbeat found",
            "poll_seconds": 5,
        }), 200
    status, age = _sma9_trail_scanner_health(state)
    state["status"] = status
    state["last_scan_age_seconds"] = round(age, 1) if age is not None else None
    state["server_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    return jsonify({"success": True, "data": state})


@app.route("/api/sma9-trail/recent-trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_trail_recent_trades():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        dataset = request.args.get("dataset")
        trade_date = request.args.get("trade_date")
        conn = get_sma9_trail_conn()
        query = "SELECT * FROM sma9_trail_trades WHERE 1=1"
        params = []
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
            "dataset": dataset or "ALL",
            "trade_date": trade_date,
        })
    except Exception as e:
        return jsonify({"success": False, "trades": [], "error": str(e)}), 500


@app.route("/api/sma9-trail/today", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma9_trail_today():
    try:
        today = request.args.get("trade_date") or datetime.now(
            ZoneInfo("Asia/Kolkata")).date().isoformat()
        conn = get_sma9_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma9_trail_trades WHERE dataset='LIVE' AND trade_date=? "
            "ORDER BY signal_timestamp DESC",
            (today,),
        ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        pnl = round(sum(t["pnl_points"] or 0 for t in trades), 2)
        wins = sum(1 for t in trades if (t["pnl_points"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl_points"] or 0) < 0)
        return jsonify({
            "success": True,
            "trade_date": today,
            "trades": trades,
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl_points": pnl,
            "is_today": True,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []}), 500


@app.route("/api/sma9-trail/legacy-audit", methods=["GET"])
@limiter.limit("60 per minute")
def api_sma9_trail_legacy_audit():
    return jsonify({
        "success": True,
        "total_audited": 0,
        "compliant": 0,
        "discrepant": 0,
        "compliance_rate_pct": 0,
        "by_option_type": [],
        "discrepancy_reason_groups": [],
        "rows": [],
    })


@app.route("/api/sma9-trail/open-positions", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma9_trail_open_positions():
    try:
        conn = get_sma9_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma9_trail_open_positions ORDER BY entry_timestamp"
        ).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "positions": [dict(r) for r in rows],
            "count": len(rows),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []}), 500


# ============================================================================
# SMA20_TRAIL trail API
# ============================================================================

SMA20_TRAIL_DB_PATH = os.path.join(BASE, "database", "sma20_trail.db")


def get_sma20_trail_conn():
    """Per-request connection to the dedicated sma20_trail trail database."""
    conn = sqlite3.connect(SMA20_TRAIL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
    except Exception:
        pass
    return conn


def _sma20_trail_live_state():
    try:
        conn = get_sma20_trail_conn()
        row = conn.execute(
            "SELECT value, updated_at FROM sma20_trail_scan_state WHERE key='live_status'"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        state = json.loads(row["value"])
        state["_state_updated_at"] = row["updated_at"]
        return state
    except Exception:
        return {}


def _sma20_trail_scanner_health(state):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    last = state.get("last_scan_at")
    age = None
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
        except Exception:
            age = None
    market_open = bool(state.get("market_open"))
    if last is None:
        status = "NOT_RUNNING"
    elif market_open and age is not None and age <= 15:
        status = "ACTIVE"
    elif market_open and age is not None and age > 15:
        status = "STALE"
    elif not market_open and age is not None and age <= 120:
        status = "IDLE_MARKET_CLOSED"
    else:
        status = "STOPPED"
    return status, age


@app.route("/api/sma20-trail/signals", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_trail_signals():
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        option_type = request.args.get("option_type")
        trade_date = request.args.get("trade_date")
        dataset = request.args.get("dataset")
        conn = get_sma20_trail_conn()
        query = "SELECT * FROM sma20_trail_trades WHERE 1=1"
        params = []
        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.upper())
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "signals": [dict(r) for r in rows],
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma20-trail/trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_trail_trades():
    return api_sma20_trail_signals()


@app.route("/api/sma20-trail/daily-summary", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_trail_daily_summary():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma20_trail_conn()
        query = """
            SELECT trade_date as date,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(pnl_points) as total_pnl_points,
                   ROUND(AVG(pnl_points), 2) as avg_pnl
            FROM sma20_trail_trades
        """
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        query += " GROUP BY trade_date ORDER BY trade_date DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        daily = [dict(r) for r in rows]
        for d in daily:
            d["win_rate"] = round(d["wins"] / d["total_trades"] * 100, 2) if d["total_trades"] > 0 else 0
        return jsonify({"success": True, "daily": daily, "dataset": dataset or "ALL"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma20-trail/scanner-status", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_trail_scanner_status():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma20_trail_conn()
        query = (
            "SELECT COUNT(*) as total_trades, SUM(pnl_points) as total_pnl, "
            "SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins, "
            "SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses "
            "FROM sma20_trail_trades"
        )
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        row = conn.execute(query, params).fetchone()
        conn.close()
        total = row["total_trades"] or 0
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        total_pnl = row["total_pnl"] or 0
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        state = _sma20_trail_live_state()
        status, age = _sma20_trail_scanner_health(state)
        return jsonify({
            "success": True,
            "scanner_id": "sma20_trail",
            "scanner_name": "SMA20 Trail - ATM Option Strike + Trail Exit (BUY ONLY)",
            "scanner_version": "2.0.0",
            "strategy_type": "SMA_BUY_ONLY",
            "instrument": "NIFTY",
            "timeframe": "5m",
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "status": status,
            "last_scan_at": state.get("last_scan_at"),
            "last_scan_age_seconds": round(age, 1) if age is not None else None,
            "poll_seconds": state.get("poll_seconds", 5),
            "actual_interval_seconds": state.get("actual_interval_seconds"),
            "market_open": state.get("market_open"),
            "spot": state.get("spot"),
            "atm_strike": state.get("atm_strike"),
            "expiry": state.get("expiry"),
            "options": state.get("options", {}),
            "today": state.get("today", {}),
            "errors": state.get("errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma20-trail/live-status", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma20_trail_live_status():
    state = _sma20_trail_live_state()
    if not state:
        return jsonify({
            "success": False,
            "status": "NOT_RUNNING",
            "error": "No scanner heartbeat found",
            "poll_seconds": 5,
        }), 200
    status, age = _sma20_trail_scanner_health(state)
    state["status"] = status
    state["last_scan_age_seconds"] = round(age, 1) if age is not None else None
    state["server_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    return jsonify({"success": True, "data": state})


@app.route("/api/sma20-trail/recent-trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_trail_recent_trades():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        dataset = request.args.get("dataset")
        trade_date = request.args.get("trade_date")
        conn = get_sma20_trail_conn()
        query = "SELECT * FROM sma20_trail_trades WHERE 1=1"
        params = []
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
            "dataset": dataset or "ALL",
            "trade_date": trade_date,
        })
    except Exception as e:
        return jsonify({"success": False, "trades": [], "error": str(e)}), 500


@app.route("/api/sma20-trail/today", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma20_trail_today():
    try:
        today = request.args.get("trade_date") or datetime.now(
            ZoneInfo("Asia/Kolkata")).date().isoformat()
        conn = get_sma20_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma20_trail_trades WHERE dataset='LIVE' AND trade_date=? "
            "ORDER BY signal_timestamp DESC",
            (today,),
        ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        pnl = round(sum(t["pnl_points"] or 0 for t in trades), 2)
        wins = sum(1 for t in trades if (t["pnl_points"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl_points"] or 0) < 0)
        return jsonify({
            "success": True,
            "trade_date": today,
            "trades": trades,
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl_points": pnl,
            "is_today": True,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []}), 500


@app.route("/api/sma20-trail/legacy-audit", methods=["GET"])
@limiter.limit("60 per minute")
def api_sma20_trail_legacy_audit():
    return jsonify({
        "success": True,
        "total_audited": 0,
        "compliant": 0,
        "discrepant": 0,
        "compliance_rate_pct": 0,
        "by_option_type": [],
        "discrepancy_reason_groups": [],
        "rows": [],
    })


@app.route("/api/sma20-trail/open-positions", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma20_trail_open_positions():
    try:
        conn = get_sma20_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma20_trail_open_positions ORDER BY entry_timestamp"
        ).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "positions": [dict(r) for r in rows],
            "count": len(rows),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []}), 500


# ============================================================================
# SMA3_HIGH_TRAIL trail API
# ============================================================================

SMA3_HIGH_TRAIL_DB_PATH = os.path.join(BASE, "database", "sma3_high_trail.db")


def get_sma3_high_trail_conn():
    """Per-request connection to the dedicated sma3_high_trail trail database."""
    conn = sqlite3.connect(SMA3_HIGH_TRAIL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
    except Exception:
        pass
    return conn


def _sma3_high_trail_live_state():
    try:
        conn = get_sma3_high_trail_conn()
        row = conn.execute(
            "SELECT value, updated_at FROM sma3_high_trail_scan_state WHERE key='live_status'"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        state = json.loads(row["value"])
        state["_state_updated_at"] = row["updated_at"]
        return state
    except Exception:
        return {}


def _sma3_high_trail_scanner_health(state):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    last = state.get("last_scan_at")
    age = None
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
        except Exception:
            age = None
    market_open = bool(state.get("market_open"))
    if last is None:
        status = "NOT_RUNNING"
    elif market_open and age is not None and age <= 15:
        status = "ACTIVE"
    elif market_open and age is not None and age > 15:
        status = "STALE"
    elif not market_open and age is not None and age <= 120:
        status = "IDLE_MARKET_CLOSED"
    else:
        status = "STOPPED"
    return status, age


@app.route("/api/sma3-high-trail/signals", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_high_trail_signals():
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        option_type = request.args.get("option_type")
        trade_date = request.args.get("trade_date")
        dataset = request.args.get("dataset")
        conn = get_sma3_high_trail_conn()
        query = "SELECT * FROM sma3_high_trail_trades WHERE 1=1"
        params = []
        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.upper())
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "signals": [dict(r) for r in rows],
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma3-high-trail/trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_high_trail_trades():
    return api_sma3_high_trail_signals()


@app.route("/api/sma3-high-trail/daily-summary", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_high_trail_daily_summary():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma3_high_trail_conn()
        query = """
            SELECT trade_date as date,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(pnl_points) as total_pnl_points,
                   ROUND(AVG(pnl_points), 2) as avg_pnl
            FROM sma3_high_trail_trades
        """
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        query += " GROUP BY trade_date ORDER BY trade_date DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        daily = [dict(r) for r in rows]
        for d in daily:
            d["win_rate"] = round(d["wins"] / d["total_trades"] * 100, 2) if d["total_trades"] > 0 else 0
        return jsonify({"success": True, "daily": daily, "dataset": dataset or "ALL"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma3-high-trail/scanner-status", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_high_trail_scanner_status():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma3_high_trail_conn()
        query = (
            "SELECT COUNT(*) as total_trades, SUM(pnl_points) as total_pnl, "
            "SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins, "
            "SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses "
            "FROM sma3_high_trail_trades"
        )
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        row = conn.execute(query, params).fetchone()
        conn.close()
        total = row["total_trades"] or 0
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        total_pnl = row["total_pnl"] or 0
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        state = _sma3_high_trail_live_state()
        status, age = _sma3_high_trail_scanner_health(state)
        return jsonify({
            "success": True,
            "scanner_id": "sma3_high_trail",
            "scanner_name": "SMA3 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY)",
            "scanner_version": "2.0.0",
            "strategy_type": "SMA_HIGH_BUY_ONLY",
            "instrument": "NIFTY",
            "timeframe": "5m",
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "status": status,
            "last_scan_at": state.get("last_scan_at"),
            "last_scan_age_seconds": round(age, 1) if age is not None else None,
            "poll_seconds": state.get("poll_seconds", 5),
            "actual_interval_seconds": state.get("actual_interval_seconds"),
            "market_open": state.get("market_open"),
            "spot": state.get("spot"),
            "atm_strike": state.get("atm_strike"),
            "expiry": state.get("expiry"),
            "options": state.get("options", {}),
            "today": state.get("today", {}),
            "errors": state.get("errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma3-high-trail/live-status", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma3_high_trail_live_status():
    state = _sma3_high_trail_live_state()
    if not state:
        return jsonify({
            "success": False,
            "status": "NOT_RUNNING",
            "error": "No scanner heartbeat found",
            "poll_seconds": 5,
        }), 200
    status, age = _sma3_high_trail_scanner_health(state)
    state["status"] = status
    state["last_scan_age_seconds"] = round(age, 1) if age is not None else None
    state["server_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    return jsonify({"success": True, "data": state})


@app.route("/api/sma3-high-trail/recent-trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma3_high_trail_recent_trades():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        dataset = request.args.get("dataset")
        trade_date = request.args.get("trade_date")
        conn = get_sma3_high_trail_conn()
        query = "SELECT * FROM sma3_high_trail_trades WHERE 1=1"
        params = []
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
            "dataset": dataset or "ALL",
            "trade_date": trade_date,
        })
    except Exception as e:
        return jsonify({"success": False, "trades": [], "error": str(e)}), 500


@app.route("/api/sma3-high-trail/today", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma3_high_trail_today():
    try:
        today = request.args.get("trade_date") or datetime.now(
            ZoneInfo("Asia/Kolkata")).date().isoformat()
        conn = get_sma3_high_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma3_high_trail_trades WHERE dataset='LIVE' AND trade_date=? "
            "ORDER BY signal_timestamp DESC",
            (today,),
        ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        pnl = round(sum(t["pnl_points"] or 0 for t in trades), 2)
        wins = sum(1 for t in trades if (t["pnl_points"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl_points"] or 0) < 0)
        return jsonify({
            "success": True,
            "trade_date": today,
            "trades": trades,
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl_points": pnl,
            "is_today": True,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []}), 500


@app.route("/api/sma3-high-trail/legacy-audit", methods=["GET"])
@limiter.limit("60 per minute")
def api_sma3_high_trail_legacy_audit():
    return jsonify({
        "success": True,
        "total_audited": 0,
        "compliant": 0,
        "discrepant": 0,
        "compliance_rate_pct": 0,
        "by_option_type": [],
        "discrepancy_reason_groups": [],
        "rows": [],
    })


@app.route("/api/sma3-high-trail/open-positions", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma3_high_trail_open_positions():
    try:
        conn = get_sma3_high_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma3_high_trail_open_positions ORDER BY entry_timestamp"
        ).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "positions": [dict(r) for r in rows],
            "count": len(rows),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []}), 500


# ============================================================================
# SMA9_HIGH_TRAIL trail API
# ============================================================================

SMA9_HIGH_TRAIL_DB_PATH = os.path.join(BASE, "database", "sma9_high_trail.db")


def get_sma9_high_trail_conn():
    """Per-request connection to the dedicated sma9_high_trail trail database."""
    conn = sqlite3.connect(SMA9_HIGH_TRAIL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
    except Exception:
        pass
    return conn


def _sma9_high_trail_live_state():
    try:
        conn = get_sma9_high_trail_conn()
        row = conn.execute(
            "SELECT value, updated_at FROM sma9_high_trail_scan_state WHERE key='live_status'"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        state = json.loads(row["value"])
        state["_state_updated_at"] = row["updated_at"]
        return state
    except Exception:
        return {}


def _sma9_high_trail_scanner_health(state):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    last = state.get("last_scan_at")
    age = None
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
        except Exception:
            age = None
    market_open = bool(state.get("market_open"))
    if last is None:
        status = "NOT_RUNNING"
    elif market_open and age is not None and age <= 15:
        status = "ACTIVE"
    elif market_open and age is not None and age > 15:
        status = "STALE"
    elif not market_open and age is not None and age <= 120:
        status = "IDLE_MARKET_CLOSED"
    else:
        status = "STOPPED"
    return status, age


@app.route("/api/sma9-high-trail/signals", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_high_trail_signals():
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        option_type = request.args.get("option_type")
        trade_date = request.args.get("trade_date")
        dataset = request.args.get("dataset")
        conn = get_sma9_high_trail_conn()
        query = "SELECT * FROM sma9_high_trail_trades WHERE 1=1"
        params = []
        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.upper())
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "signals": [dict(r) for r in rows],
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma9-high-trail/trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_high_trail_trades():
    return api_sma9_high_trail_signals()


@app.route("/api/sma9-high-trail/daily-summary", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_high_trail_daily_summary():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma9_high_trail_conn()
        query = """
            SELECT trade_date as date,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(pnl_points) as total_pnl_points,
                   ROUND(AVG(pnl_points), 2) as avg_pnl
            FROM sma9_high_trail_trades
        """
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        query += " GROUP BY trade_date ORDER BY trade_date DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        daily = [dict(r) for r in rows]
        for d in daily:
            d["win_rate"] = round(d["wins"] / d["total_trades"] * 100, 2) if d["total_trades"] > 0 else 0
        return jsonify({"success": True, "daily": daily, "dataset": dataset or "ALL"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma9-high-trail/scanner-status", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_high_trail_scanner_status():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma9_high_trail_conn()
        query = (
            "SELECT COUNT(*) as total_trades, SUM(pnl_points) as total_pnl, "
            "SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins, "
            "SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses "
            "FROM sma9_high_trail_trades"
        )
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        row = conn.execute(query, params).fetchone()
        conn.close()
        total = row["total_trades"] or 0
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        total_pnl = row["total_pnl"] or 0
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        state = _sma9_high_trail_live_state()
        status, age = _sma9_high_trail_scanner_health(state)
        return jsonify({
            "success": True,
            "scanner_id": "sma9_high_trail",
            "scanner_name": "SMA9 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY)",
            "scanner_version": "2.0.0",
            "strategy_type": "SMA_HIGH_BUY_ONLY",
            "instrument": "NIFTY",
            "timeframe": "5m",
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "status": status,
            "last_scan_at": state.get("last_scan_at"),
            "last_scan_age_seconds": round(age, 1) if age is not None else None,
            "poll_seconds": state.get("poll_seconds", 5),
            "actual_interval_seconds": state.get("actual_interval_seconds"),
            "market_open": state.get("market_open"),
            "spot": state.get("spot"),
            "atm_strike": state.get("atm_strike"),
            "expiry": state.get("expiry"),
            "options": state.get("options", {}),
            "today": state.get("today", {}),
            "errors": state.get("errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma9-high-trail/live-status", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma9_high_trail_live_status():
    state = _sma9_high_trail_live_state()
    if not state:
        return jsonify({
            "success": False,
            "status": "NOT_RUNNING",
            "error": "No scanner heartbeat found",
            "poll_seconds": 5,
        }), 200
    status, age = _sma9_high_trail_scanner_health(state)
    state["status"] = status
    state["last_scan_age_seconds"] = round(age, 1) if age is not None else None
    state["server_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    return jsonify({"success": True, "data": state})


@app.route("/api/sma9-high-trail/recent-trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma9_high_trail_recent_trades():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        dataset = request.args.get("dataset")
        trade_date = request.args.get("trade_date")
        conn = get_sma9_high_trail_conn()
        query = "SELECT * FROM sma9_high_trail_trades WHERE 1=1"
        params = []
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
            "dataset": dataset or "ALL",
            "trade_date": trade_date,
        })
    except Exception as e:
        return jsonify({"success": False, "trades": [], "error": str(e)}), 500


@app.route("/api/sma9-high-trail/today", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma9_high_trail_today():
    try:
        today = request.args.get("trade_date") or datetime.now(
            ZoneInfo("Asia/Kolkata")).date().isoformat()
        conn = get_sma9_high_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma9_high_trail_trades WHERE dataset='LIVE' AND trade_date=? "
            "ORDER BY signal_timestamp DESC",
            (today,),
        ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        pnl = round(sum(t["pnl_points"] or 0 for t in trades), 2)
        wins = sum(1 for t in trades if (t["pnl_points"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl_points"] or 0) < 0)
        return jsonify({
            "success": True,
            "trade_date": today,
            "trades": trades,
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl_points": pnl,
            "is_today": True,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []}), 500


@app.route("/api/sma9-high-trail/legacy-audit", methods=["GET"])
@limiter.limit("60 per minute")
def api_sma9_high_trail_legacy_audit():
    return jsonify({
        "success": True,
        "total_audited": 0,
        "compliant": 0,
        "discrepant": 0,
        "compliance_rate_pct": 0,
        "by_option_type": [],
        "discrepancy_reason_groups": [],
        "rows": [],
    })


@app.route("/api/sma9-high-trail/open-positions", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma9_high_trail_open_positions():
    try:
        conn = get_sma9_high_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma9_high_trail_open_positions ORDER BY entry_timestamp"
        ).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "positions": [dict(r) for r in rows],
            "count": len(rows),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []}), 500


# ============================================================================
# SMA20_HIGH_TRAIL trail API
# ============================================================================

SMA20_HIGH_TRAIL_DB_PATH = os.path.join(BASE, "database", "sma20_high_trail.db")


def get_sma20_high_trail_conn():
    """Per-request connection to the dedicated sma20_high_trail trail database."""
    conn = sqlite3.connect(SMA20_HIGH_TRAIL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
    except Exception:
        pass
    return conn


def _sma20_high_trail_live_state():
    try:
        conn = get_sma20_high_trail_conn()
        row = conn.execute(
            "SELECT value, updated_at FROM sma20_high_trail_scan_state WHERE key='live_status'"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        state = json.loads(row["value"])
        state["_state_updated_at"] = row["updated_at"]
        return state
    except Exception:
        return {}


def _sma20_high_trail_scanner_health(state):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    last = state.get("last_scan_at")
    age = None
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
        except Exception:
            age = None
    market_open = bool(state.get("market_open"))
    if last is None:
        status = "NOT_RUNNING"
    elif market_open and age is not None and age <= 15:
        status = "ACTIVE"
    elif market_open and age is not None and age > 15:
        status = "STALE"
    elif not market_open and age is not None and age <= 120:
        status = "IDLE_MARKET_CLOSED"
    else:
        status = "STOPPED"
    return status, age


@app.route("/api/sma20-high-trail/signals", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_high_trail_signals():
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        option_type = request.args.get("option_type")
        trade_date = request.args.get("trade_date")
        dataset = request.args.get("dataset")
        conn = get_sma20_high_trail_conn()
        query = "SELECT * FROM sma20_high_trail_trades WHERE 1=1"
        params = []
        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.upper())
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "signals": [dict(r) for r in rows],
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma20-high-trail/trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_high_trail_trades():
    return api_sma20_high_trail_signals()


@app.route("/api/sma20-high-trail/daily-summary", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_high_trail_daily_summary():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma20_high_trail_conn()
        query = """
            SELECT trade_date as date,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(pnl_points) as total_pnl_points,
                   ROUND(AVG(pnl_points), 2) as avg_pnl
            FROM sma20_high_trail_trades
        """
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        query += " GROUP BY trade_date ORDER BY trade_date DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        daily = [dict(r) for r in rows]
        for d in daily:
            d["win_rate"] = round(d["wins"] / d["total_trades"] * 100, 2) if d["total_trades"] > 0 else 0
        return jsonify({"success": True, "daily": daily, "dataset": dataset or "ALL"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma20-high-trail/scanner-status", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_high_trail_scanner_status():
    try:
        dataset = request.args.get("dataset")
        conn = get_sma20_high_trail_conn()
        query = (
            "SELECT COUNT(*) as total_trades, SUM(pnl_points) as total_pnl, "
            "SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins, "
            "SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses "
            "FROM sma20_high_trail_trades"
        )
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        row = conn.execute(query, params).fetchone()
        conn.close()
        total = row["total_trades"] or 0
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        total_pnl = row["total_pnl"] or 0
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        state = _sma20_high_trail_live_state()
        status, age = _sma20_high_trail_scanner_health(state)
        return jsonify({
            "success": True,
            "scanner_id": "sma20_high_trail",
            "scanner_name": "SMA20 HIGH Trail - ATM Option Strike + Trail Exit (BUY ONLY)",
            "scanner_version": "2.0.0",
            "strategy_type": "SMA_HIGH_BUY_ONLY",
            "instrument": "NIFTY",
            "timeframe": "5m",
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "status": status,
            "last_scan_at": state.get("last_scan_at"),
            "last_scan_age_seconds": round(age, 1) if age is not None else None,
            "poll_seconds": state.get("poll_seconds", 5),
            "actual_interval_seconds": state.get("actual_interval_seconds"),
            "market_open": state.get("market_open"),
            "spot": state.get("spot"),
            "atm_strike": state.get("atm_strike"),
            "expiry": state.get("expiry"),
            "options": state.get("options", {}),
            "today": state.get("today", {}),
            "errors": state.get("errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sma20-high-trail/live-status", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma20_high_trail_live_status():
    state = _sma20_high_trail_live_state()
    if not state:
        return jsonify({
            "success": False,
            "status": "NOT_RUNNING",
            "error": "No scanner heartbeat found",
            "poll_seconds": 5,
        }), 200
    status, age = _sma20_high_trail_scanner_health(state)
    state["status"] = status
    state["last_scan_age_seconds"] = round(age, 1) if age is not None else None
    state["server_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    return jsonify({"success": True, "data": state})


@app.route("/api/sma20-high-trail/recent-trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_sma20_high_trail_recent_trades():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        dataset = request.args.get("dataset")
        trade_date = request.args.get("trade_date")
        conn = get_sma20_high_trail_conn()
        query = "SELECT * FROM sma20_high_trail_trades WHERE 1=1"
        params = []
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
            "dataset": dataset or "ALL",
            "trade_date": trade_date,
        })
    except Exception as e:
        return jsonify({"success": False, "trades": [], "error": str(e)}), 500


@app.route("/api/sma20-high-trail/today", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma20_high_trail_today():
    try:
        today = request.args.get("trade_date") or datetime.now(
            ZoneInfo("Asia/Kolkata")).date().isoformat()
        conn = get_sma20_high_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma20_high_trail_trades WHERE dataset='LIVE' AND trade_date=? "
            "ORDER BY signal_timestamp DESC",
            (today,),
        ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        pnl = round(sum(t["pnl_points"] or 0 for t in trades), 2)
        wins = sum(1 for t in trades if (t["pnl_points"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl_points"] or 0) < 0)
        return jsonify({
            "success": True,
            "trade_date": today,
            "trades": trades,
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl_points": pnl,
            "is_today": True,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []}), 500


@app.route("/api/sma20-high-trail/legacy-audit", methods=["GET"])
@limiter.limit("60 per minute")
def api_sma20_high_trail_legacy_audit():
    return jsonify({
        "success": True,
        "total_audited": 0,
        "compliant": 0,
        "discrepant": 0,
        "compliance_rate_pct": 0,
        "by_option_type": [],
        "discrepancy_reason_groups": [],
        "rows": [],
    })


@app.route("/api/sma20-high-trail/open-positions", methods=["GET"])
@limiter.limit("180 per minute")
def api_sma20_high_trail_open_positions():
    try:
        conn = get_sma20_high_trail_conn()
        rows = conn.execute(
            "SELECT * FROM sma20_high_trail_open_positions ORDER BY entry_timestamp"
        ).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "positions": [dict(r) for r in rows],
            "count": len(rows),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []}), 500


# ============================================================================
# NO_SMA_TRAIL trail API
# ============================================================================

NO_SMA_TRAIL_DB_PATH = os.path.join(BASE, "database", "no_sma_trail.db")


def get_no_sma_trail_conn():
    """Per-request connection to the dedicated no_sma_trail trail database."""
    conn = sqlite3.connect(NO_SMA_TRAIL_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
    except Exception:
        pass
    return conn


def _no_sma_trail_live_state():
    try:
        conn = get_no_sma_trail_conn()
        row = conn.execute(
            "SELECT value, updated_at FROM no_sma_trail_scan_state WHERE key='live_status'"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        state = json.loads(row["value"])
        state["_state_updated_at"] = row["updated_at"]
        return state
    except Exception:
        return {}


def _no_sma_trail_scanner_health(state):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    last = state.get("last_scan_at")
    age = None
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
        except Exception:
            age = None
    market_open = bool(state.get("market_open"))
    if last is None:
        status = "NOT_RUNNING"
    elif market_open and age is not None and age <= 15:
        status = "ACTIVE"
    elif market_open and age is not None and age > 15:
        status = "STALE"
    elif not market_open and age is not None and age <= 120:
        status = "IDLE_MARKET_CLOSED"
    else:
        status = "STOPPED"
    return status, age


@app.route("/api/no-sma-trail/signals", methods=["GET"])
@limiter.limit("120 per minute")
def api_no_sma_trail_signals():
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        option_type = request.args.get("option_type")
        trade_date = request.args.get("trade_date")
        dataset = request.args.get("dataset")
        conn = get_no_sma_trail_conn()
        query = "SELECT * FROM no_sma_trail_trades WHERE 1=1"
        params = []
        if option_type:
            query += " AND option_type = ?"
            params.append(option_type.upper())
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "signals": [dict(r) for r in rows],
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/no-sma-trail/trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_no_sma_trail_trades():
    return api_no_sma_trail_signals()


@app.route("/api/no-sma-trail/daily-summary", methods=["GET"])
@limiter.limit("120 per minute")
def api_no_sma_trail_daily_summary():
    try:
        dataset = request.args.get("dataset")
        conn = get_no_sma_trail_conn()
        query = """
            SELECT trade_date as date,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses,
                   SUM(pnl_points) as total_pnl_points,
                   ROUND(AVG(pnl_points), 2) as avg_pnl
            FROM no_sma_trail_trades
        """
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        query += " GROUP BY trade_date ORDER BY trade_date DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        daily = [dict(r) for r in rows]
        for d in daily:
            d["win_rate"] = round(d["wins"] / d["total_trades"] * 100, 2) if d["total_trades"] > 0 else 0
        return jsonify({"success": True, "daily": daily, "dataset": dataset or "ALL"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/no-sma-trail/scanner-status", methods=["GET"])
@limiter.limit("120 per minute")
def api_no_sma_trail_scanner_status():
    try:
        dataset = request.args.get("dataset")
        conn = get_no_sma_trail_conn()
        query = (
            "SELECT COUNT(*) as total_trades, SUM(pnl_points) as total_pnl, "
            "SUM(CASE WHEN pnl_points > 0 THEN 1 ELSE 0 END) as wins, "
            "SUM(CASE WHEN pnl_points < 0 THEN 1 ELSE 0 END) as losses "
            "FROM no_sma_trail_trades"
        )
        params = []
        if dataset:
            query += " WHERE dataset = ?"
            params.append(dataset)
        row = conn.execute(query, params).fetchone()
        conn.close()
        total = row["total_trades"] or 0
        wins = row["wins"] or 0
        losses = row["losses"] or 0
        total_pnl = row["total_pnl"] or 0
        win_rate = round(wins / total * 100, 2) if total > 0 else 0
        state = _no_sma_trail_live_state()
        status, age = _no_sma_trail_scanner_health(state)
        return jsonify({
            "success": True,
            "scanner_id": "no_sma_trail",
            "scanner_name": "NO-SMA Trail - ATM Option Strike + Trail Exit (BUY ONLY)",
            "scanner_version": "2.0.0",
            "strategy_type": "PREV_HIGH_BUY_ONLY",
            "instrument": "NIFTY",
            "timeframe": "5m",
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "status": status,
            "last_scan_at": state.get("last_scan_at"),
            "last_scan_age_seconds": round(age, 1) if age is not None else None,
            "poll_seconds": state.get("poll_seconds", 5),
            "actual_interval_seconds": state.get("actual_interval_seconds"),
            "market_open": state.get("market_open"),
            "spot": state.get("spot"),
            "atm_strike": state.get("atm_strike"),
            "expiry": state.get("expiry"),
            "options": state.get("options", {}),
            "today": state.get("today", {}),
            "errors": state.get("errors", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/no-sma-trail/live-status", methods=["GET"])
@limiter.limit("180 per minute")
def api_no_sma_trail_live_status():
    state = _no_sma_trail_live_state()
    if not state:
        return jsonify({
            "success": False,
            "status": "NOT_RUNNING",
            "error": "No scanner heartbeat found",
            "poll_seconds": 5,
        }), 200
    status, age = _no_sma_trail_scanner_health(state)
    state["status"] = status
    state["last_scan_age_seconds"] = round(age, 1) if age is not None else None
    state["server_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    return jsonify({"success": True, "data": state})


@app.route("/api/no-sma-trail/recent-trades", methods=["GET"])
@limiter.limit("120 per minute")
def api_no_sma_trail_recent_trades():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        dataset = request.args.get("dataset")
        trade_date = request.args.get("trade_date")
        conn = get_no_sma_trail_conn()
        query = "SELECT * FROM no_sma_trail_trades WHERE 1=1"
        params = []
        if dataset:
            query += " AND dataset = ?"
            params.append(dataset)
        if trade_date:
            query += " AND trade_date = ?"
            params.append(trade_date)
        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        total = conn.execute(count_query, params).fetchone()[0]
        query += " ORDER BY signal_timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "trades": [dict(r) for r in rows],
            "count": len(rows),
            "total": total,
            "dataset": dataset or "ALL",
            "trade_date": trade_date,
        })
    except Exception as e:
        return jsonify({"success": False, "trades": [], "error": str(e)}), 500


@app.route("/api/no-sma-trail/today", methods=["GET"])
@limiter.limit("180 per minute")
def api_no_sma_trail_today():
    try:
        today = request.args.get("trade_date") or datetime.now(
            ZoneInfo("Asia/Kolkata")).date().isoformat()
        conn = get_no_sma_trail_conn()
        rows = conn.execute(
            "SELECT * FROM no_sma_trail_trades WHERE dataset='LIVE' AND trade_date=? "
            "ORDER BY signal_timestamp DESC",
            (today,),
        ).fetchall()
        conn.close()
        trades = [dict(r) for r in rows]
        pnl = round(sum(t["pnl_points"] or 0 for t in trades), 2)
        wins = sum(1 for t in trades if (t["pnl_points"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl_points"] or 0) < 0)
        return jsonify({
            "success": True,
            "trade_date": today,
            "trades": trades,
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl_points": pnl,
            "is_today": True,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []}), 500


@app.route("/api/no-sma-trail/legacy-audit", methods=["GET"])
@limiter.limit("60 per minute")
def api_no_sma_trail_legacy_audit():
    return jsonify({
        "success": True,
        "total_audited": 0,
        "compliant": 0,
        "discrepant": 0,
        "compliance_rate_pct": 0,
        "by_option_type": [],
        "discrepancy_reason_groups": [],
        "rows": [],
    })


@app.route("/api/no-sma-trail/open-positions", methods=["GET"])
@limiter.limit("180 per minute")
def api_no_sma_trail_open_positions():
    try:
        conn = get_no_sma_trail_conn()
        rows = conn.execute(
            "SELECT * FROM no_sma_trail_open_positions ORDER BY entry_timestamp"
        ).fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "positions": [dict(r) for r in rows],
            "count": len(rows),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []}), 500
