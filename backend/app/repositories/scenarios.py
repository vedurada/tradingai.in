from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.db import Scenario


class ScenarioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_scenario(self, data: dict) -> Scenario:
        record = Scenario(
            symbol=data.get("symbol", "NIFTY"),
            condition=data.get("condition", ""),
            scenario_type=data.get("scenario_type", "continuation"),
            probability=data.get("probability", 0),
            description=data.get("description"),
            is_active=data.get("is_active", True),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_active(self, symbol: Optional[str] = None) -> list[Scenario]:
        query = select(Scenario).where(Scenario.is_active == True)
        if symbol:
            query = query.where(Scenario.symbol == symbol)
        query = query.order_by(desc(Scenario.timestamp))
        result = await self.session.execute(query)
        return list(result.scalars().all())