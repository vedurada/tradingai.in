from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "tradingai"
    username: str = "tradingai"
    password: str = "tradingai"
    url: str = field(default="postgresql+asyncpg://tradingai:tradingai@localhost:5432/tradingai")

    def __post_init__(self) -> None:
        self.url = f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    url: str = field(default="redis://localhost:6379/0")

@dataclass
class AppConfig:
    environment: str = "development"
    debug: bool = True
    api_version: str = "v1"
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    market_refresh_interval: int = 5
    option_refresh_interval: int = 30
    news_refresh_interval: int = 300
    ai_refresh_interval: int = 300
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)

    def get_redis_url(self) -> str:
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.database}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.database}"

    def get_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.database.username}:{self.database.password}@{self.database.host}:{self.database.port}/{self.database.database}"

def load_config() -> AppConfig:
    config = AppConfig()
    config.environment = os.getenv("ENVIRONMENT", "development")
    config.debug = os.getenv("DEBUG", "true").lower() == "true"
    config.api_version = os.getenv("API_VERSION", "v1")
    config.database.host = os.getenv("DB_HOST", "localhost")
    config.database.port = int(os.getenv("DB_PORT", "5432"))
    config.database.database = os.getenv("DB_NAME", "tradingai")
    config.database.username = os.getenv("DB_USER", "tradingai")
    config.database.password = os.getenv("DB_PASSWORD", "tradingai")
    config.redis.host = os.getenv("REDIS_HOST", "localhost")
    config.redis.port = int(os.getenv("REDIS_PORT", "6379"))
    config.redis.password = os.getenv("REDIS_PASSWORD")
    config.log_level = os.getenv("LOG_LEVEL", "INFO")
    return config