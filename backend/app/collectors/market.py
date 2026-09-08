from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import MarketQuote, OHLCV, Base
from app.repositories.market import MarketRepository
from app.providers.base import MarketDataProvider
from app.providers.yahoofinance import YahooFinanceProvider
from app.providers.mock import MockMarketDataProvider

logger = logging.getLogger("tradingai.collectors.market")

INDEX_SYMBOLS = ["NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "NIFTYIT", "NIFTYAUTO", "NIFTYFMCG", "NIFTYPHARMA", "NIFTYMETAL", "NIFTYREALTY", "NIFTYPSUBANK"]


class MarketCollector:
    def __init__(self) -> None:
        self.provider: Optional[MarketDataProvider] = None

    async def connect(self) -> None:
        from app.providers.base import DataProviderRegistry
        self.provider = DataProviderRegistry.get_connected()
        if not self.provider:
            logger.warning("No provider connected, using mock")
            self.provider = MockMarketDataProvider()

    async def collect(self, session: AsyncSession) -> dict:
        if not self.provider:
            await self.connect()

        records_updated = 0
        for symbol in INDEX_SYMBOLS:
            try:
                quote = self.provider.get_quote(symbol)
                if quote:
                    repo = MarketRepository(session)
                    await repo.save_quote(quote.to_dict())
                    records_updated += 1
            except Exception as e:
                logger.error(f"Market collect error for {symbol}: {e}")

        overview = self.provider.get_market_overview()
        for sym in ["NIFTY", "BANKNIFTY", "SENSEX"]:
            try:
                ohlcv_list = self.provider.get_ohlcv(sym, interval="5m", limit=12)
                for ohlcv in ohlcv_list:
                    record = OHLCV(
                        symbol=sym, interval="5m",
                        timestamp=datetime.fromisoformat(ohlcv["timestamp"]) if "timestamp" in ohlcv else datetime.now(timezone.utc),
                        open=ohlcv["open"], high=ohlcv["high"],
                        low=ohlcv["low"], close=ohlcv["close"],
                        volume=ohlcv["volume"],
                    )
                    session.add(record)
                    records_updated += 1
            except Exception as e:
                logger.error(f"OHLCV collect error for {sym}: {e}")

        await session.commit()
        return {"collector": "market", "records_updated": records_updated}