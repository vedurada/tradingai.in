from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import yfinance as yf

from app.models.market import (
    MarketOverview, MarketQuote, OHLCV, OptionChain, OptionContract,
    PCRData, MaxPainData, MarketStatus, VIXQuote,
)
from app.providers.base import MarketDataProvider

logger = logging.getLogger("tradingai.providers.yahoofinance")

SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "INDIA VIX": "^VIX",
    "USD/INR": "USDINR=X",
    "GOLD": "GOLD=NS",
    "CRUDE": "CL=F",
    "FINNIFTY": "^NSEFIN",
    "MIDCPNIFTY": "^NSEMDCP",
}

INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]

F&O_STOCKS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "INFY", "TCS", "LT",
    "AXISBANK", "ADANIENT", "BHARTIARTL", "BEL", "HDFC", "HDFCLIFE",
    "ICICIGI", "KOHLERBD", "M&M", "MARUTI", "NTPC", "POWERGRID",
    "TATAMOTORS", "TATASTEEL", "WIPRO", "TECHM", "BAJAJ-AUTO",
    "BAJFINANCE", "BAJAJFINSV", "SUNPHARMA", "ULTRACEMCO", "GRASIM",
    "HEROMOTOCO", "BPCL", "IOC", "ONGC", "GAIL", "COALINDIA",
    "CANBK", "PNB", "UNIONBANK", "KOTAKBANK", "INDUSINDBK",
    "DIVISLAB", "DRREDDY", "CIPLA", "ASHOKLEY", "TORNTPHARM",
    "BAJAJ-AUTO", "TVSMOTOR", "HEROMOTOCO", "EICHERMOT",
]

SECTOR_SYMBOLS = ["NIFTYIT", "NIFTYAUTO", "NIFTYFMCG", "NIFTYPHARMA", "NIFTYMETAL", "NIFTYREALTY", "NIFTYPSUBANK"]

FALLBACK_SECTOR_SYMBOLS = {
    "NIFTYIT": "^IXIC", "NIFTYAUTO": "^DJI", "NIFTYFMCG": "^GSPC",
    "NIFTYPHARMA": "^IXIC", "NIFTYMETAL": "^DJI", "NIFTYREALTY": "^GSPC",
    "NIFTYPSUBANK": "^IXIC",
}

GLOBAL_SYMBOLS = ["USD/INR", "GOLD", "CRUDE"]


def is_fo_stock(symbol: str) -> bool:
    return symbol.upper() in F&O_STOCKS


def get_all_symbols() -> list[str]:
    return INDICES + F&O_STOCKS


