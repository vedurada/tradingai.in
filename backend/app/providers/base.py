from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

from app.models.market import MarketQuote, MarketOverview, VIXQuote, OHLCV, OptionChain, OptionContract, PCRData, MaxPainData, MarketStatus


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

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    def get_sector_indices(self) -> Optional[dict[str, MarketQuote]]:
        return None

    def get_stock_quote(self, symbol: str) -> Optional[MarketQuote]:
        return None

    def get_etf_quote(self, symbol: str) -> Optional[MarketQuote]:
        return None

    def get_global_markets(self) -> Optional[dict[str, MarketQuote]]:
        return None


class DataProviderRegistry:
    _providers: dict[str, MarketDataProvider] = {}

    @classmethod
    def register(cls, name: str, provider: MarketDataProvider) -> None:
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> Optional[MarketDataProvider]:
        return cls._providers.get(name)

    @classmethod
    def get_connected(cls) -> Optional[MarketDataProvider]:
        for name, provider in cls._providers.items():
            if provider.is_connected():
                return provider
        return None

    @classmethod
    def all(cls) -> dict[str, MarketDataProvider]:
        return dict(cls._providers)
