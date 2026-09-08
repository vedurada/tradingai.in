from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.db import Signal


class SignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_signal(self, signal: dict) -> Signal:
        record = Signal(
            symbol=signal["symbol"],
            signal_type=signal["signal_type"],
            confidence=signal.get("confidence", 0),
            price_target=signal.get("price_target"),
            stop_loss=signal.get("stop_loss"),
            rationale=signal.get("rationale"),
            is_active=signal.get("is_active", True),
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_active_signals(self, symbol: Optional[str] = None) -> list[Signal]:
        query = select(Signal).where(Signal.is_active == True)
        if symbol:
            query = query.where(Signal.symbol == symbol)
        query = query.order_by(desc(Signal.timestamp))
        result = await self.session.execute(query)
        return list(result.scalars().all())