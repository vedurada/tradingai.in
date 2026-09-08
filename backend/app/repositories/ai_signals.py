from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.db import AISignal


class AISignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_signal(self, data: dict) -> AISignal:
        record = AISignal(
            symbol=data.get("symbol", "NIFTY"),
            regime=data.get("regime", "NEUTRAL"),
            trend=data.get("trend", "NEUTRAL"),
            momentum=data.get("momentum", "NEUTRAL"),
            volatility=data.get("volatility", "NEUTRAL"),
            breadth=data.get("breadth", "NEUTRAL"),
            options_sentiment=data.get("options_sentiment", "NEUTRAL"),
            confidence=data.get("confidence", 0),
            reasons_bullish=data.get("reasons_bullish"),
            reasons_bearish=data.get("reasons_bearish"),
            warnings=data.get("warnings"),
            view_invalidation=data.get("view_invalidation"),
            is_active=data.get("is_active", True),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_latest(self, symbol: Optional[str] = None) -> Optional[AISignal]:
        query = select(AISignal).order_by(desc(AISignal.timestamp))
        if symbol:
            query = query.where(AISignal.symbol == symbol)
        query = query.limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()