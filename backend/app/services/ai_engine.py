from __future__ import annotations

import logging
import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.market import MarketOverview, MarketQuote, VIXQuote
from app.models.db import AISignal, Scenario
from app.repositories.market import MarketRepository
from app.services.market_regime import market_regime_engine

logger = logging.getLogger("tradingai.ai")


class AIEngine:
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

    async def analyze_market(
        self, session: AsyncSession, overview: MarketOverview
    ) -> dict:
        cached = self._cached("market_analysis")
        if cached:
            return cached

        nifty = overview.nifty
        vix = overview.vix
        banknifty = overview.banknifty

        reasons_bullish = []
        reasons_bearish = []
        warnings = []

        # Trend analysis
        nifty_change = nifty.change_pct
        banknifty_change = banknifty.change_pct

        if nifty_change > 0.5:
            trend = "BULLISH"
            confidence = min(80 + nifty_change * 5, 95)
            reasons_bullish.append(f"NIFTY up {nifty_change:.2f}%")
        elif nifty_change < -0.5:
            trend = "BEARISH"
            confidence = min(80 + abs(nifty_change) * 5, 95)
            reasons_bearish.append(f"NIFTY down {abs(nifty_change):.2f}%")
        else:
            trend = "NEUTRAL"
            confidence = 55
            reasons_bullish.append("NIFTY flat")

        # BankNifty confirmation
        if banknifty_change > 0.3:
            reasons_bullish.append("BankNifty confirming")
        elif banknifty_change < -0.3:
            reasons_bearish.append("BankNifty weakening")
            warnings.append("BankNifty momentum weakening")

        # VIX analysis
        if vix.price < 13:
            reasons_bullish.append("Low VIX indicates calm")
        elif vix.price > 20:
            reasons_bearish.append("High VIX indicates fear")
            warnings.append("Elevated VIX")

        if vix.trend == "Declining":
            reasons_bullish.append("VIX declining - reduced fear")
        elif vix.trend == "Rising":
            reasons_bearish.append("VIX rising - increased fear")
            warnings.append("VIX rising sharply")

        # PCR analysis
        pcr = overview.global_markets.get("pcr") if overview.global_markets else None
        if pcr:
            if isinstance(pcr, dict):
                pcr_val = pcr.get("value", 0)
                if pcr_val > 1.3:
                    reasons_bullish.append("Put-heavy - bearish sentiment")
                elif pcr_val < 0.8:
                    reasons_bullish.append("Call-heavy - bullish sentiment")

        # Market status
        if overview.market_status == "Open":
            reasons_bullish.append("Market status: Open")
        else:
            warnings.append("Market closed")

        # Breadth (simplified)
        reasons_bullish.append("Breadth positive")

        # Options sentiment
        options_sentiment = "NEUTRAL"
        if reasons_bullish and len(reasons_bullish) > len(reasons_bearish):
            options_sentiment = "BULLISH"
        elif reasons_bearish and len(reasons_bearish) > len(reasons_bullish):
            options_sentiment = "BEARISH"

        analysis = {
            "trend": trend,
            "confidence": round(confidence, 1),
            "market_view": trend,
            "reasons_bullish": reasons_bullish,
            "reasons_bearish": reasons_bearish,
            "warnings": warnings,
            "options_sentiment": options_sentiment,
            "vix_level": vix.price,
            "regime": trend,
            "momentum": "UP" if nifty_change > 0 else "DOWN" if nifty_change < 0 else "FLAT",
            "volatility": "LOW" if vix.price < 15 else "HIGH" if vix.price > 20 else "MEDIUM",
            "breadth": "POSITIVE",
            "view_invalidation": [
                "NIFTY below VWAP",
                "Break below 25,000",
                "VIX rises sharply",
                "Breadth turns negative",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

        self._set_cache("market_analysis", analysis)

        # Persist to DB
        try:
            repo = MarketRepository(session)
            signal = AISignal(
                symbol="NIFTY", regime=trend, trend=trend,
                momentum=analysis["momentum"], volatility=analysis["volatility"],
                breadth="POSITIVE", options_sentiment=options_sentiment,
                confidence=confidence,
                reasons_bullish=json.dumps(reasons_bullish),
                reasons_bearish=json.dumps(reasons_bearish),
                warnings=json.dumps(warnings),
                view_invalidation=json.dumps(analysis["view_invalidation"]),
                timestamp=datetime.utcnow(),
            )
            session.add(signal)
            await session.commit()
        except Exception as e:
            logger.error(f"AI signal save error: {e}")

        return analysis

    async def analyze_with_regime(
        self, session: AsyncSession, overview: MarketOverview, indicators: Optional[dict] = None
    ) -> dict:
        cached = self._cached("market_analysis_regime")
        if cached:
            return cached

        nifty = overview.nifty
        vix = overview.vix

        # Use regime engine for structured analysis
        vwap = indicators.get("vwap", 0) if indicators else 0
        rsi = indicators.get("rsi") if indicators else None
        macd = indicators.get("macd") if indicators else None
        adx = indicators.get("adx") if indicators else None
        bollinger = indicators.get("bollinger_bands") if indicators else None
        pivot = indicators.get("pivot") if indicators else None
        support_resistance = indicators.get("support_resistance") if indicators else None

        regime = market_regime_engine.evaluate(
            price=nifty.price,
            vwap=vwap,
            prev_close=nifty.previous_close,
            rsi=rsi,
            macd=macd,
            adx=adx,
            vix_price=vix.price,
            bollinger=bollinger,
            pivot=pivot,
            support_resistance=support_resistance,
            breadth_positive=True,
        )

        # Generate scenarios based on regime
        scenarios = market_regime_engine.generate_scenarios(
            price=nifty.price,
            regime=regime["regime"],
            support_resistance=support_resistance,
            pivot=pivot,
            confidence=regime["confidence"],
        )

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "market_regime": regime["regime"],
            "confidence": regime["confidence"],
            "market_bias": "BULLISH" if regime["scores"]["trend_up"] > regime["scores"]["trend_down"] else "BEARISH" if regime["scores"]["trend_down"] > regime["scores"]["trend_up"] else "NEUTRAL",
            "summary": self._generate_summary(regime, vix, nifty),
            "nifty": {
                "spot": nifty.price,
                "support": support_resistance.get("support", []) if support_resistance else [],
                "resistance": support_resistance.get("resistance", []) if support_resistance else [],
                "trend": regime["regime"],
            },
            "regime": {
                "type": regime["regime"],
                "confidence": regime["confidence"],
                "trend_strength": regime["trend_strength"],
                "momentum": regime["momentum"],
                "volatility": regime["volatility"],
            },
            "evidence": regime["evidence"],
            "primary_scenario": scenarios[0] if scenarios else {},
            "alternative_scenario": scenarios[1] if len(scenarios) > 1 else {},
            "risk_scenario": scenarios[2] if len(scenarios) > 2 else {},
            "strategy_classes": self._get_strategy_classes(regime["regime"]),
            "risk_flags": self._get_risk_flags(regime, vix),
        }

        self._set_cache("market_analysis_regime", result)

        # Persist to DB
        try:
            signal = AISignal(
                symbol="NIFTY", regime=regime["regime"], trend=regime["momentum"],
                momentum=regime["momentum"], volatility=regime["volatility"],
                breadth="POSITIVE", options_sentiment="NEUTRAL",
                confidence=regime["confidence"],
                reasons_bullish=json.dumps([e for e in regime["evidence"] if "bullish" in e.lower() or "up" in e.lower() or "positive" in e.lower()]),
                reasons_bearish=json.dumps([e for e in regime["evidence"] if "bearish" in e.lower() or "down" in e.lower() or "negative" in e.lower()]),
                warnings=json.dumps(warnings),
                view_invalidation=json.dumps([s.get("invalidation", "") for s in scenarios]),
                timestamp=datetime.utcnow(),
            )
            session.add(signal)
            for s in scenarios:
                scenario = Scenario(
                    symbol="NIFTY", condition=s.get("condition", ""),
                    scenario_type=s.get("type", ""), probability=0,
                    description=s.get("condition", ""),
                    timestamp=datetime.utcnow(),
                )
                session.add(scenario)
            await session.commit()
        except Exception as e:
            logger.error(f"AI signal/scenario save error: {e}")

        return result

    def _generate_summary(self, regime: dict, vix: VIXQuote, nifty: MarketQuote) -> str:
        lines = [
            f"The current market structure shows {regime['regime'].lower()} with {regime['confidence']}% confidence.",
            f"NIFTY is trading at {nifty.price:.2f} with {nifty.change_pct:+.2f}% change.",
            f"VIX at {vix.price:.2f} indicates {'elevated' if vix.price > 20 else 'low' if vix.price < 13 else 'moderate'} volatility.",
        ]
        for ev in regime["evidence"][:5]:
            lines.append(f"• {ev}")
        return "\n".join(lines)

    def _get_strategy_classes(self, regime: str) -> list[str]:
        mapping = {
            "TREND_UP": ["Bull Call Spread", "Bull Put Spread", "Covered Call"],
            "TREND_DOWN": ["Bear Put Spread", "Bear Call Spread", "Protective Put"],
            "RANGE": ["Iron Condor", "Short Strangle", "Butterfly Spread"],
            "BREAKOUT": ["Long Call", "Long Straddle", "Bull Call Spread"],
            "BREAKDOWN": ["Long Put", "Long Straddle", "Bear Put Spread"],
            "HIGH_VOLATILITY": ["Defined-risk structures", "Avoid naked exposure"],
            "LOW_VOLATILITY": ["Long Straddle", "Long Strangle"],
            "OPENING_VOLATILITY": ["Wait for stabilization", "Defined-risk only"],
        }
        return mapping.get(regime, ["Neutral strategies"])

    def _get_risk_flags(self, regime: dict, vix: VIXQuote) -> list[str]:
        flags = []
        if regime["volatility"] == "HIGH":
            flags.append("Elevated volatility - reduce position size")
        if vix.price > 25:
            flags.append("VIX above 25 - risk-off conditions")
        if regime["confidence"] < 60:
            flags.append("Low confidence - avoid new positions")
        return flags

    async def generate_scenarios(
        self, session: AsyncSession, overview: MarketOverview
    ) -> list[dict]:
        cached = self._cached("scenarios")
        if cached:
            return cached

        nifty = overview.nifty
        price = nifty.price

        scenarios = [
            {
                "symbol": "NIFTY",
                "condition": f"price > {price + 200:.0f}",
                "scenario_type": "continuation",
                "probability": 40,
                "description": "Bullish continuation - price breaks above resistance, momentum sustains",
            },
            {
                "symbol": "NIFTY",
                "condition": f"{price - 200:.0f} <= price <= {price + 200:.0f}",
                "scenario_type": "range",
                "probability": 45,
                "description": "Range-bound - consolidation between support and resistance, wait for breakout",
            },
            {
                "symbol": "NIFTY",
                "condition": f"price < {price - 200:.0f}",
                "scenario_type": "reversal",
                "probability": 15,
                "description": "Bearish scenario - breakdown below support, risk-off sentiment",
            },
        ]

        # Persist to DB
        try:
            for s in scenarios:
                scenario = Scenario(
                    symbol=s["symbol"], condition=s["condition"],
                    scenario_type=s["scenario_type"], probability=s["probability"],
                    description=s["description"],
                    timestamp=datetime.utcnow(),
                )
                session.add(scenario)
            await session.commit()
        except Exception as e:
            logger.error(f"Scenario save error: {e}")

        self._set_cache("scenarios", scenarios)
        return scenarios

    async def get_ai_signals(
        self, session: AsyncSession, symbol: Optional[str] = None
    ) -> list[dict]:
        query = select(AISignal).where(AISignal.is_active == True)
        if symbol:
            query = query.where(AISignal.symbol == symbol)
        query = query.order_by(desc(AISignal.timestamp)).limit(10)
        result = await session.execute(query)
        signals = result.scalars().all()
        return [
            {
                "symbol": s.symbol,
                "regime": s.regime,
                "trend": s.trend,
                "momentum": s.momentum,
                "volatility": s.volatility,
                "breadth": s.breadth,
                "options_sentiment": s.options_sentiment,
                "confidence": s.confidence,
                "reasons_bullish": json.loads(s.reasons_bullish) if s.reasons_bullish else [],
                "reasons_bearish": json.loads(s.reasons_bearish) if s.reasons_bearish else [],
                "warnings": json.loads(s.warnings) if s.warnings else [],
                "view_invalidation": json.loads(s.view_invalidation) if s.view_invalidation else [],
                "timestamp": s.timestamp.isoformat() if s.timestamp else "",
            }
            for s in signals
        ]


ai_engine = AIEngine()