from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("tradingai.strategy")


class StrategyEngine:
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

    def select_strategy(self, analysis: dict) -> dict:
        cached_key = f"strategy:{analysis.get('asset', '')}:{analysis.get('market_regime', '')}"
        cached = self._cached(cached_key)
        if cached:
            return cached

        regime = analysis.get("market_regime", "UNCONFIRMED")
        confidence = analysis.get("confidence", 50)
        directional_bias = analysis.get("directional_bias", "NEUTRAL")
        rsi = analysis.get("momentum_analysis", "")
        trend = analysis.get("trend_analysis", "")
        support_levels = analysis.get("support_levels", [])
        resistance_levels = analysis.get("resistance_levels", [])
        expected_move = analysis.get("expected_move", "")

        strategies = []
        alternative_strategies = []
        intraday_plan = []
        no_trade_conditions = analysis.get("no_trade_conditions", [])

        if regime == "TRENDING BULLISH":
            strategies = [
                {
                    "strategy": "Bull Call Spread",
                    "market_condition": "Bullish trend with momentum",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "BUY ATM CALL",
                        "SELL 1-2 strikes OTM CALL",
                    ],
                    "entry_trigger": "Price above VWAP with RSI < 70",
                    "maximum_profit": "Strike width - premium paid",
                    "maximum_loss": "Premium paid + transaction costs",
                    "breakeven": "Lower strike + premium paid",
                    "stop_loss": "Below lower strike",
                    "target": "Upper strike at expiry",
                    "adjustment": "Roll up both legs if price continues higher",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
                {
                    "strategy": "Bull Put Spread",
                    "market_condition": "Bullish trend with moderate volatility",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "SELL OTM PUT",
                        "BUY further OTM PUT",
                    ],
                    "entry_trigger": "Price above VWAP with RSI < 70",
                    "maximum_profit": "Premium received",
                    "maximum_loss": "Strike width - premium received",
                    "breakeven": "Higher strike - premium received",
                    "stop_loss": "Below lower strike",
                    "target": "Expiry out-of-the-money",
                    "adjustment": "Roll down both legs if price declines",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
            ]
            alternative_strategies = [
                "Long Call",
                "Call Ratio Spread",
            ]
        elif regime == "TRENDING BEARISH":
            strategies = [
                {
                    "strategy": "Bear Put Spread",
                    "market_condition": "Bearish trend with momentum",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "BUY ATM PUT",
                        "SELL 1-2 strikes OTM PUT",
                    ],
                    "entry_trigger": "Price below VWAP with RSI > 30",
                    "maximum_profit": "Strike width - premium paid",
                    "maximum_loss": "Premium paid + transaction costs",
                    "breakeven": "Higher strike - premium paid",
                    "stop_loss": "Above higher strike",
                    "target": "Lower strike at expiry",
                    "adjustment": "Roll down both legs if price continues lower",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
                {
                    "strategy": "Bear Call Spread",
                    "market_condition": "Bearish trend with moderate volatility",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "SELL OTM CALL",
                        "BUY further OTM CALL",
                    ],
                    "entry_trigger": "Price below VWAP with RSI > 30",
                    "maximum_profit": "Premium received",
                    "maximum_loss": "Strike width - premium received",
                    "breakeven": "Lower strike + premium received",
                    "stop_loss": "Above higher strike",
                    "target": "Expiry out-of-the-money",
                    "adjustment": "Roll up both legs if price rises",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
            ]
            alternative_strategies = [
                "Long Put",
                "Put Ratio Spread",
            ]
        elif regime == "RANGE BOUND":
            strategies = [
                {
                    "strategy": "Iron Condor",
                    "market_condition": "Range-bound with low volatility",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "SELL OTM CALL",
                        "BUY further OTM CALL",
                        "SELL OTM PUT",
                        "BUY further OTM PUT",
                    ],
                    "entry_trigger": "Price between support and resistance",
                    "maximum_profit": "Premium received",
                    "maximum_loss": "Strike width - premium received",
                    "breakeven": "Higher strike ± premium received",
                    "stop_loss": "Breakout above resistance or breakdown below support",
                    "target": "Expiry out-of-the-money",
                    "adjustment": "Roll both sides if price approaches a wing",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
                {
                    "strategy": "Butterfly Spread",
                    "market_condition": "Range-bound with expected low volatility",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "BUY 1 ATM Call",
                        "SELL 2 ATM Calls",
                        "BUY 1 further OTM Call",
                    ],
                    "entry_trigger": "Price between support and resistance",
                    "maximum_profit": "Strike width - net premium paid",
                    "maximum_loss": "Net premium paid + transaction costs",
                    "breakeven": "Lower strike + premium paid / Higher strike - premium paid",
                    "stop_loss": "Breakout above resistance or breakdown below support",
                    "target": "At ATM strike at expiry",
                    "adjustment": "Roll to new ATM strike if price moves",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
            ]
            alternative_strategies = [
                "Short Strangle",
                "Iron Fly",
            ]
        elif regime == "BREAKOUT":
            strategies = [
                {
                    "strategy": "Long Straddle",
                    "market_condition": "Expected breakout with high volatility",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "BUY ATM CALL",
                        "BUY ATM PUT",
                    ],
                    "entry_trigger": "Price at support/resistance with high volume",
                    "maximum_profit": "Unlimited",
                    "maximum_loss": "Premium paid + transaction costs",
                    "breakeven": "ATM strike ± premium paid",
                    "stop_loss": "Time decay",
                    "target": "Breakout direction x 2",
                    "adjustment": "Roll to new ATM strike if price moves",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
                {
                    "strategy": "Long Strangle",
                    "market_condition": "Expected breakout with high volatility",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "BUY OTM CALL",
                        "BUY OTM PUT",
                    ],
                    "entry_trigger": "Price at support/resistance with high volume",
                    "maximum_profit": "Unlimited",
                    "maximum_loss": "Premium paid + transaction costs",
                    "breakeven": "OTM strike ± premium paid",
                    "stop_loss": "Time decay",
                    "target": "Breakout direction x 2",
                    "adjustment": "Roll to new OTM strike if price moves",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
            ]
            alternative_strategies = [
                "Long Call",
                "Long Put",
            ]
        elif regime == "HIGH VOLATILITY":
            strategies = [
                {
                    "strategy": "Defined-risk premium selling",
                    "market_condition": "High IV - sell premium with defined risk",
                    "expiry": "NEXT_WEEKLY",
                    "legs": [
                        "SELL OTM PUT Spread",
                        "SELL OTM CALL Spread",
                    ],
                    "entry_trigger": "High IV with range-bound price",
                    "maximum_profit": "Premium received",
                    "maximum_loss": "Strike width - premium received",
                    "breakeven": "Higher strike ± premium received",
                    "stop_loss": "Breakout above resistance or breakdown below support",
                    "target": "Expiry out-of-the-money",
                    "adjustment": "Roll both sides if price approaches a wing",
                    "exit": "At expiry or when target is reached",
                    "time_based_exit": "30 minutes before expiry",
                },
            ]
            alternative_strategies = [
                "Iron Condor",
                "Butterfly Spread",
            ]
        else:
            strategies = [
                {
                    "strategy": "NO TRADE",
                    "market_condition": "Unclear market conditions",
                    "expiry": "N/A",
                    "legs": [],
                    "entry_trigger": "Wait for clear signal",
                    "maximum_profit": "N/A",
                    "maximum_loss": "N/A",
                    "breakeven": "N/A",
                    "stop_loss": "N/A",
                    "target": "N/A",
                    "adjustment": "N/A",
                    "exit": "N/A",
                    "time_based_exit": "N/A",
                },
            ]
            no_trade_conditions = [
                "Conflicting indicators",
                "Unclear direction",
                "Low liquidity",
                "Very wide bid/ask spread",
                "Extreme volatility",
                "Price trapped between major levels",
                "Insufficient expected move relative to option premium",
            ]

        result = {
            "asset": analysis.get("asset", ""),
            "date": analysis.get("date", ""),
            "market_regime": regime,
            "directional_bias": directional_bias,
            "confidence": confidence,
            "strategies": strategies,
            "alternative_strategies": alternative_strategies,
            "intraday_plan": self._generate_intraday_plan(support_levels, resistance_levels, regime),
            "no_trade_conditions": no_trade_conditions,
            "risk_warnings": [
                "This is analytical decision-support output, not a guaranteed trading signal",
                "Do not enter trades solely based on the opening gap",
                "Every strategy must have an explicit invalidation condition",
            ],
            "data_quality": analysis.get("data_quality", "UNKNOWN"),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        self._set_cache(cached_key, result)
        return result

    def _generate_intraday_plan(
        self,
        support_levels: list[float],
        resistance_levels: list[float],
        regime: str,
    ) -> list[dict]:
        plan = []

        if support_levels and resistance_levels:
            plan.append({
                "time": "09:15 - 09:30",
                "action": "OBSERVE",
                "description": "Watch opening price action and volume",
                "invalidation": "None",
            })
            plan.append({
                "time": "09:30 - 10:00",
                "action": "ASSESS",
                "description": f"Price near support ({support_levels[-1]:.2f}) or resistance ({resistance_levels[0]:.2f})",
                "invalidation": "Breakout above resistance or breakdown below support",
            })
            plan.append({
                "time": "10:00 - 11:30",
                "action": "TRADE",
                "description": "Enter trade based on breakout/breakdown",
                "invalidation": "Price returns to range",
            })
            plan.append({
                "time": "11:30 - 13:30",
                "action": "MANAGE",
                "description": "Monitor and adjust positions",
                "invalidation": "Stop-loss hit or target reached",
            })
            plan.append({
                "time": "13:30 - 15:00",
                "action": "CLOSE",
                "description": "Close positions before market close",
                "invalidation": "None",
            })
        else:
            plan.append({
                "time": "09:15 - 15:00",
                "action": "NO TRADE",
                "description": "Insufficient data for intraday plan",
                "invalidation": "None",
            })

        return plan


strategy_engine = StrategyEngine()