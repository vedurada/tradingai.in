from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.config import load_config
from utils.logging import setup_logging
from app.providers.yahoofinance import YahooFinanceProvider
from app.providers.mock import MockMarketDataProvider, MarketDataProvider
from app.models.market import MarketOverviewResponse, HealthStatus
from app.models.db import Base
from app.repositories import MarketRepository, SignalRepository, NewsRepository
from app.services.cache import cache_service
from app.services.auth import auth_service
from app.services.ai import ai_service

logger = setup_logging("tradingai-api")

config = load_config()

engine = create_async_engine(config.get_database_url(), echo=False, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    if not credentials:
        return None
    token = credentials.credentials
    user = auth_service.validate_token(token)
    return user


async def get_provider() -> MarketDataProvider:
    provider = YahooFinanceProvider()
    if provider.is_connected():
        logger.info("Using YahooFinanceProvider")
        return provider
    logger.info("YahooFinance unavailable, falling back to MockMarketDataProvider")
    return MockMarketDataProvider()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TradingAI API...")
    await cache_service.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("TradingAI API started")
    yield
    logger.info("Shutting down TradingAI API...")
    if cache_service.enabled:
        await cache_service._client.close()
    await engine.dispose()
    logger.info("TradingAI API shut down")


def create_app(config: Optional[dict] = None) -> FastAPI:
    app_config = load_config() if config is None else config

    app = FastAPI(
        title="TradingAI API",
        description="Production financial market intelligence platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    async def health():
        provider = YahooFinanceProvider()
        db_ok = True
        redis_ok = cache_service.enabled
        try:
            async with async_session() as session:
                await session.execute("SELECT 1")
        except Exception:
            db_ok = False
        return HealthStatus(
            status="healthy",
            version="1.0.0",
            uptime_seconds=time.time() - start_time,
            services={
                "database": "connected" if db_ok else "disconnected",
                "redis": "connected" if redis_ok else "disabled",
                "provider": "yahoofinance" if provider.is_connected() else "mock",
            },
        )

    @app.get("/api/v1/market/overview")
    async def market_overview(provider: MarketDataProvider = Depends(get_provider)):
        try:
            cached = await cache_service.get("market_overview")
            if cached:
                return cached
            overview = provider.get_market_overview()
            result = overview.to_dict()
            await cache_service.set("market_overview", result, ttl=60)
            return result
        except Exception as e:
            logger.error(f"Market overview error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch market overview")

    @app.get("/api/v1/market/nifty")
    async def get_nifty(provider: MarketDataProvider = Depends(get_provider)):
        try:
            cached = await cache_service.get("quote:NIFTY")
            if cached:
                return cached
            quote = provider.get_quote("NIFTY")
            if not quote:
                raise HTTPException(status_code=404, detail="NIFTY data not found")
            result = quote.to_dict()
            await cache_service.set("quote:NIFTY", result, ttl=30)
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"NIFTY error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch NIFTY data")

    @app.get("/api/v1/market/banknifty")
    async def get_banknifty(provider: MarketDataProvider = Depends(get_provider)):
        try:
            cached = await cache_service.get("quote:BANKNIFTY")
            if cached:
                return cached
            quote = provider.get_quote("BANKNIFTY")
            if not quote:
                raise HTTPException(status_code=404, detail="BANKNIFTY data not found")
            result = quote.to_dict()
            await cache_service.set("quote:BANKNIFTY", result, ttl=30)
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"BANKNIFTY error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch BANKNIFTY data")

    @app.get("/api/v1/market/sensex")
    async def get_sensex(provider: MarketDataProvider = Depends(get_provider)):
        try:
            cached = await cache_service.get("quote:SENSEX")
            if cached:
                return cached
            quote = provider.get_quote("SENSEX")
            if not quote:
                raise HTTPException(status_code=404, detail="SENSEX data not found")
            result = quote.to_dict()
            await cache_service.set("quote:SENSEX", result, ttl=30)
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SENSEX error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch SENSEX data")

    @app.get("/api/v1/market/vix")
    async def get_vix(provider: MarketDataProvider = Depends(get_provider)):
        try:
            cached = await cache_service.get("vix")
            if cached:
                return cached
            vix = provider.get_vix()
            if not vix:
                raise HTTPException(status_code=404, detail="VIX data not found")
            result = vix.to_dict()
            await cache_service.set("vix", result, ttl=60)
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"VIX error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch VIX data")

    @app.get("/api/v1/market/ohlcv")
    async def get_ohlcv(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
    ):
        try:
            provider = await get_provider()
            data = provider.get_ohlcv(symbol.upper(), interval, limit)
            return {"symbol": symbol.upper(), "interval": interval, "data": data}
        except Exception as e:
            logger.error(f"OHLCV error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch OHLCV data")

    @app.get("/api/v1/market/option-chain")
    async def get_option_chain(
        symbol: str = Query(..., description="Symbol"),
        expiry: str = Query("", description="Expiry date"),
    ):
        try:
            provider = await get_provider()
            chain = provider.get_option_chain(symbol.upper(), expiry)
            if not chain:
                raise HTTPException(status_code=404, detail="Option chain not found")
            return chain.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Option chain error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch option chain")

    @app.post("/api/v1/auth/register")
    async def register(username: str = Query(...), password: str = Query(...), role: str = Query("user")):
        ok = auth_service.register(username, password, role)
        if not ok:
            raise HTTPException(status_code=409, detail="Username already exists")
        return {"message": "User registered", "username": username}

    @app.post("/api/v1/auth/login")
    async def login(username: str = Query(...), password: str = Query(...)):
        token = auth_service.login(username, password)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"token": token, "user": auth_service.get_user(username).to_dict()}

    @app.post("/api/v1/auth/logout")
    async def logout(token: str = Query(...)):
        auth_service.logout(token)
        return {"message": "Logged out"}

    @app.get("/api/v1/auth/me")
    async def me(current_user: Optional[dict] = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return current_user

    @app.get("/api/v1/ai/market-view")
    async def market_view(
        current_user: Optional[dict] = Depends(get_current_user),
        provider: MarketDataProvider = Depends(get_provider),
    ):
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        overview = provider.get_market_overview()
        analysis = ai_service.analyze_market(overview)
        return analysis

    @app.get("/api/v1/ai/signal")
    async def get_signal(
        symbol: str = Query(...),
        current_user: Optional[dict] = Depends(get_current_user),
        provider: MarketDataProvider = Depends(get_provider),
    ):
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        quote = provider.get_quote(symbol.upper())
        if not quote:
            raise HTTPException(status_code=404, detail="Symbol not found")
        signal = ai_service.generate_signal(symbol.upper(), quote)
        return signal

    @app.get("/api/v1/news")
    async def get_news(
        current_user: Optional[dict] = Depends(get_current_user),
        limit: int = Query(20),
    ):
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        async with async_session() as session:
            repo = NewsRepository(session)
            articles = await repo.get_latest_news(limit=limit)
            return {
                "articles": [
                    {
                        "title": a.title,
                        "source": a.source,
                        "url": a.url,
                        "summary": a.summary,
                        "sentiment": a.sentiment,
                        "category": a.category,
                        "published_at": a.published_at.isoformat() if a.published_at else "",
                    }
                    for a in articles
                ]
            }

    @app.get("/api/v1/signals")
    async def get_signals(
        current_user: Optional[dict] = Depends(get_current_user),
        symbol: Optional[str] = Query(None),
    ):
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        async with async_session() as session:
            repo = SignalRepository(session)
            signals = await repo.get_active_signals(symbol)
            return {
                "signals": [
                    {
                        "symbol": s.symbol,
                        "signal_type": s.signal_type,
                        "confidence": s.confidence,
                        "price_target": s.price_target,
                        "stop_loss": s.stop_loss,
                        "rationale": s.rationale,
                        "timestamp": s.timestamp.isoformat() if s.timestamp else "",
                    }
                    for s in signals
                ]
            }

    start_time = time.time()
    return app


app = create_app()