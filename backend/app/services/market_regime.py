from __future__ import annotations

import math
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("tradingai.regime")


class MarketRegimeEngine:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, float] = {}
        self._cache_ttl = 300

    def _cached(self, key: str) -> Optional[Any]:
        if key in self._cache and key in self._cache_time:
            if (datetime.utcnow().timestamp() - self._cache_time[key]) < self._cache_ttl:
                return self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_time[key] = datetime.utcnow().timestamp()

    def evaluate(
        self,
        price: float,
        vwap: float,
        prev_close: float,
        rsi: Optional[float],
        macd: Optional[dict],
        adx: Optional[float],
        vix_price: float,
        bollinger: Optional[dict],
        pivot: Optional[dict],
        support_resistance: Optional[dict],
        pcr: Optional[float] = None,
        breadth_positive: bool = True,
        gap_up: bool = False,
        options_oi_change: float = 0,
    ) -> dict:
        cached_key = f"regime:{price}:{vwap}:{rsi}:{adx}"
        cached = self._cached(cached_key)
        if cached:
            return cached

        scores: dict[str, float] = {
            "trend_up": 0.0,
            "trend_down": 0.0,
            "range": 0.0,
            "breakout": 0.0,
            "breakdown": 0.0,
            "high_volatility": 0.0,
            "low_volatility": 0.0,
            "opening_volatility": 0.0,
        }
        evidence: list[str] = []

        # 1. Trend analysis (EMA / VWAP / Price position)
        if vwap > 0 and price > 0:
            vwap_diff = (price - vwap) / vwap * 100
            if vwap_diff > 1:
                scores["trend_up"] += 0.25
                evidence.append(f"Price above VWAP by {vwap_diff:.2f}%")
            elif vwap_diff < -1:
                scores["trend_down"] += 0.25
                evidence.append(f"Price below VWAP by {abs(vwap_diff):.2f}%")
            else:
                scores["range"] += 0.15
                evidence.append(f"Price near VWAP ({vwap_diff:.2f}%)")

        # 2. RSI analysis
        if rsi is not None:
            if rsi > 70:
                scores["trend_up"] += 0.1
                evidence.append(f"RSI overbought ({rsi})")
            elif rsi < 30:
                scores["trend_down"] += 0.1
                evidence.append(f"RSI oversold ({rsi})")
            elif 40 < rsi < 60:
                scores["range"] += 0.1
                evidence.append(f"RSI neutral ({rsi})")
            else:
                evidence.append(f"RSI = {rsi}")

        # 3. MACD analysis
        if macd is not None:
            hist = macd.get("histogram", 0)
            if hist > 0:
                scores["trend_up"] += 0.1
                evidence.append("MACD histogram positive")
            elif hist < 0:
                scores["trend_down"] += 0.1
                evidence.append("MACD histogram negative")
            else:
                evidence.append("MACD neutral")

        # 4. ADX (trend strength)
        if adx is not None:
            if adx > 25:
                scores["trend_up"] += 0.1
                scores["trend_down"] += 0.1
                evidence.append(f"Strong trend (ADX={adx})")
            elif adx < 20:
                scores["range"] += 0.15
                evidence.append(f"Weak trend / range (ADX={adx})")
            else:
                evidence.append(f"Moderate trend (ADX={adx})")

        # 5. Volatility (VIX / ATR proxy)
        if vix_price > 25:
            scores["high_volatility"] += 0.3
            evidence.append(f"High VIX ({vix_price})")
        elif vix_price < 12:
            scores["low_volatility"] += 0.3
            evidence.append(f"Low VIX ({vix_price})")
        else:
            evidence.append(f"Normal VIX ({vix_price})")

        # 6. Bollinger Bands (breakout / breakdown)
        if bollinger is not None and price > 0:
            upper = bollinger.get("upper", 0)
            lower = bollinger.get("lower", 0)
            if upper > 0 and price > upper:
                scores["breakout"] += 0.2
                evidence.append(f"Price above Bollinger upper ({upper})")
            elif lower > 0 and price < lower:
                scores["breakdown"] += 0.2
                evidence.append(f"Price below Bollinger lower ({lower})")
            else:
                bb_width = (upper - lower) / upper * 100 if upper > 0 else 0
                if bb_width < 5:
                    evidence.append("Bollinger squeeze - potential breakout")

        # 7. Pivot / CPR (breakout / breakdown from pivot)
        if pivot is not None and price > 0:
            p = pivot.get("pivot", 0)
            r1 = pivot.get("r1", 0)
            s1 = pivot.get("s1", 0)
            if p > 0 and price > r1:
                scores["breakout"] += 0.15
                evidence.append(f"Price above R1 ({r1})")
            elif s1 > 0 and price < s1:
                scores["breakdown"] += 0.15
                evidence.append(f"Price below S1 ({s1})")

        # 8. Support/Resistance proximity
        if support_resistance is not None and price > 0:
            resistances = support_resistance.get("resistance", [])
            supports = support_resistance.get("support", [])
            for r in resistances[:2]:
                if abs(price - r) / price < 0.005:
                    scores["breakout"] += 0.05
                    evidence.append(f"Near resistance {r}")
            for s in supports[:2]:
                if abs(price - s) / price < 0.005:
                    scores["breakdown"] += 0.05
                    evidence.append(f"Near support {s}")

        # 9. Options PCR
        if pcr is not None:
            if pcr > 1.3:
                evidence.append(f"Put-heavy PCR ({pcr}) - bearish sentiment")
            elif pcr < 0.8:
                evidence.append(f"Call-heavy PCR ({pcr}) - bullish sentiment")

        # 10. Breadth
        if breadth_positive:
            scores["trend_up"] += 0.05
            evidence.append("Breadth positive")
        else:
            scores["trend_down"] += 0.05
            evidence.append("Breadth negative")

        # 11. Gap
        if gap_up:
            scores["breakout"] += 0.05
            evidence.append("Gap up - potential breakout")
        elif gap_up is False and prev_close > 0 and price < prev_close:
            evidence.append("Gap down risk")

        # 12. Options OI change
        if options_oi_change > 0:
            evidence.append(f"OI increasing ({options_oi_change})")

        # Determine regime
        regime = max(scores, key=scores.get)
        confidence = min(scores[regime] * 100, 95)

        # Trend strength based on ADX
        trend_strength = "STRONG" if (adx or 0) > 25 else "WEAK" if (adx or 0) < 20 else "MODERATE"

        # Momentum
        if scores["trend_up"] > scores["trend_down"] * 1.5:
            momentum = "UP"
        elif scores["trend_down"] > scores["trend_up"] * 1.5:
            momentum = "DOWN"
        else:
            momentum = "NEUTRAL"

        result = {
            "regime": regime,
            "confidence": round(confidence, 1),
            "trend_strength": trend_strength,
            "momentum": momentum,
            "volatility": "HIGH" if vix_price > 20 else "LOW" if vix_price < 13 else "MEDIUM",
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "evidence": evidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._set_cache(cached_key, result)
        return result

    def generate_scenarios(
        self,
        price: float,
        regime: str,
        support_resistance: Optional[dict],
        pivot: Optional[dict],
        confidence: float,
    ) -> list[dict]:
        scenarios = []

        # Primary scenario based on regime
        if regime == "TREND_UP":
            condition = f"Price stays above VWAP and momentum continues"
            confirmation = "NIFTY holds above key support with volume"
            invalidation = "Break below VWAP with decreasing volume"
            target = price * 1.01
        elif regime == "TREND_DOWN":
            condition = "Price continues lower with negative momentum"
            confirmation = "NIFTY breaks below key support"
            invalidation = "Price bounces above VWAP"
            target = price * 0.99
        elif regime == "BREAKOUT":
            condition = "Price breaks above resistance with volume"
            confirmation = "Sustained move above resistance level"
            invalidation = "Rejection at resistance, close below"
            target = price * 1.015 if price > 0 else price
        elif regime == "BREAKDOWN":
            condition = "Price breaks below support"
            confirmation = "Sustained move below support level"
            invalidation = "Bounce back above support"
            target = price * 0.985 if price > 0 else price
        else:
            condition = "Price remains in range"
            confirmation = "No clear breakout direction"
            invalidation = "Break of range boundaries"
            target = price

        scenarios.append({
            "type": "PRIMARY",
            "condition": condition,
            "confirmation": confirmation,
            "invalidation": invalidation,
            "target": round(target, 2) if price > 0 else 0,
        })

        # Alternative scenario
        if regime in ("TREND_UP", "BREAKOUT"):
            alt_condition = "Price pulls back to VWAP or nearest support"
            alt_target = price * 0.995 if price > 0 else price
        elif regime in ("TREND_DOWN", "BREAKDOWN"):
            alt_condition = "Price rebounds to VWAP or nearest resistance"
            alt_target = price * 1.005 if price > 0 else price
        else:
            alt_condition = "Range continues between support and resistance"
            alt_target = price

        scenarios.append({
            "type": "ALTERNATIVE",
            "condition": alt_condition,
            "confirmation": "Pullback holds key level",
            "invalidation": "Break of alternative level",
            "target": round(alt_target, 2) if price > 0 else 0,
        })

        # Risk / Invalidation scenario
        sr = support_resistance or {}
        supports = sr.get("support", [])
        resistances = sr.get("resistance", [])

        if supports and price > 0:
            risk_level = supports[0] if supports else 0
        elif resistances and price > 0:
            risk_level = resistances[0] if resistances else 0
        else:
            risk_level = price * 0.98

        scenarios.append({
            "type": "RISK / INVALIDATION",
            "condition": f"NIFTY breaks below {risk_level} and remains there",
            "confirmation": "Close below support with volume",
            "invalidation": "Bounce back above support",
            "target": round(risk_level, 2),
        })

        return scenarios


market_regime_engine = MarketRegimeEngine()