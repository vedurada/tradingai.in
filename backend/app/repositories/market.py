from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.db import MarketQuote, OHLCV, OptionContract


class MarketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_quote(self, quote: dict) -> MarketQuote:
        record = MarketQuote(
            symbol=quote["symbol"],
            price=quote["price"],
            change=quote.get("change", 0),
            change_pct=quote.get("change_pct", 0),
            open_price=quote.get("open", 0),
            high=quote.get("high", 0),
            low=quote.get("low", 0),
            previous_close=quote.get("previous_close", 0),
            volume=quote.get("volume", 0),
            market_status=quote.get("market_status", "Closed"),
            timestamp=datetime.fromisoformat(quote["timestamp"]) if "timestamp" in quote else datetime.now(timezone.utc),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_latest_quote(self, symbol: str) -> Optional[MarketQuote]:
        result = await self.session.execute(
            select(MarketQuote).where(MarketQuote.symbol == symbol).order_by(desc(MarketQuote.timestamp)).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_quotes(self, symbols: list[str]) -> list[MarketQuote]:
        result = await self.session.execute(
            select(MarketQuote).where(MarketQuote.symbol.in_(symbols)).order_by(desc(MarketQuote.timestamp))
        )
        return list(result.scalars().all())

    async def save_ohlcv(self, ohlcv: dict) -> OHLCV:
        record = OHLCV(
            symbol=ohlcv["symbol"],
            interval=ohlcv.get("timeframe", "1d"),
            timestamp=datetime.fromisoformat(ohlcv["timestamp"]) if "timestamp" in ohlcv else datetime.now(timezone.utc),
            open=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
            volume=ohlcv["volume"],
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_ohlcv(self, symbol: str, interval: str = "1d", limit: int = 100) -> list[OHLCV]:
        result = await self.session.execute(
            select(OHLCV)
            .where(OHLCV.symbol == symbol, OHLCV.interval == interval)
            .order_by(desc(OHLCV.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save_option_contracts(self, contracts: list[dict]) -> list[OptionContract]:
        records = []
        for c in contracts:
            record = OptionContract(
                symbol=c["symbol"],
                expiry=c.get("expiry", ""),
                strike=c.get("strike", 0),
                option_type=c.get("option_type", "CE"),
                last_price=c.get("last_price"),
                open_interest=c.get("open_interest", 0),
                change_in_oi=c.get("change_in_oi", 0),
                volume=c.get("volume", 0),
                implied_volatility=c.get("implied_volatility"),
                bid=c.get("bid"),
                ask=c.get("ask"),
                delta=c.get("delta"),
                gamma=c.get("gamma"),
                theta=c.get("theta"),
                vega=c.get("vega"),
            )
            self.session.add(record)
            records.append(record)
        await self.session.commit()
        return records

    async def get_option_chain(self, symbol: str, expiry: str = "") -> list[OptionContract]:
        query = select(OptionContract).where(OptionContract.symbol == symbol)
        if expiry:
            query = query.where(OptionContract.expiry == expiry)
        query = query.order_by(desc(OptionContract.timestamp))
        result = await self.session.execute(query)
        return list(result.scalars().all())