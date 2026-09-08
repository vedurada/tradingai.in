from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.collectors import MarketCollector, OptionsCollector, NewsCollector, AIAnalyzer
from app.services.cache import cache_service

logger = logging.getLogger("tradingai.scheduler")


class Scheduler:
    def __init__(self) -> None:
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self._running = True
        logger.info("Scheduler started")

        self._tasks.append(asyncio.create_task(self._run_market()))
        self._tasks.append(asyncio.create_task(self._run_options()))
        self._tasks.append(asyncio.create_task(self._run_news()))
        self._tasks.append(asyncio.create_task(self._run_ai()))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("Scheduler stopped")

    async def _run_market(self) -> None:
        while self._running:
            try:
                from app.main import async_session
                async with async_session() as session:
                    collector = MarketCollector()
                    await collector.connect()
                    result = await collector.collect(session)
                    logger.info(f"Market collector: {result}")
            except Exception as e:
                logger.error(f"Market collector error: {e}")
            await asyncio.sleep(60)

    async def _run_options(self) -> None:
        while self._running:
            try:
                from app.main import async_session
                async with async_session() as session:
                    collector = OptionsCollector()
                    await collector.connect()
                    result = await collector.collect(session)
                    logger.info(f"Options collector: {result}")
            except Exception as e:
                logger.error(f"Options collector error: {e}")
            await asyncio.sleep(300)

    async def _run_news(self) -> None:
        while self._running:
            try:
                from app.main import async_session
                async with async_session() as session:
                    collector = NewsCollector()
                    await collector.connect()
                    result = await collector.collect(session)
                    logger.info(f"News collector: {result}")
            except Exception as e:
                logger.error(f"News collector error: {e}")
            await asyncio.sleep(900)

    async def _run_ai(self) -> None:
        while self._running:
            try:
                from app.main import async_session
                async with async_session() as session:
                    analyzer = AIAnalyzer()
                    await analyzer.connect()
                    result = await analyzer.collect(session)
                    logger.info(f"AI analyzer: {result}")
            except Exception as e:
                logger.error(f"AI analyzer error: {e}")
            await asyncio.sleep(300)


scheduler = Scheduler()