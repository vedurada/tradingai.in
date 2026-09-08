from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging
from typing import Optional

from config.config import load_config
from utils.logging import setup_logging
from app.providers.mock import MockMarketDataProvider, MarketDataProvider
from app.models.market import MarketOverviewResponse, HealthStatus

logger = setup_logging("tradingai-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TradingAI API...")
    yield
    logger.info("Shutting down TradingAI API...")

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

    @app.get("/api/v1/health", response_model=HealthStatus)
    async def health():
        return HealthStatus(
            status="healthy",
            version="1.0.0",
            uptime_seconds=time.time() - start_time,
            services={"database": "connected", "redis": "connected"},
        )

    @app.get("/api/v1/market/overview")
    async def market_overview():
        try:
            provider = MockMarketDataProvider()
            return provider.get_market_overview().to_dict()
        except Exception as e:
            logger.error(f"Market overview error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch market overview")

    @app.get("/api/v1/market/nifty")
    async def get_nifty():
        try:
            provider = MockMarketDataProvider()
            quote = provider.get_quote("NIFTY")
            if not quote:
                raise HTTPException(status_code=404, detail="NIFTY data not found")
            return quote.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"NIFTY error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch NIFTY data")

    @app.get("/api/v1/market/banknifty")
    async def get_banknifty():
        try:
            provider = MockMarketDataProvider()
            quote = provider.get_quote("BANKNIFTY")
            if not quote:
                raise HTTPException(status_code=404, detail="BANKNIFTY data not found")
            return quote.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"BANKNIFTY error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch BANKNIFTY data")

    @app.get("/api/v1/market/sensex")
    async def get_sensex():
        try:
            provider = MockMarketDataProvider()
            quote = provider.get_quote("SENSEX")
            if not quote:
                raise HTTPException(status_code=404, detail="SENSEX data not found")
            return quote.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SENSEX error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch SENSEX data")

    @app.get("/api/v1/market/vix")
    async def get_vix():
        try:
            provider = MockMarketDataProvider()
            vix = provider.get_vix()
            if not vix:
                raise HTTPException(status_code=404, detail="VIX data not found")
            return vix.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"VIX error: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch VIX data")

    start_time = time.time()
    return app

app = create_app()