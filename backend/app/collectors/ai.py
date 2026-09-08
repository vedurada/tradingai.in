from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_engine import AIEngine
from app.providers.yahoofinance import YahooFinanceProvider
from app.providers.mock import MockMarketDataProvider
from app.models.market import MarketOverview

logger = logging.getLogger("tradingai.collectors.ai")


class AIAnalyzer:
    def __init__(self) -> None:
        self.engine = AIEngine()
        self.provider = None

    async def connect(self) -> None:
        from app.providers.base import DataProviderRegistry
        self.provider = DataProviderRegistry.get_connected()
        if not self.provider:
            logger.warning("No provider connected for AI")
            self.provider = MockMarketDataProvider()

    async def collect(self, session: AsyncSession) -> dict:
        if not self.provider:
            await self.connect()

        overview = self.provider.get_market_overview()
        await self.engine.analyze_market(session, overview)
        await self.engine.generate_scenarios(session, overview)

        return {"collector": "ai", "records_updated": 1}