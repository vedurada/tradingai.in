from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

from app.models.market import MarketQuote, MarketOverview, VIXQuote

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
    option_type: str  # CE or PE
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
    call_contracts: list[OptionContract] = field(default_factory=list)
    put_contracts: list[OptionContract] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "expiry": self.expiry,
            "underlying_price": self.underlying_price,
            "call_contracts": [c.to_dict() for c in self.call_contracts],
            "put_contracts": [p.to_dict() for p in self.put_contracts],
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
    current_phase: str  # Pre-open, Open, Closing, Closed
    market_open_time: str = "09:15 IST"
    market_close_time: str = "15:30 IST"
    current_time: str = ""

class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        pass

    @abstractmethod
    def get_ohlcv(self, symbol: str, interval: str, limit: int = 100) -> list[OHLCV]:
        pass

    @abstractmethod
    def get_option_chain(self, symbol: str, expiry: str) -> Optional[OptionChain]:
        pass

    @abstractmethod
    def get_market_status(self) -> MarketStatus:
        pass

    @abstractmethod
    def get_market_overview(self) -> MarketOverview:
        pass

    @abstractmethod
    def get_vix(self) -> Optional[VIXQuote]:
        pass

    def is_connected(self) -> bool:
        return True

class MockMarketDataProvider(MarketDataProvider):
    def __init__(self) -> None:
        self._connected = True
        self._cache: dict[str, Any] = {}

    def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        quotes = {
            "NIFTY": MarketQuote("NIFTY", "NIFTY 50", 25142.35, 105.20, 0.42, 25050.0, 25200.0, 25020.0, 25037.15, 0, "2026-09-08T14:50:00Z", "Open"),
            "BANKNIFTY": MarketQuote("BANKNIFTY", "NIFTY Bank", 55230.50, 245.75, 0.45, 55000.0, 55400.0, 54980.0, 54984.75, 0, "2026-09-08T14:50:00Z", "Open"),
            "SENSEX": MarketQuote("SENSEX", "S&P BSE Sensex", 82350.75, 312.50, 0.38, 82100.0, 82500.0, 82050.0, 82038.25, 0, "2026-09-08T14:50:00Z", "Open"),
            "INDIA VIX": MarketQuote("INDIA VIX", "India Volatility Index", 12.85, -0.15, -1.15, 12.90, 13.10, 12.80, 13.00, 0, "2026-09-08T14:50:00Z", "Open"),
        }
        return quotes.get(symbol.upper())

    def get_ohlcv(self, symbol: str, interval: str, limit: int = 100) -> list[OHLCV]:
        return []

    def get_option_chain(self, symbol: str, expiry: str) -> Optional[OptionChain]:
        return None

    def get_market_status(self) -> MarketStatus:
        return MarketStatus(True, "Open", "09:15 IST", "15:30 IST", "2026-09-08T14:50:00Z")

    def get_market_overview(self) -> MarketOverview:
        return MarketOverview(
            nifty=self.get_quote("NIFTY") or _default_quote(),
            banknifty=self.get_quote("BANKNIFTY") or _default_quote(),
            sensex=self.get_quote("SENSEX") or _default_quote(),
            vix=VIXQuote("INDIA VIX", "India Volatility Index", 12.85, -0.15, -1.15, "Declining", False, "2026-09-08T14:50:00Z"),
            market_status="Open",
            timestamp="2026-09-08T14:50:00Z",
        )

    def get_vix(self) -> Optional[VIXQuote]:
        return VIXQuote("INDIA VIX", "India Volatility Index", 12.85, -0.15, -1.15, "Declining", False, "2026-09-08T14:50:00Z")

    def is_connected(self) -> bool:
        return self._connected
