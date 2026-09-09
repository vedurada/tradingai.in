from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.market import OHLCV


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def calculate_vwap(ohlcv: list[dict]) -> float:
    if not ohlcv:
        return 0.0
    total_tpv = 0.0
    total_vol = 0.0
    for row in ohlcv:
        tp = (row.get("high", 0) + row.get("low", 0) + row.get("close", 0)) / 3
        vol = row.get("volume", 0)
        total_tpv += tp * vol
        total_vol += vol
    if total_vol == 0:
        return 0.0
    return round(total_tpv / total_vol, 2)


def calculate_pivot(quote: dict) -> dict[str, float]:
    high = quote.get("high", 0)
    low = quote.get("low", 0)
    close = quote.get("close", 0) or quote.get("previous_close", 0) or quote.get("price", 0)

    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)

    return {
        "pivot": round(pivot, 2),
        "r1": round(r1, 2),
        "s1": round(s1, 2),
        "r2": round(r2, 2),
        "s2": round(s2, 2),
        "r3": round(r3, 2),
        "s3": round(s3, 2),
    }


def calculate_cpr(pivot_data: dict[str, float]) -> dict[str, float]:
    p = pivot_data["pivot"]
    r1 = pivot_data["r1"]
    s1 = pivot_data["s1"]
    bc = (p + s1) / 2
    tc = (p + r1) / 2
    return {
        "pivot": p,
        "bc": round(bc, 2),
        "tc": round(tc, 2),
        "r1": r1,
        "s1": s1,
    }


def calculate_bollinger_bands(
    closes: list[float], period: int = 20, std_mult: float = 2.0
) -> Optional[dict[str, Any]]:
    if len(closes) < period:
        return None
    recent = closes[-period:]
    mid = _mean(recent)
    sd = _std(recent)
    return {
        "upper": round(mid + std_mult * sd, 2),
        "middle": round(mid, 2),
        "lower": round(mid - std_mult * sd, 2),
        "period": period,
    }


def calculate_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = _mean(gains[-period:])
    avg_loss = _mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calculate_macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Optional[dict[str, Any]]:
    if len(closes) < slow + signal:
        return None

    def _ema(values: list[float], period: int) -> list[float]:
        result = []
        k = 2 / (period + 1)
        for i, v in enumerate(values):
            if i == 0:
                result.append(v)
            else:
                result.append(v * k + result[-1] * (1 - k))
        return result

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line[-signal:], signal)
    histogram = [m - s for m, s in zip(macd_line[-signal:], signal_line)]

    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(histogram[-1], 4),
        "fast": fast,
        "slow": slow,
        "signal_period": signal,
    }


def calculate_adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None

    dm_plus = []
    dm_minus = []
    tr_values = []

    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        dm_plus.append(max(up, 0) if up > down else 0)
        dm_minus.append(max(down, 0) if down > up else 0)
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_values.append(tr)

    if len(dm_plus) < period:
        return None

    atr = _mean(tr_values[-period:])
    if atr == 0:
        return 0.0

    di_plus = (_mean(dm_plus[-period:]) / atr) * 100
    di_minus = (_mean(dm_minus[-period:]) / atr) * 100
    dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) != 0 else 0

    return round(dx, 2)


def calculate_support_resistance(
    ohlcv: list[dict], window: int = 20
) -> dict[str, list[float]]:
    if len(ohlcv) < window:
        return {"support": [], "resistance": []}

    highs = [row.get("high", 0) for row in ohlcv[-window:]]
    lows = [row.get("low", 0) for row in ohlcv[-window:]]
    closes = [row.get("close", 0) for row in ohlcv[-window:]]

    max_high = max(highs) if highs else 0
    min_low = min(lows) if lows else 0
    avg_close = _mean(closes) if closes else 0

    resistance = []
    support = []

    for h in set(round(h, 2) for h in highs):
        count = sum(1 for x in highs if abs(x - h) < max_high * 0.005)
        if count >= 2 and h > avg_close:
            resistance.append(h)

    for l in set(round(l, 2) for l in lows):
        count = sum(1 for x in lows if abs(x - l) < max_high * 0.005)
        if count >= 2 and l < avg_close:
            support.append(l)

    resistance = sorted(set(resistance), reverse=True)[:3]
    support = sorted(set(support))[:3]

    if not resistance:
        resistance = [round(max_high, 2)]
    if not support:
        support = [round(min_low, 2)]

    return {
        "support": [round(s, 2) for s in support],
        "resistance": [round(r, 2) for r in resistance],
        "prev_high": round(max_high, 2),
        "prev_low": round(min_low, 2),
    }


def calculate_all_indicators(
    ohlcv: list[dict], current_quote: Optional[dict] = None
) -> dict[str, Any]:
    closes = [row.get("close", 0) for row in ohlcv]
    highs = [row.get("high", 0) for row in ohlcv]
    lows = [row.get("low", 0) for row in ohlcv]

    vwap = calculate_vwap(ohlcv)
    pivot_data = calculate_pivot(current_quote or {"high": 0, "low": 0, "close": 0, "price": 0})
    cpr = calculate_cpr(pivot_data)
    bb = calculate_bollinger_bands(closes)
    rsi = calculate_rsi(closes)
    macd = calculate_macd(closes)
    adx = calculate_adx(highs, lows, closes)
    sr = calculate_support_resistance(ohlcv)
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    ema100 = calculate_ema(closes, 100)
    ema200 = calculate_ema(closes, 200)
    atr = calculate_atr(highs, lows, closes)

    return {
        "vwap": vwap,
        "pivot": pivot_data,
        "cpr": cpr,
        "bollinger_bands": bb,
        "rsi": rsi,
        "macd": macd,
        "adx": adx,
        "support_resistance": sr,
        "ema20": ema20,
        "ema50": ema50,
        "ema100": ema100,
        "ema200": ema200,
        "atr": atr,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def calculate_ema(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return round(ema, 2)


def calculate_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return round(_mean(trs[-period:]), 2)