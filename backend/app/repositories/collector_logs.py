from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.db import CollectorLog


class CollectorLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, collector_name: str, status: str, records_updated: int = 0, error: Optional[str] = None) -> CollectorLog:
        record = CollectorLog(
            collector_name=collector_name,
            status=status,
            records_updated=records_updated,
            error=error,
            started_at=datetime.utcnow(),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def complete(self, record_id: int) -> None:
        result = await self.session.get(CollectorLog, record_id)
        if result:
            result.completed_at = datetime.utcnow()
            result.status = "completed"
            if result.started_at:
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            await self.session.commit()

    async def get_recent(self, limit: int = 20) -> list[CollectorLog]:
        result = await self.session.execute(
            select(CollectorLog).order_by(desc(CollectorLog.timestamp)).limit(limit)
        )
        return list(result.scalars().all())