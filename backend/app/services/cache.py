from __future__ import annotations

import json
import logging
from typing import Any, Optional

from config.config import load_config

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger("tradingai.cache")


class CacheService:
    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._config = load_config()
        self._enabled = False

    async def connect(self) -> None:
        if not REDIS_AVAILABLE:
            logger.warning("redis async not installed, caching disabled")
            return
        try:
            self._client = redis.from_url(
                self._config.get_redis_url(),
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            self._enabled = True
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, caching disabled")
            self._enabled = False

    async def get(self, key: str) -> Optional[Any]:
        if not self._enabled or not self._client:
            return None
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self._enabled or not self._client:
            return
        try:
            await self._client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")

    async def delete(self, key: str) -> None:
        if not self._enabled or not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")

    @property
    def enabled(self) -> bool:
        return self._enabled


cache_service = CacheService()