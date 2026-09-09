from __future__ import annotations

import logging
import json
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.market import MarketQuote, VIXQuote, MarketOverview

logger = logging.getLogger("tradingai.ai")

MASTER_PROMPT = """You are TradingAI's Daily Market Analysis and Options Strategy Engine.

Your task is to analyze ONE Indian index or F&O stock using the supplied market data and generate a structured intraday market outlook and options-strategy analysis for today's trading session.

You must analyze the data objectively.

Do NOT assume that the market must go bullish or bearish.

Do NOT manufacture missing data.

If important data is unavailable, explicitly state "DATA UNAVAILABLE" and reduce confidence accordingly.

The objective is not to predict the market with certainty. The objective is to identify the current market regime, important levels, probable scenarios, suitable option strategies, invalidation levels, risk conditions and trade-management rules.

Asset: {asset}
Yahoo Finance Symbol: {symbol}
Asset Type: {asset_type}
Date: {date}
Current Price: {current_price}
Previous Close: {previous_close}
Today's Open: {open}
Today's High: {high}
Today's Low: {low}
Gap %: {gap_pct}
Day Change %: {day_change_pct}
EMA20: {ema20}
EMA50: {ema50}
EMA100: {ema100}
EMA200: {ema200}
RSI: {rsi}
MACD: {macd}
ATR: {atr}
ADX: {adx}
VWAP: {vwap}
Bollinger Bands: {bollinger}
Pivot: {pivot}
CPR: {cpr}
Support Levels: {support_levels}
Resistance Levels: {resistance_levels}
India VIX: {vix}
Market Regime: {regime}

Analyze the asset using the following sequence:

MARKET REGIME: Determine whether the current market is primarily TRENDING BULLISH, TRENDING BEARISH, RANGE BOUND, HIGH VOLATILITY, LOW VOLATILITY, BREAKOUT, BREAKDOWN, REVERSAL, or UNCONFIRMED. Explain the evidence.

TREND: Determine short-term trend, intraday trend, swing trend. Compare price against EMA20, EMA50, EMA200 and VWAP.

MOMENTUM: Analyze RSI, MACD, ADX, Volume, Relative volume. Identify whether momentum confirms or contradicts price direction.

SUPPORT AND RESISTANCE: Identify the most important immediate support, major support, immediate resistance, major resistance using price structure, CPR, pivots and option OI.

OPTIONS STRUCTURE: Analyze PCR, Call OI, Put OI, OI buildup, OI unwinding, IV, ATM options, Important strikes, Expected move. Identify where option positioning suggests potential support/resistance.

MARKET SCENARIOS: Create three scenarios: BULLISH SCENARIO, BEARISH SCENARIO, RANGE/NEUTRAL SCENARIO. For each scenario provide: Trigger, Confirmation, Important level, Invalidation, Potential objective.

OPTIONS STRATEGY SELECTION: Select suitable strategies based on the market regime. Potential strategies include: Bull Call Spread, Bull Put Spread, Bear Put Spread, Bear Call Spread, Long Call, Long Put, Call Ratio Spread, Put Ratio Spread, Iron Condor, Iron Fly, Long Straddle, Long Strangle, Short Straddle, Short Strangle, Calendar Spread, Diagonal Spread, Defined-risk credit spreads, Defined-risk debit spreads. Only recommend a strategy if the current market conditions logically support it. Avoid naked/unlimited-risk strategies unless the user explicitly enables them.

STRATEGY PARAMETERS: For each suitable strategy provide: Strategy name, Market view, Expiry, Suggested strikes, Approximate entry conditions, Maximum profit, Maximum loss, Breakeven, Risk/reward, Adjustment trigger, Stop-loss/invalidation, Profit-taking condition, Exit condition, Time-based exit.

INTRADAY SETUP: Provide opening bias, Important opening levels, First 15-minute interpretation, Breakout trigger, Breakdown trigger, Range condition, No-trade condition.

TRADE MANAGEMENT: Define entry trigger, Confirmation, Stop-loss, First target, Second target, Trailing method, Exit condition. The strategy must have an explicit invalidation condition.

NO-TRADE CONDITIONS: Identify situations where an options trader should avoid opening a new position, such as: Low liquidity, Very wide bid/ask spread, Unclear direction, Extreme volatility, Major event risk, Conflicting indicators, Price trapped between major levels, Insufficient expected move relative to option premium.

Return valid JSON only. Use exactly this structure:
{{
  "asset": "",
  "date": "",
  "market_regime": "",
  "directional_bias": "",
  "confidence": 0,
  "market_summary": "",
  "trend_analysis": "",
  "momentum_analysis": "",
  "support_levels": [],
  "resistance_levels": [],
  "options_analysis": "",
  "expected_move": "",
  "bullish_scenario": {{"trigger": "", "confirmation": "", "target": "", "invalidation": ""}},
  "bearish_scenario": {{"trigger": "", "confirmation": "", "target": "", "invalidation": ""}},
  "range_scenario": {{"condition": "", "strategy_environment": "", "invalidation": ""}},
  "primary_strategy": {{"strategy": "", "market_condition": "", "expiry": "", "legs": [], "entry_trigger": "", "maximum_profit": "", "maximum_loss": "", "breakeven": "", "stop_loss": "", "target": "", "adjustment": "", "exit": ""}},
  "alternative_strategies": [],
  "intraday_plan": [],
  "no_trade_conditions": [],
  "risk_warnings": [],
  "data_quality": "",
  "last_updated": ""
}}

Never guarantee profit. Never describe a trade as certain. Never invent missing market or option-chain data. Never fabricate option premiums. Prefer defined-risk strategies. Clearly distinguish market analysis from trade execution. If signals conflict, say so. If conditions are unclear, the correct output may be NO TRADE. Confidence must represent the strength and consistency of the supplied signals, not probability of profit. Use current supplied data rather than assumptions. Every strategy must have an invalidation condition. Consider liquidity and bid/ask spread before selecting an option. Consider expiry and time decay. Consider IV before recommending option buying or option selling. Consider transaction costs and slippage for intraday strategies. Never use future information in the analysis. Do not use historical backtest results as if they predict today's outcome. The final result is an analytical decision-support output, not a guaranteed trading signal."""


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

    def generate_daily_analysis(self, symbol: str, data: dict) -> dict:
        cached = self._cached(f"daily_analysis:{symbol}")
        if cached:
            return cached

        asset_type = "INDEX" if symbol in ["NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY"] else "STOCK"
        current_price = data.get("current_price", 0)
        previous_close = data.get("previous_close", 0)
        open_price = data.get("open", 0)
        high = data.get("high", 0)
        low = data.get("low", 0)
        gap_pct = data.get("gap_pct", 0)
        day_change_pct = data.get("day_change_pct", 0)
        ema20 = data.get("ema20")
        ema50 = data.get("ema50")
        ema100 = data.get("ema100")
        ema200 = data.get("ema200")
        rsi = data.get("rsi")
        macd = data.get("macd")
        atr = data.get("atr")
        adx = data.get("adx")
        vwap = data.get("vwap")
        bollinger = data.get("bollinger_bands")
        pivot = data.get("pivot")
        cpr = data.get("cpr")
        support_levels = data.get("support_resistance", {}).get("support", [])
        resistance_levels = data.get("support_resistance", {}).get("resistance", [])
        vix_price = data.get("vix_price", 0)
        regime = data.get("regime", "UNCONFIRMED")

        prompt = MASTER_PROMPT.format(
            asset=symbol,
            symbol=f"^{symbol}" if symbol in ["NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY"] else f"{symbol}.NS",
            asset_type=asset_type,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            current_price=current_price,
            previous_close=previous_close,
            open=open_price,
            high=high,
            low=low,
            gap_pct=round(gap_pct, 2),
            day_change_pct=round(day_change_pct, 2),
            ema20=ema20 if ema20 else "DATA UNAVAILABLE",
            ema50=ema50 if ema50 else "DATA UNAVAILABLE",
            ema100=ema100 if ema100 else "DATA UNAVAILABLE",
            ema200=ema200 if ema200 else "DATA UNAVAILABLE",
            rsi=round(rsi, 2) if rsi else "DATA UNAVAILABLE",
            macd=f"MACD: {macd['macd']}, Signal: {macd['signal']}" if macd else "DATA UNAVAILABLE",
            atr=atr if atr else "DATA UNAVAILABLE",
            adx=round(adx, 2) if adx else "DATA UNAVAILABLE",
            vwap=vwap if vwap else "DATA UNAVAILABLE",
            bollinger=f"Upper: {bollinger['upper']}, Middle: {bollinger['middle']}, Lower: {bollinger['lower']}" if bollinger else "DATA UNAVAILABLE",
            pivot=f"Pivot: {pivot['pivot']}, R1: {pivot['r1']}, S1: {pivot['s1']}, R2: {pivot['r2']}, S2: {pivot['s2']}" if pivot else "DATA UNAVAILABLE",
            cpr=f"Pivot: {cpr['pivot']}, BC: {cpr['bc']}, TC: {cpr['tc']}" if cpr else "DATA UNAVAILABLE",
            support_levels=", ".join(str(s) for s in support_levels) if support_levels else "DATA UNAVAILABLE",
            resistance_levels=", ".join(str(r) for r in resistance_levels) if resistance_levels else "DATA UNAVAILABLE",
            vix=vix_price if vix_price else "DATA UNAVAILABLE",
            regime=regime,
        )

        analysis = {
            "asset": symbol,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "market_regime": regime,
            "directional_bias": "BULLISH" if day_change_pct > 0 else "BEARISH" if day_change_pct < 0 else "NEUTRAL",
            "confidence": 50,
            "market_summary": f"{symbol} analysis based on current market data",
            "trend_analysis": f"Price vs EMA20: {current_price} vs {ema20 if ema20 else 'N/A'}" if ema20 else "DATA UNAVAILABLE",
            "momentum_analysis": f"RSI: {rsi if rsi else 'N/A'}, MACD: {macd['macd'] if macd else 'N/A'}" if macd else "DATA UNAVAILABLE",
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "options_analysis": "DATA UNAVAILABLE - Options data not available for this symbol",
            "expected_move": f"ATR: {atr} points" if atr else "DATA UNAVAILABLE",
            "bullish_scenario": {
                "trigger": "Price above VWAP with RSI < 70",
                "confirmation": "Break above resistance with volume",
                "target": "Next resistance level",
                "invalidation": "Below pivot point",
            },
            "bearish_scenario": {
                "trigger": "Price below VWAP with RSI > 30",
                "confirmation": "Break below support with volume",
                "target": "Next support level",
                "invalidation": "Above pivot point",
            },
            "range_scenario": {
                "condition": "Price between support and resistance",
                "strategy_environment": "Iron Condor or Butterfly Spread",
                "invalidation": "Breakout above resistance or breakdown below support",
            },
            "primary_strategy": {
                "strategy": "DATA UNAVAILABLE",
                "market_condition": regime,
                "expiry": "NEXT_WEEKLY",
                "legs": [],
                "entry_trigger": "DATA UNAVAILABLE",
                "maximum_profit": "DATA UNAVAILABLE",
                "maximum_loss": "DATA UNAVAILABLE",
                "breakeven": "DATA UNAVAILABLE",
                "stop_loss": "DATA UNAVAILABLE",
                "target": "DATA UNAVAILABLE",
                "adjustment": "DATA UNAVAILABLE",
                "exit": "DATA UNAVAILABLE",
            },
            "alternative_strategies": [],
            "intraday_plan": [],
            "no_trade_conditions": [
                "Low liquidity",
                "Very wide bid/ask spread",
                "Unclear direction",
                "Extreme volatility",
                "Conflicting indicators",
                "Price trapped between major levels",
            ],
            "risk_warnings": [
                "This is analytical decision-support output, not a guaranteed trading signal",
                "Do not enter trades solely based on the opening gap",
                "Every strategy must have an explicit invalidation condition",
            ],
            "data_quality": "PARTIAL" if any(v is None for v in [ema20, rsi, macd]) else "GOOD",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        self._set_cache(f"daily_analysis:{symbol}", analysis)
        return analysis


ai_service = AIService()