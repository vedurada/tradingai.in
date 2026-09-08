from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

from app.models.market import MarketQuote, MarketOverview, VIXQuote, OHLCV, OptionChain, OptionContract, PCRData, MaxPainData, MarketStatus
from app.providers.base import MarketDataProvider


def _default_quote() -> MarketQuote:
    return MarketQuote("NIFTY", "NIFTY 50", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, "", "Closed")


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