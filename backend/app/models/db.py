from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Index,
    Boolean,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    exchange = Column(String(20), default="NSE")
    sector = Column(String(100))
    instrument_type = Column(String(20), default="EQ")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change = Column(Float, default=0)
    change_pct = Column(Float, default=0)
    open_price = Column(Float)
    high = Column(Float)
    low = Column(Float)
    previous_close = Column(Float)
    volume = Column(Integer, default=0)
    market_status = Column(String(20), default="Closed")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class OHLCV(Base):
    __tablename__ = "ohlcv"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    interval = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_ohlcv_sym_time", "symbol", "interval", "timestamp"),
    )


class OptionContract(Base):
    __tablename__ = "option_contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    expiry = Column(String(20), nullable=False)
    strike = Column(Float, nullable=False)
    option_type = Column(String(2), nullable=False)
    last_price = Column(Float)
    open_interest = Column(Integer, default=0)
    change_in_oi = Column(Integer, default=0)
    volume = Column(Integer, default=0)
    implied_volatility = Column(Float)
    bid = Column(Float)
    ask = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)
    confidence = Column(Float, default=0)
    price_target = Column(Float)
    stop_loss = Column(Float)
    rationale = Column(Text)
    is_active = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class NewsArticle(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    source = Column(String(200))
    url = Column(Text)
    summary = Column(Text)
    sentiment = Column(String(20), default="neutral")
    category = Column(String(50))
    published_at = Column(DateTime, default=datetime.utcnow)
    timestamp = Column(DateTime, default=datetime.utcnow)