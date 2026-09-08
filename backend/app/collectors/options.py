from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market import MarketRepository
from app.providers.base import MarketDataProvider
from app.providers.yahoofinance import YahooFinanceProvider
from app.providers.mock import MockMarketDataProvider

logger = logging.getLogger("tradingai.collectors.options")


class OptionsCollector:
    def __init__(self) -> None:
        self.provider: Optional[MarketDataProvider] = None

    async def connect(self) -> None:
        from app.providers.base import DataProviderRegistry
        self.provider = DataProviderRegistry.get_connected()
        if not self.provider:
            logger.warning("No provider connected for options, using mock")
            self.provider = MockMarketDataProvider()

    async def collect(self, session: AsyncSession) -> dict:
        if not self.provider:
            await self.connect()

        records_updated = 0
        for symbol in ["NIFTY", "BANKNIFTY"]:
            try:
                chain = self.provider.get_option_chain(symbol)
                if chain:
                    repo = MarketRepository(session)
                    result = await repo.save_option_contracts(chain.call_contracts + chain.put_contracts)
                    records_updated += len(result)
            except Exception as e:
                logger.error(f"Options collect error for {symbol}: {e}")

        await session.commit()
        return {"collector": "options", "records_updated": records_updated}