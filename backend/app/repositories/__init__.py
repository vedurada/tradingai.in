from app.repositories.market import MarketRepository
from app.repositories.signals import SignalRepository
from app.repositories.news import NewsRepository
from app.repositories.ai_signals import AISignalRepository
from app.repositories.scenarios import ScenarioRepository
from app.repositories.collector_logs import CollectorLogRepository

__all__ = [
    "MarketRepository",
    "SignalRepository",
    "NewsRepository",
    "AISignalRepository",
    "ScenarioRepository",
    "CollectorLogRepository",
]