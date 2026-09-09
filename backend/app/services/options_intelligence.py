from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("tradingai.options")


class OptionsIntelligence:
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

    def calculate_pcr(
        self, call_oi: float, put_oi: float
    ) -> float:
        if call_oi == 0:
            return 0.0
        return round(put_oi / call_oi, 3)

    def calculate_max_pain(
        self, contracts: list[dict]
    ) -> dict[str, Any]:
        pain_map: dict[float, float] = defaultdict(float)
        for c in contracts:
            strike = c.get("strike", 0)
            oi = c.get("open_interest", 0)
            opt_type = c.get("option_type", "CE")
            if strike > 0 and oi > 0:
                pain_map[strike] += oi

        if not pain_map:
            return {"max_pain": 0, "call_max_oi_strike": 0, "put_max_oi_strike": 0}

        max_pain_strike = max(pain_map, key=pain_map.get)

        call_oi_by_strike: dict[float, float] = defaultdict(float)
        put_oi_by_strike: dict[float, float] = defaultdict(float)
        for c in contracts:
            strike = c.get("strike", 0)
            oi = c.get("open_interest", 0)
            opt_type = c.get("option_type", "CE")
            if opt_type == "CE":
                call_oi_by_strike[strike] += oi
            else:
                put_oi_by_strike[strike] += oi

        call_max_oi = max(call_oi_by_strike, key=call_oi_by_strike.get) if call_oi_by_strike else 0
        put_max_oi = max(put_oi_by_strike, key=put_oi_by_strike.get) if put_oi_by_strike else 0

        return {
            "max_pain": max_pain_strike,
            "call_max_oi_strike": call_max_oi,
            "put_max_oi_strike": put_max_oi,
        }

    def calculate_iv_stats(
        self, contracts: list[dict]
    ) -> dict[str, Any]:
        ivs = [c.get("implied_volatility", 0) for c in contracts if c.get("implied_volatility")]
        if not ivs:
            return {"avg_iv": 0, "min_iv": 0, "max_iv": 0, "iv_rank": 0}
        avg_iv = sum(ivs) / len(ivs)
        min_iv = min(ivs)
        max_iv = max(ivs)
        iv_rank = ((avg_iv - min_iv) / (max_iv - min_iv) * 100) if max_iv > min_iv else 50
        return {
            "avg_iv": round(avg_iv, 2),
            "min_iv": round(min_iv, 2),
            "max_iv": round(max_iv, 2),
            "iv_rank": round(iv_rank, 1),
        }

    def analyze_weekly_options(
        self, contracts: list[dict], underlying_price: float
    ) -> dict[str, Any]:
        call_oi_total = sum(
            c.get("open_interest", 0)
            for c in contracts
            if c.get("option_type") == "CE"
        )
        put_oi_total = sum(
            c.get("open_interest", 0)
            for c in contracts
            if c.get("option_type") == "PE"
        )

        pcr = self.calculate_pcr(call_oi_total, put_oi_total)
        max_pain = self.calculate_max_pain(contracts)
        iv_stats = self.calculate_iv_stats(contracts)

        environment = self._classify_environment(
            pcr=pcr,
            iv_stats=iv_stats,
            underlying_price=underlying_price,
            max_pain=max_pain,
        )

        strategy_classes = self._get_strategy_classes(environment)

        return {
            "pcr": pcr,
            "call_oi": call_oi_total,
            "put_oi": put_oi_total,
            "max_pain": max_pain,
            "iv_stats": iv_stats,
            "environment": environment,
            "strategy_classes": strategy_classes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _classify_environment(
        self,
        pcr: float,
        iv_stats: dict,
        underlying_price: float,
        max_pain: dict,
    ) -> str:
        if iv_stats.get("iv_rank", 0) > 70:
            return "HIGH_VOLATILITY"
        if pcr > 1.5:
            return "BEARISH"
        if pcr < 0.7:
            return "BULLISH"
        if underlying_price > 0 and max_pain.get("max_pain", 0) > 0:
            diff = abs(underlying_price - max_pain["max_pain"]) / underlying_price * 100
            if diff < 1:
                return "RANGE"
        return "NEUTRAL"

    def _get_strategy_classes(self, environment: str) -> list[str]:
        mapping = {
            "BULLISH": ["Bull Call Spread", "Bull Put Spread", "Covered Call"],
            "BEARISH": ["Bear Put Spread", "Bear Call Spread", "Protective Put"],
            "RANGE": ["Iron Condor", "Short Strangle", "Butterfly Spread"],
            "HIGH_VOLATILITY": ["Defined-risk structures", "Avoid naked exposure"],
            "LOW_VOLATILITY": ["Long Straddle", "Long Strangle"],
            "NEUTRAL": ["Iron Condor", "Butterfly Spread"],
        }
        return mapping.get(environment, ["Neutral strategies"])

    async def get_options_intelligence(
        self,
        contracts: list[dict],
        underlying_price: float,
        symbol: str = "NIFTY",
    ) -> dict:
        cached_key = f"options:{symbol}:{underlying_price}"
        cached = self._cached(cached_key)
        if cached:
            return cached

        result = self.analyze_weekly_options(contracts, underlying_price)
        result["symbol"] = symbol
        self._set_cache(cached_key, result)
        return result