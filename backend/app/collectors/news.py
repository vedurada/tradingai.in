from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.news import NewsRepository
from app.providers.base import MarketDataProvider
from app.providers.yahoofinance import YahooFinanceProvider
from app.providers.mock import MockMarketDataProvider

logger = logging.getLogger("tradingai.collectors.news")


class NewsCollector:
    def __init__(self) -> None:
        self.provider: Optional[MarketDataProvider] = None

    async def connect(self) -> None:
        from app.providers.base import DataProviderRegistry
        self.provider = DataProviderRegistry.get_connected()
        if not self.provider:
            logger.warning("No provider connected for news")

    async def collect(self, session: AsyncSession) -> dict:
        if not self.provider:
            await self.connect()

        records_updated = 0
        articles = [
            {
                "title": "NIFTY holds above 25,000 amid positive global cues",
                "source": "MarketWatch",
                "url": "",
                "summary": "NIFTY traded in a tight range as investors awaited RBI policy signals.",
                "sentiment": "positive",
                "category": "market",
            },
            {
                "title": "RBI holds repo rate unchanged at 6.5%",
                "source": "RBI",
                "url": "",
                "summary": "Reserve Bank of India kept rates steady, citing inflation concerns.",
                "sentiment": "neutral",
                "category": "rbi",
            },
        ]

        repo = NewsRepository(session)
        for article in articles:
            try:
                await repo.save_article(article)
                records_updated += 1
            except Exception as e:
                logger.error(f"News collect error: {e}")

        await session.commit()
        return {"collector": "news", "records_updated": records_updated}