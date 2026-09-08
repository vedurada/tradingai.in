from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.market import MarketQuote, VIXQuote, MarketOverview

logger = logging.getLogger("tradingai.ai")


class AIService:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, float] = {}
        self._cache_ttl = 300

    def _cached(self, key: str) -> Optional[Any]:
        if key in self._cache and key in self._cache_time:
            if (datetime.now(timezone.utc).timestamp() - self._cache_time[key]) < self._cache_ttl:
                return self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_time[key] = datetime.now(timezone.utc).timestamp()

    def analyze_market(self, overview: MarketOverview) -> dict:
        cached = self._cached("market_analysis")
        if cached:
            return cached

        nifty = overview.nifty
        vix = overview.vix

        signals = []
        if nifty.price > nifty.previous_close:
            signals.append("NIFTY above previous close - bullish momentum")
        else:
            signals.append("NIFTY below previous close - bearish pressure")

        if vix.price < 15:
            signals.append("Low VIX indicates calm market conditions")
        elif vix.price > 20:
            signals.append("High VIX indicates elevated market fear")

        pcr_signal = "Neutral"
        if hasattr(overview, 'pcr') and overview.pcr:
            if overview.pcr > 1.5:
                pcr_signal = "Put-heavy - bearish sentiment"
            elif overview.pcr < 0.7:
                pcr_signal = "Call-heavy - bullish sentiment"

        change_pct = nifty.change_pct
        if change_pct > 1:
            trend = "Bullish"
            confidence = min(80 + change_pct * 5, 95)
        elif change_pct < -1:
            trend = "Bearish"
            confidence = min(80 + abs(change_pct) * 5, 95)
        else:
            trend = "Neutral"
            confidence = 55

        reasons_bullish = []
        reasons_bearish = []

        if change_pct > 0:
            reasons_bullish.append(f"NIFTY up {change_pct:.2f}%")
        else:
            reasons_bearish.append(f"NIFTY down {abs(change_pct):.2f}%")

        if vix.trend == "Declining":
            reasons_bullish.append("VIX declining - reduced fear")
        elif vix.trend == "Rising":
            reasons_bearish.append("VIX rising - increased fear")

        reasons_bullish.append("Market status: Open")

        analysis = {
            "trend": trend,
            "confidence": round(confidence, 1),
            "market_view": "BULLISH" if trend == "Bullish" else "BEARISH" if trend == "Bearish" else "NEUTRAL",
            "reasons_bullish": reasons_bullish,
            "reasons_bearish": reasons_bearish,
            "signals": signals,
            "pcr_signal": pcr_signal,
            "vix_level": vix.price,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._set_cache("market_analysis", analysis)
        return analysis

    def generate_signal(self, symbol: str, quote: MarketQuote) -> dict:
        change_pct = quote.change_pct
        if change_pct > 0.5:
            signal_type = "BUY"
            confidence = min(60 + change_pct * 10, 90)
        elif change_pct < -0.5:
            signal_type = "SELL"
            confidence = min(60 + abs(change_pct) * 10, 90)
        else:
            signal_type = "HOLD"
            confidence = 50

        return {
            "symbol": symbol,
            "signal": signal_type,
            "confidence": round(confidence, 1),
            "price": quote.price,
            "target": round(quote.price * (1.02 if signal_type == "BUY" else 0.98), 2),
            "stop_loss": round(quote.price * (0.98 if signal_type == "BUY" else 1.02), 2),
            "rationale": f"{symbol} {signal_type} signal based on {change_pct:+.2f}% change",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


ai_service = AIService()