from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

@dataclass
class MarketQuote:
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    previous_close: float
    volume: int
    timestamp: str
    market_status: str = "Closed"
    currency: str = "INR"
    exchange: str = "NSE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_pct": self.change_pct,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "previous_close": self.previous_close,
            "volume": self.volume,
            "timestamp": self.timestamp,
            "market_status": self.market_status,
            "currency": self.currency,
            "exchange": self.exchange,
        }

def _default_quote() -> MarketQuote:
    return MarketQuote("NIFTY", "NIFTY 50", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, "", "Closed")

@dataclass
class MarketOverview:
    nifty: MarketQuote = field(default_factory=_default_quote)
    banknifty: MarketQuote = field(default_factory=_default_quote)
    sensex: MarketQuote = field(default_factory=_default_quote)
    vix: MarketQuote = field(default_factory=_default_quote)
    market_status: str = "Closed"
    timestamp: str = ""
    global_markets: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nifty": self.nifty.to_dict(),
            "banknifty": self.banknifty.to_dict(),
            "sensex": self.sensex.to_dict(),
            "vix": self.vix.to_dict(),
            "market_status": self.market_status,
            "timestamp": self.timestamp,
            "global_markets": self.global_markets,
        }

@dataclass
class HealthStatus:
    status: str
    version: str
    uptime_seconds: float
    services: dict[str, str] = field(default_factory=dict)

@dataclass
class IndexQuote:
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    previous_close: float
    volume: int
    timestamp: str
    market_status: str = "Closed"

@dataclass
class VIXQuote:
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    trend: str = "Stable"
    risk_off: bool = False
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_pct": self.change_pct,
            "trend": self.trend,
            "risk_off": self.risk_off,
            "timestamp": self.timestamp,
        }

@dataclass
class GlobalMarket:
    name: str
    symbol: str
    price: float
    change: float
    change_pct: float
    currency: str = ""
    category: str = ""

@dataclass
class MarketOverviewResponse:
    nifty: dict[str, Any]
    banknifty: dict[str, Any]
    sensex: dict[str, Any]
    vix: dict[str, Any]
    market_status: str
    timestamp: str
    global_markets: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class NiftyQuote:
    symbol: str = "NIFTY"
    name: str = "NIFTY 50"
    price: float = 25142.35
    change: float = 105.20
    change_pct: float = 0.42
    open: float = 25050.0
    high: float = 25200.0
    low: float = 25020.0
    previous_close: float = 25037.15
    volume: int = 0
    timestamp: str = ""
    market_status: str = "Open"
    currency: str = "INR"
    exchange: str = "NSE"

@dataclass
class BankNiftyQuote:
    symbol: str = "BANKNIFTY"
    name: str = "NIFTY Bank"
    price: float = 55230.50
    change: float = 245.75
    change_pct: float = 0.45
    open: float = 55000.0
    high: float = 55400.0
    low: float = 54980.0
    previous_close: float = 54984.75
    volume: int = 0
    timestamp: str = ""
    market_status: str = "Open"
    currency: str = "INR"
    exchange: str = "NSE"

@dataclass
class SensexQuote:
    symbol: str = "SENSEX"
    name: str = "S&P BSE Sensex"
    price: float = 82350.75
    change: float = 312.50
    change_pct: float = 0.38
    open: float = 82100.0
    high: float = 82500.0
    low: float = 82050.0
    previous_close: float = 82038.25
    volume: int = 0
    timestamp: str = ""
    market_status: str = "Open"
    currency: str = "INR"
    exchange: str = "BSE"

@dataclass
class VIXQuoteResponse:
    symbol: str = "INDIA VIX"
    name: str = "India Volatility Index"
    price: float = 12.85
    change: float = -0.15
    change_pct: float = -1.15
    trend: str = "Declining"
    risk_off: bool = False
    timestamp: str = ""


@dataclass
class OHLCV:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class OptionContract:
    symbol: str
    expiry: str
    strike: float
    option_type: str
    last_price: float
    open_interest: int
    change_in_oi: int
    volume: int
    implied_volatility: float
    bid: float
    ask: float
    delta: float
    gamma: float
    theta: float
    vega: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "expiry": self.expiry,
            "strike": self.strike,
            "option_type": self.option_type,
            "last_price": self.last_price,
            "open_interest": self.open_interest,
            "change_in_oi": self.change_in_oi,
            "volume": self.volume,
            "implied_volatility": self.implied_volatility,
            "bid": self.bid,
            "ask": self.ask,
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
        }


@dataclass
class OptionChain:
    symbol: str
    expiry: str
    underlying_price: float
    call_contracts: list[Any] = field(default_factory=list)
    put_contracts: list[Any] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "expiry": self.expiry,
            "underlying_price": self.underlying_price,
            "call_contracts": [c if isinstance(c, dict) else c.to_dict() for c in self.call_contracts],
            "put_contracts": [c if isinstance(c, dict) else c.to_dict() for c in self.put_contracts],
            "timestamp": self.timestamp,
        }


@dataclass
class PCRData:
    symbol: str
    oi_pcr: float = 0.0
    volume_pcr: float = 0.0
    timestamp: str = ""


@dataclass
class MaxPainData:
    symbol: str
    expiry: str
    max_pain: float = 0.0
    call_max_oi_strike: float = 0.0
    put_max_oi_strike: float = 0.0
    timestamp: str = ""


@dataclass
class MarketStatus:
    is_open: bool
    current_phase: str
    market_open_time: str = "09:15 IST"
    market_close_time: str = "15:30 IST"
    current_time: str = ""
