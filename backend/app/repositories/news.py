from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.db import NewsArticle


class NewsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_article(self, article: dict) -> NewsArticle:
        record = NewsArticle(
            title=article["title"],
            source=article.get("source", ""),
            url=article.get("url", ""),
            summary=article.get("summary", ""),
            sentiment=article.get("sentiment", "neutral"),
            category=article.get("category", "market"),
            published_at=datetime.utcnow(),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_latest_news(self, limit: int = 20, category: Optional[str] = None) -> list[NewsArticle]:
        query = select(NewsArticle).order_by(desc(NewsArticle.timestamp))
        if category:
            query = query.where(NewsArticle.category == category)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())