class YahooFinanceProvider(MarketDataProvider):
    def __init__(self) -> None:
        self._connected = False
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, float] = {}
        self._cache_ttl = 30
        self._daily_cache: dict[str, dict] = {}
        self._daily_cache_time: dict[str, float] = {}
        self._daily_cache_ttl = 3600

    def _cached(self, key: str, ttl: float = 30) -> Optional[Any]:
        if key in self._cache and key in self._cache_time:
            if datetime.now(timezone.utc).timestamp() - self._cache_time[key] < ttl:
                return self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_time[key] = datetime.now(timezone.utc).timestamp()

    def _to_market_quote(self, ticker: Any, symbol: str, name: str) -> Optional[MarketQuote]:
        try:
            info = ticker.info or {}
            prev_close = info.get("previousClose", 0)
            open_price = info.get("open", 0)
            high = info.get("dayHigh", 0)
            low = info.get("dayLow", 0)
            price = info.get("regularMarketPrice", info.get("currentPrice", 0))
            volume = info.get("volume", 0)

            if price == 0:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    row = hist.iloc[-1]
                    price = float(row["Close"])
                    open_price = float(row["Open"])
                    high = float(row["High"])
                    low = float(row["Low"])
                    volume = int(row["Volume"])

            if prev_close == 0:
                prev_close = price

            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            return MarketQuote(
                symbol=symbol, name=name, price=round(price, 2),
                change=round(change, 2), change_pct=round(change_pct, 2),
                open=round(open_price, 2), high=round(high, 2), low=round(low, 2),
                previous_close=round(prev_close, 2), volume=volume,
                timestamp=datetime.now(timezone.utc).isoformat(), market_status="Open",
            )
        except Exception as e:
            logger.error(f"Error parsing quote for {symbol}: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        yf_symbol = SYMBOL_MAP.get(symbol.upper())
        if not yf_symbol:
            return None
        try:
            ticker = yf.Ticker(yf_symbol)
            quote = self._to_market_quote(ticker, symbol.upper(), symbol.upper())
            if quote:
                self._set_cache(f"quote:{symbol.upper()}", quote)
            return quote
        except Exception as e:
            logger.error(f"Yahoo Finance quote error for {symbol}: {e}")
            cached = self._cached(f"quote:{symbol.upper()}")
            return cached

    def get_ohlcv(self, symbol: str, interval: str = "1d", limit: int = 100) -> list:
        yf_symbol = SYMBOL_MAP.get(symbol.upper())
        if not yf_symbol:
            return []
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="max", interval=interval)
            if hist.empty:
                return []
            ohlcv_list = []
            for idx, row in hist.tail(limit).iterrows():
                ohlcv_list.append(
                    OHLCV(
                        symbol=symbol.upper(), timeframe=interval, timestamp=idx,
                        open=float(row["Open"]), high=float(row["High"]),
                        low=float(row["Low"]), close=float(row["Close"]),
                        volume=int(row["Volume"]),
                    ).to_dict()
                )
            return ohlcv_list
        except Exception as e:
            logger.error(f"OHLCV error for {symbol}: {e}")
            return []

    def get_option_chain(self, symbol: str, expiry: str = "") -> Optional[OptionChain]:
        yf_symbol = SYMBOL_MAP.get(symbol.upper())
        if not yf_symbol:
            return None
        try:
            ticker = yf.Ticker(yf_symbol)
            expirations = ticker.options
            if not expirations:
                return None
            target_expiry = expiry if expiry else expirations[0]
            opt = ticker.option_chain(target_expiry)
            underlying_price = float(ticker.info.get("regularMarketPrice", 0))
            if underlying_price == 0:
                underlying_price = float(ticker.info.get("currentPrice", 0))

            calls = [
                OptionContract(
                    symbol=symbol.upper(), expiry=target_expiry, strike=float(row["strike"]),
                    option_type="CE", last_price=float(row["lastPrice"]),
                    open_interest=int(row["openInterest"]), change_in_oi=int(row.get("changeInOpenInterest", 0)),
                    volume=int(row["volume"]), implied_volatility=float(row.get("impliedVolatility", 0)),
                    bid=float(row["bid"]), ask=float(row["ask"]), delta=0, gamma=0, theta=0, vega=0,
                ).to_dict()
                for _, row in opt.calls.iterrows()
            ]
            puts = [
                OptionContract(
                    symbol=symbol.upper(), expiry=target_expiry, strike=float(row["strike"]),
                    option_type="PE", last_price=float(row["lastPrice"]),
                    open_interest=int(row["openInterest"]), change_in_oi=int(row.get("changeInOpenInterest", 0)),
                    volume=int(row["volume"]), implied_volatility=float(row.get("impliedVolatility", 0)),
                    bid=float(row["bid"]), ask=float(row["ask"]), delta=0, gamma=0, theta=0, vega=0,
                ).to_dict()
                for _, row in opt.puts.iterrows()
            ]

            chain = OptionChain(
                symbol=symbol.upper(), expiry=target_expiry, underlying_price=underlying_price,
                call_contracts=calls, put_contracts=puts,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._set_cache(f"option_chain:{symbol.upper()}:{target_expiry}", chain)
            return chain
        except Exception as e:
            logger.error(f"Option chain error for {symbol}: {e}")
            return None

    def get_market_status(self) -> MarketStatus:
        now = datetime.now(timezone.utc)
        hour = now.hour
        is_open = 9 <= hour < 15
        phase = "Open" if is_open else "Closed"
        return MarketStatus(is_open, phase, "09:15 IST", "15:30 IST", now.isoformat())

    def get_market_overview(self) -> MarketOverview:
        quotes = {}
        for sym in ["NIFTY", "BANKNIFTY", "SENSEX"]:
            q = self.get_quote(sym)
            if q:
                quotes[sym.lower()] = q

        vix_quote = self.get_vix()
        vix_quoted = vix_quote.to_dict() if vix_quote else {}

        return MarketOverview(
            nifty=quotes.get("nifty", MarketQuote("NIFTY", "NIFTY 50", 0, 0, 0, 0, 0, 0, 0, 0, "", "Closed")),
            banknifty=quotes.get("banknifty", MarketQuote("BANKNIFTY", "NIFTY Bank", 0, 0, 0, 0, 0, 0, 0, 0, "", "Closed")),
            sensex=quotes.get("sensex", MarketQuote("SENSEX", "S&P BSE Sensex", 0, 0, 0, 0, 0, 0, 0, 0, "", "Closed")),
            vix=VIXQuote(
                symbol=vix_quoted.get("symbol", "INDIA VIX"),
                name=vix_quoted.get("name", "India Volatility Index"),
                price=vix_quoted.get("price", 0), change=vix_quoted.get("change", 0),
                change_pct=vix_quoted.get("change_pct", 0), trend=vix_quoted.get("trend", "Stable"),
                risk_off=vix_quoted.get("risk_off", False), timestamp=vix_quoted.get("timestamp", ""),
            ),
            market_status="Open" if self.get_market_status().is_open else "Closed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_vix(self) -> Optional[VIXQuote]:
        cached = self._cached("vix")
        if cached:
            return cached
        try:
            ticker = yf.Ticker("^VIX")
            info = ticker.info or {}
            price = info.get("regularMarketPrice", info.get("currentPrice", 12.85))
            prev = info.get("previousClose", price + 0.15)
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0
            trend = "Declining" if change < 0 else "Rising" if change > 0 else "Stable"
            vix = VIXQuote(
                symbol="INDIA VIX", name="India Volatility Index", price=round(price, 2),
                change=round(change, 2), change_pct=round(change_pct, 2), trend=trend,
                risk_off=change < 0, timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._set_cache("vix", vix)
            return vix
        except Exception as e:
            logger.error(f"VIX error: {e}")
            return None

    def get_sector_indices(self) -> Optional[dict[str, MarketQuote]]:
        result = {}
        for sym in SECTOR_SYMBOLS:
            q = self.get_quote(sym)
            if not q and sym in FALLBACK_SECTOR_SYMBOLS:
                fallback = FALLBACK_SECTOR_SYMBOLS[sym]
                logger.warning(f"Symbol {sym} not found, using fallback {fallback}")
                q = self._fetch_quote_by_yf_symbol(fallback, sym)
            if q:
                result[sym] = q
        return result if result else None

    def _fetch_quote_by_yf_symbol(self, yf_symbol: str, display_symbol: str) -> Optional[MarketQuote]:
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info or {}
            price = info.get("regularMarketPrice", info.get("currentPrice", 0))
            if price == 0:
                return None
            prev_close = info.get("previousClose", price)
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            return MarketQuote(
                symbol=display_symbol, name=display_symbol, price=round(price, 2),
                change=round(change, 2), change_pct=round(change_pct, 2),
                open=round(price * 0.99, 2), high=round(price * 1.01, 2),
                low=round(price * 0.99, 2), previous_close=round(prev_close, 2),
                volume=0, timestamp=datetime.now(timezone.utc).isoformat(),
                market_status="Open" if self.get_market_status().is_open else "Closed",
            )
        except Exception as e:
            logger.error(f"Fallback quote error for {yf_symbol}: {e}")
            return None

    def get_global_markets(self) -> Optional[dict[str, MarketQuote]]:
        result = {}
        for sym in GLOBAL_SYMBOLS:
            q = self.get_quote(sym)
            if q:
                result[sym] = q
        return result if result else None

    def get_stock_quote(self, symbol: str) -> Optional[MarketQuote]:
        try:
            ticker = yf.Ticker(symbol.upper() + ".NS")
            return self._to_market_quote(ticker, symbol.upper(), symbol.upper())
        except Exception:
            return None

    def get_etf_quote(self, symbol: str) -> Optional[MarketQuote]:
        try:
            ticker = yf.Ticker(symbol.upper())
            return self._to_market_quote(ticker, symbol.upper(), symbol.upper())
        except Exception:
            return None

    def is_connected(self) -> bool:
        try:
            ticker = yf.Ticker("^NSEI")
            info = ticker.info or {}
            self._connected = "regularMarketPrice" in info or "currentPrice" in info
            return self._connected
        except Exception:
            self._connected = False
            return False

    def get_stock_quote(self, symbol: str) -> Optional[MarketQuote]:
        try:
            ticker = yf.Ticker(symbol.upper() + ".NS")
            return self._to_market_quote(ticker, symbol.upper(), symbol.upper())
        except Exception:
            return None

    def get_etf_quote(self, symbol: str) -> Optional[MarketQuote]:
        try:
            ticker = yf.Ticker(symbol.upper())
            return self._to_market_quote(ticker, symbol.upper(), symbol.upper())
        except Exception:
            return None

    def get_daily_data(
        self, symbol: str, period: str = "60d"
    ) -> dict[str, Any]:
        cached = self._cached(f"daily:{symbol}", ttl=3600)
        if cached:
            return cached
        yf_symbol = SYMBOL_MAP.get(symbol.upper()) or f"{symbol.upper()}.NS"
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period, interval="1d")
            if hist.empty:
                return {}
            data = self._to_daily_data(hist, symbol.upper())
            self._set_cache(f"daily:{symbol}", data, ttl=3600)
            return data
        except Exception as e:
            logger.error(f"Daily data error for {symbol}: {e}")
            return {}

    def get_intraday_data(
        self, symbol: str, interval: str = "15m", period: str = "5d"
    ) -> dict[str, Any]:
        yf_symbol = SYMBOL_MAP.get(symbol.upper()) or f"{symbol.upper()}.NS"
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                return {}
            return self._to_intraday_data(hist, symbol.upper(), interval)
        except Exception as e:
            logger.error(f"Intraday data error for {symbol}: {e}")
            return {}

    def get_multi_timeframe(
        self, symbol: str
    ) -> dict[str, dict]:
        return {
            "1d": self.get_daily_data(symbol, period="60d"),
            "1h": self.get_intraday_data(symbol, interval="1h", period="5d"),
            "15m": self.get_intraday_data(symbol, interval="15m", period="5d"),
            "5m": self.get_intraday_data(symbol, interval="5m", period="5d"),
            "1m": self.get_intraday_data(symbol, interval="1m", period="5d"),
        }

    def _to_daily_data(self, hist, symbol: str) -> dict:
        if hist.empty:
            return {}
        rows = []
        for idx, row in hist.iterrows():
            rows.append(
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )
        latest = rows[-1] if rows else {}
        prev = rows[-2] if len(rows) > 1 else {}
        prev_close = prev.get("close", latest.get("close", 0))
        gap_pct = (
            ((latest.get("open", 0) - prev_close) / prev_close * 100)
            if prev_close
            else 0
        )
        change_pct = (
            ((latest.get("close", 0) - prev_close) / prev_close * 100)
            if prev_close
            else 0
        )
        return {
            "symbol": symbol,
            "current_price": latest.get("close", 0),
            "previous_close": prev_close,
            "open": latest.get("open", 0),
            "high": latest.get("high", 0),
            "low": latest.get("low", 0),
            "gap_pct": round(gap_pct, 2),
            "day_change_pct": round(change_pct, 2),
            "volume": latest.get("volume", 0),
            "avg_volume": (
                sum(r["volume"] for r in rows[-20:]) / min(len(rows), 20)
                if rows
                else 0
            ),
            "relative_volume": (
                latest.get("volume", 0)
                / (sum(r["volume"] for r in rows[-20:]) / min(len(rows), 20))
                if rows and latest.get("volume")
                else 0
            ),
            "data": rows,
        }

    def _to_intraday_data(
        self, hist, symbol: str, interval: str
    ) -> dict:
        rows = []
        for idx, row in hist.iterrows():
            rows.append(
                {
                    "timestamp": idx.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )
        return {"symbol": symbol, "interval": interval, "data": rows}