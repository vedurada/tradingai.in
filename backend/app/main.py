from __future__ import annotations

import time
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from config.config import load_config
from utils.logging import setup_logging
from app.providers.yahoofinance import YahooFinanceProvider
from app.providers.mock import MockMarketDataProvider, MarketDataProvider
from app.providers.base import DataProviderRegistry
from app.models.market import MarketOverviewResponse, HealthStatus
from app.models.db import Base
from app.repositories import MarketRepository, SignalRepository, NewsRepository
from app.services.cache import cache_service
from app.services.auth import auth_service
from app.services.ai import ai_service
from app.services.scheduler import scheduler
from app.services.technical_indicators import (
    calculate_all_indicators,
    calculate_vwap,
    calculate_pivot,
    calculate_cpr,
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_macd,
    calculate_adx,
    calculate_support_resistance,
)
from app.services.market_regime import market_regime_engine
from app.services.options_intelligence import OptionsIntelligence
from app.services.strategy_engine import strategy_engine
from app.collectors import MarketCollector, OptionsCollector, NewsCollector, AIAnalyzer

logger = setup_logging("tradingai-api")

config = load_config()

engine = create_async_engine(config.get_database_url(), echo=False, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_current_user(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    user = auth_service.validate_token(token)
    return user


async def get_provider() -> MarketDataProvider:
    provider = DataProviderRegistry.get_connected()
    if provider:
        return provider
    yp = YahooFinanceProvider()
    if yp.is_connected():
        DataProviderRegistry.register("yahoofinance", yp)
        logger.info("Using YahooFinanceProvider")
        return yp
    logger.info("YahooFinance unavailable, falling back to MockMarketDataProvider")
    mp = MockMarketDataProvider()
    DataProviderRegistry.register("mock", mp)
    return mp


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TradingAI API...")
    await cache_service.connect()
    db_connected = False
    for attempt in range(30):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")
            db_connected = True
            break
        except Exception as e:
            logger.warning(f"DB connection attempt {attempt+1} failed: {e}")
            await asyncio.sleep(5)
    if not db_connected:
        logger.warning("Database not available, starting without DB")

    await scheduler.start()
    logger.info("TradingAI API started")
    yield
    logger.info("Shutting down TradingAI API...")
    await scheduler.stop()
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
        provider = await get_provider()
        db_ok = True
        redis_ok = cache_service.enabled
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1"))
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

    @app.get("/api/v1/market/sector-indices")
    async def get_sector_indices(provider: MarketDataProvider = Depends(get_provider)):
        result = provider.get_sector_indices()
        if not result:
            raise HTTPException(status_code=404, detail="Sector indices not available")
        return {symbol: quote.to_dict() for symbol, quote in result.items()}

    @app.get("/api/v1/market/global")
    async def get_global_markets(provider: MarketDataProvider = Depends(get_provider)):
        result = provider.get_global_markets()
        if not result:
            raise HTTPException(status_code=404, detail="Global markets not available")
        return {symbol: quote.to_dict() for symbol, quote in result.items()}

    @app.get("/api/v1/market/stock/{symbol}")
    async def get_stock(symbol: str, provider: MarketDataProvider = Depends(get_provider)):
        quote = provider.get_stock_quote(symbol.upper())
        if not quote:
            raise HTTPException(status_code=404, detail="Stock not found")
        return quote.to_dict()

    @app.get("/api/v1/market/etf/{symbol}")
    async def get_etf(symbol: str, provider: MarketDataProvider = Depends(get_provider)):
        quote = provider.get_etf_quote(symbol.upper())
        if not quote:
            raise HTTPException(status_code=404, detail="ETF not found")
        return quote.to_dict()

    @app.get("/api/v1/technical/indicators")
    async def get_technical_indicators(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            quote = provider.get_quote(symbol.upper())
            quote_dict = quote.to_dict() if quote else {"high": 0, "low": 0, "close": 0, "price": 0}
            result = calculate_all_indicators(ohlcv_data, quote_dict)
            return {
                "symbol": symbol.upper(),
                "interval": interval,
                "indicators": result,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Technical indicators error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate indicators")

    @app.get("/api/v1/technical/vwap")
    async def get_vwap(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            vwap = calculate_vwap(ohlcv_data)
            return {"symbol": symbol.upper(), "interval": interval, "vwap": vwap}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"VWAP error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate VWAP")

    @app.get("/api/v1/technical/pivot")
    async def get_pivot(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            quote = provider.get_quote(symbol.upper())
            quote_dict = quote.to_dict() if quote else {"high": 0, "low": 0, "close": 0, "price": 0}
            pivot = calculate_pivot(quote_dict)
            cpr = calculate_cpr(pivot)
            return {"symbol": symbol.upper(), "interval": interval, "pivot": pivot, "cpr": cpr}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Pivot error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate pivot")

    @app.get("/api/v1/technical/bollinger")
    async def get_bollinger(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
        period: int = Query(20),
        std_mult: float = Query(2.0),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            closes = [row.get("close", 0) for row in ohlcv_data]
            bb = calculate_bollinger_bands(closes, period, std_mult)
            return {"symbol": symbol.upper(), "interval": interval, "bollinger_bands": bb}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Bollinger Bands error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate Bollinger Bands")

    @app.get("/api/v1/technical/rsi")
    async def get_rsi(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
        period: int = Query(14),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            closes = [row.get("close", 0) for row in ohlcv_data]
            rsi = calculate_rsi(closes, period)
            return {"symbol": symbol.upper(), "interval": interval, "rsi": rsi}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"RSI error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate RSI")

    @app.get("/api/v1/technical/macd")
    async def get_macd(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
        fast: int = Query(12),
        slow: int = Query(26),
        signal: int = Query(9),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            closes = [row.get("close", 0) for row in ohlcv_data]
            macd = calculate_macd(closes, fast, slow, signal)
            return {"symbol": symbol.upper(), "interval": interval, "macd": macd}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"MACD error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate MACD")

    @app.get("/api/v1/technical/adx")
    async def get_adx(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
        period: int = Query(14),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            highs = [row.get("high", 0) for row in ohlcv_data]
            lows = [row.get("low", 0) for row in ohlcv_data]
            closes = [row.get("close", 0) for row in ohlcv_data]
            adx = calculate_adx(highs, lows, closes, period)
            return {"symbol": symbol.upper(), "interval": interval, "adx": adx}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ADX error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate ADX")

    @app.get("/api/v1/technical/support-resistance")
    async def get_support_resistance(
        symbol: str = Query(..., description="Symbol"),
        interval: str = Query("1d", description="Timeframe"),
        limit: int = Query(100, description="Candles"),
        window: int = Query(20),
    ):
        try:
            provider = await get_provider()
            ohlcv_data = provider.get_ohlcv(symbol.upper(), interval, limit)
            if not ohlcv_data:
                raise HTTPException(status_code=404, detail="OHLCV data not found")
            sr = calculate_support_resistance(ohlcv_data, window)
            return {"symbol": symbol.upper(), "interval": interval, "support_resistance": sr}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Support/Resistance error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate support/resistance")

    options_intel = OptionsIntelligence()

    @app.get("/api/v1/options/intelligence")
    async def get_options_intelligence(
        symbol: str = Query("NIFTY", description="Symbol"),
        expiry: str = Query("", description="Expiry filter"),
    ):
        try:
            provider = await get_provider()
            chain = provider.get_option_chain(symbol.upper(), expiry)
            if not chain:
                raise HTTPException(status_code=404, detail="Option chain not found")
            contracts = [c if isinstance(c, dict) else c.to_dict() for c in chain.call_contracts + chain.put_contracts]
            result = await options_intel.get_options_intelligence(
                contracts, chain.underlying_price, symbol.upper()
            )
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Options intelligence error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch options intelligence")

    @app.get("/api/v1/options/pcr")
    async def get_pcr(
        symbol: str = Query("NIFTY", description="Symbol"),
        expiry: str = Query("", description="Expiry filter"),
    ):
        try:
            provider = await get_provider()
            chain = provider.get_option_chain(symbol.upper(), expiry)
            if not chain:
                raise HTTPException(status_code=404, detail="Option chain not found")
            contracts = [c if isinstance(c, dict) else c.to_dict() for c in chain.call_contracts + chain.put_contracts]
            call_oi = sum(c.get("open_interest", 0) for c in contracts if c.get("option_type") == "CE")
            put_oi = sum(c.get("open_interest", 0) for c in contracts if c.get("option_type") == "PE")
            pcr = options_intel.calculate_pcr(call_oi, put_oi)
            return {"symbol": symbol.upper(), "pcr": pcr, "call_oi": call_oi, "put_oi": put_oi}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PCR error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate PCR")

    @app.get("/api/v1/options/max-pain")
    async def get_max_pain(
        symbol: str = Query("NIFTY", description="Symbol"),
        expiry: str = Query("", description="Expiry filter"),
    ):
        try:
            provider = await get_provider()
            chain = provider.get_option_chain(symbol.upper(), expiry)
            if not chain:
                raise HTTPException(status_code=404, detail="Option chain not found")
            contracts = [c if isinstance(c, dict) else c.to_dict() for c in chain.call_contracts + chain.put_contracts]
            max_pain = options_intel.calculate_max_pain(contracts)
            return {"symbol": symbol.upper(), "max_pain": max_pain}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Max pain error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate max pain")

    @app.get("/api/v1/options/iv")
    async def get_iv(
        symbol: str = Query("NIFTY", description="Symbol"),
        expiry: str = Query("", description="Expiry filter"),
    ):
        try:
            provider = await get_provider()
            chain = provider.get_option_chain(symbol.upper(), expiry)
            if not chain:
                raise HTTPException(status_code=404, detail="Option chain not found")
            contracts = [c if isinstance(c, dict) else c.to_dict() for c in chain.call_contracts + chain.put_contracts]
            iv_stats = options_intel.calculate_iv_stats(contracts)
            return {"symbol": symbol.upper(), "iv_stats": iv_stats}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"IV error: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate IV stats")

    @app.get("/api/v1/options/weekly-analysis")
    async def get_weekly_analysis(
        symbol: str = Query("NIFTY", description="Symbol"),
        expiry: str = Query("", description="Expiry filter"),
    ):
        try:
            provider = await get_provider()
            chain = provider.get_option_chain(symbol.upper(), expiry)
            if not chain:
                raise HTTPException(status_code=404, detail="Option chain not found")
            contracts = [c if isinstance(c, dict) else c.to_dict() for c in chain.call_contracts + chain.put_contracts]
            result = await options_intel.get_options_intelligence(
                contracts, chain.underlying_price, symbol.upper()
            )
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Weekly analysis error: {e}")
            raise HTTPException(status_code=500, detail="Failed to analyze weekly options")

    @app.get("/api/v1/strategy/decision-matrix")
    async def get_strategy_decision_matrix(
        current_user: Optional[dict] = Depends(get_current_user),
    ):
        matrix = [
            {"market_condition": "Strong bullish trend", "strategy_family": "Call Debit Spread", "risk_level": "Medium"},
            {"market_condition": "Moderate bullish", "strategy_family": "Put Credit Spread", "risk_level": "Low"},
            {"market_condition": "Strong bearish trend", "strategy_family": "Put Debit Spread", "risk_level": "Medium"},
            {"market_condition": "Moderate bearish", "strategy_family": "Call Credit Spread", "risk_level": "Low"},
            {"market_condition": "Tight range + low volatility", "strategy_family": "Iron Condor", "risk_level": "Low"},
            {"market_condition": "Expected breakout + low IV", "strategy_family": "Long Straddle/Strangle", "risk_level": "High"},
            {"market_condition": "High IV + range", "strategy_family": "Defined-risk premium selling", "risk_level": "Medium"},
            {"market_condition": "Extreme volatility", "strategy_family": "Reduce risk / wait", "risk_level": "High"},
            {"market_condition": "Conflicting signals", "strategy_family": "No trade", "risk_level": "N/A"},
            {"market_condition": "Poor liquidity", "strategy_family": "No trade", "risk_level": "N/A"},
        ]
        return {"decision_matrix": matrix}

    @app.get("/api/v1/strategy/options")
    async def get_strategy_options(
        current_user: Optional[dict] = Depends(get_current_user),
        provider: MarketDataProvider = Depends(get_provider),
        symbol: str = Query("NIFTY", description="Symbol for strategy"),
    ):
        try:
            data = provider.get_daily_data(symbol.upper())
            if not data:
                raise HTTPException(status_code=404, detail="Daily data not found")
            vix = provider.get_vix()
            data["vix_price"] = vix.price if vix else 0
            analysis = ai_service.generate_daily_analysis(symbol.upper(), data)
            strategy = strategy_engine.select_strategy(analysis)
            return strategy
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Strategy options error: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate strategy options")

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
        overview = provider.get_market_overview()
        analysis = ai_service.analyze_market(overview)
        return analysis

    @app.get("/api/v1/ai/signal")
    async def get_signal(
        symbol: str = Query(...),
        current_user: Optional[dict] = Depends(get_current_user),
        provider: MarketDataProvider = Depends(get_provider),
    ):
        quote = provider.get_quote(symbol.upper())
        if not quote:
            raise HTTPException(status_code=404, detail="Symbol not found")
        signal = ai_service.generate_signal(symbol.upper(), quote)
        return signal

    @app.get("/api/v1/ai/scenarios")
    async def get_scenarios(
        current_user: Optional[dict] = Depends(get_current_user),
    ):
        from app.services.ai_engine import ai_engine
        async with async_session() as session:
            scenarios = await ai_engine.generate_scenarios(session, (await get_provider()).get_market_overview())
        return {"scenarios": scenarios}

    @app.get("/api/v1/ai/regime")
    async def get_regime(
        current_user: Optional[dict] = Depends(get_current_user),
        provider: MarketDataProvider = Depends(get_provider),
    ):
        from app.services.ai_engine import ai_engine
        async with async_session() as session:
            overview = provider.get_market_overview()
            analysis = await ai_engine.analyze_market(session, overview)
        return analysis

    @app.get("/api/v1/ai/regime-enhanced")
    async def get_regime_enhanced(
        current_user: Optional[dict] = Depends(get_current_user),
        provider: MarketDataProvider = Depends(get_provider),
        symbol: str = Query("NIFTY", description="Symbol for indicators"),
    ):
        async with async_session() as session:
            overview = provider.get_market_overview()

            # Fetch technical indicators
            indicators = None
            try:
                ohlcv_data = provider.get_ohlcv(symbol.upper(), "1d", 20)
                if ohlcv_data:
                    quote = provider.get_quote(symbol.upper())
                    quote_dict = quote.to_dict() if quote else {"high": 0, "low": 0, "close": 0, "price": 0}
                    indicators = calculate_all_indicators(ohlcv_data, quote_dict)
            except Exception as e:
                logger.error(f"Indicators error for regime: {e}")

            analysis = await ai_engine.analyze_with_regime(session, overview, indicators)
        return analysis

    @app.get("/api/v1/ai/daily-analysis")
    async def get_daily_analysis(
        current_user: Optional[dict] = Depends(get_current_user),
        provider: MarketDataProvider = Depends(get_provider),
        symbol: str = Query("NIFTY", description="Symbol for analysis"),
    ):
        try:
            data = provider.get_daily_data(symbol.upper())
            if not data:
                raise HTTPException(status_code=404, detail="Daily data not found")
            vix = provider.get_vix()
            data["vix_price"] = vix.price if vix else 0
            analysis = ai_service.generate_daily_analysis(symbol.upper(), data)
            return analysis
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Daily analysis error: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate daily analysis")

    @app.get("/api/v1/ai/signals")
    async def get_ai_signals(
        current_user: Optional[dict] = Depends(get_current_user),
        symbol: Optional[str] = Query(None),
    ):
        from app.services.ai_engine import ai_engine
        async with async_session() as session:
            signals = await ai_engine.get_ai_signals(session, symbol)
        return {"signals": signals}

    @app.get("/api/v1/news")
    async def get_news(
        current_user: Optional[dict] = Depends(get_current_user),
        limit: int = Query(20),
    ):
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

    @app.get("/api/v1/collectors/status")
    async def collectors_status():
        return {
            "scheduler_running": scheduler._running,
            "collectors": ["market", "options", "news", "ai"],
        }

    start_time = time.time()
    return app


app = create_app()