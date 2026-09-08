from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

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
