# TradingAI.in — Implementation Specification

## Architecture

```
                  Browser
                     │
                     ▼
              TradingAI UI (Next.js)
                     │
                     ▼
               API Layer (FastAPI)
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
   Market         Options         News
   Data           Data            Data
      │              │              │
      └──────────────┼──────────────┘
                     ▼
               Data Engine
                     │
          ┌──────────┴──────────┐
          ▼                      ▼
       Redis                  PostgreSQL
          │                      │
          └──────────┬───────────┘
                     ▼
                  AI/ML Engine
```

## Data Provider Abstraction

All data flows through providers. Frontend never knows the source.

```
Provider (YahooFinance / RBI / FRED / NewsAPI)
    │
    ▼
Collector (scheduled)
    │
    ▼
PostgreSQL + Redis cache
    │
    ▼
API Layer (FastAPI)
    │
    ▼
Frontend (Next.js)
```

## Tech Stack

- **Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts
- **Backend:** FastAPI, SQLAlchemy async, asyncpg
- **Cache:** Redis
- **Data:** yfinance, NewsAPI, FRED, RBI
- **Deploy:** Docker Compose, VM (129.159.224.81)

## Database Schema

```sql
-- Instruments
CREATE TABLE instruments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    exchange VARCHAR(20),
    sector VARCHAR(100),
    instrument_type VARCHAR(20),
    is_active BOOLEAN DEFAULT true
);

-- Market quotes
CREATE TABLE market_quotes (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price FLOAT NOT NULL,
    change FLOAT,
    change_pct FLOAT,
    open_price FLOAT,
    high FLOAT,
    low FLOAT,
    previous_close FLOAT,
    volume BIGINT,
    vwap FLOAT,
    rsi FLOAT,
    ema20 FLOAT,
    ema50 FLOAT,
    ema200 FLOAT,
    market_status VARCHAR(20),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- OHLCV
CREATE TABLE ohlcv (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10),
    timestamp TIMESTAMPTZ NOT NULL,
    open FLOAT, high FLOAT, low FLOAT, close FLOAT, volume FLOAT
);

-- Options
CREATE TABLE option_contracts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20), expiry DATE, strike FLOAT,
    option_type VARCHAR(2), last_price FLOAT,
    open_interest BIGINT, change_in_oi BIGINT, volume BIGINT,
    implied_volatility FLOAT, bid FLOAT, ask FLOAT,
    delta FLOAT, gamma FLOAT, theta FLOAT, vega FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- AI signals
CREATE TABLE ai_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20), signal_type VARCHAR(20),
    confidence FLOAT, price_target FLOAT, stop_loss FLOAT,
    rationale TEXT, is_active BOOLEAN DEFAULT true, timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- News
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500), source VARCHAR(200), url TEXT,
    summary TEXT, sentiment VARCHAR(20), category VARCHAR(50),
    published_at TIMESTAMPTZ, timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Scenarios
CREATE TABLE scenarios (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20), condition TEXT,
    scenario_type VARCHAR(20), probability FLOAT,
    description TEXT, timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE, password_hash VARCHAR(256),
    role VARCHAR(20) DEFAULT 'user', created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## API Endpoints

```
GET  /api/v1/market/overview
GET  /api/v1/market/{symbol}
GET  /api/v1/market/{symbol}/ohlcv
GET  /api/v1/market/{symbol}/option-chain
GET  /api/v1/market/screener
GET  /api/v1/options/nifty
GET  /api/v1/options/chain
GET  /api/v1/options/intelligence
GET  /api/v1/options/pcr
GET  /api/v1/options/maxpain
GET  /api/v1/stocks
GET  /api/v1/stocks/screener
GET  /api/v1/etfs
GET  /api/v1/etfs/compare
GET  /api/v1/news
GET  /api/v1/news/market-moving
GET  /api/v1/ai/market-view
GET  /api/v1/ai/scenarios
GET  /api/v1/ai/explain/{symbol}
POST /api/v1/auth/login
POST /api/v1/auth/register
GET  /api/v1/health
```

## Collector Jobs (Redis-scheduled)

```
MarketCollector:   every 1 min  → market_quotes, ohlcv
OptionsCollector:  every 5 min  → option_contracts
NewsCollector:     every 15 min → news_articles
AIAnalyzer:        every 5 min  → ai_signals, scenarios
```

## Page-by-Page UI Spec

### 1. HOME (`/`)
- Market status banner (OPEN/CLOSED + time)
- Index ticker row (NIFTY, BANKNIFTY, SENSEX, VIX)
- AI Market Regime card (BULLISH/BEARISH/NEUTRAL + confidence)
- Why? checklist (VWAP, EMA, breadth, VIX, PCR)
- View invalidation warnings
- NIFTY intraday mini chart
- Options positioning summary (PCR, Max Pain, Support/Resistance)
- Market breadth bar (Advancing/Declining)
- AI news feed

### 2. MARKETS (`/markets`)
- Tab: Indices | Sector Indices | Stocks | Global
- Indices table: NIFTY 50, BANKNIFTY, FINNIFTY, MIDCAP, SENSEX, NIFTY IT, AUTO, BANK, FMCG, PHARMA, METAL, REALTY, PSU BANK
- Columns: Price, Change, %Ch, High, Low, Open, Prev Close, VWAP, 52W H/L, Volume, RSI, EMA20/50/200
- AI interpretation per index: Trend, Momentum, Volatility, Breadth, Options sentiment
- Click any index → NIFTY dashboard page

### 3. OPTIONS (`/options`)
- Spot, Expiry selector
- PCR, OI PCR, Volume PCR, Max Pain, ATM, IV, VIX
- CALLS / PUTS chain table: OI, ΔOI, IV, LTP, STRIKE, LTP, IV, ΔOI, OI
- Highlights: Highest Call OI, Highest Put OI, Largest ΔOI, Support/Resistance zones, IV expansion/contraction
- Options Intelligence panel: Put OI concentration, Call OI concentration, PCR, OI trend, IV trend, interpretation

### 4. TRADING (`/trading`)
- NIFTY Intraday Intelligence: Regime, Trend, Momentum, Volatility, Breadth, Options
- Key levels: Resistance, Current, Support, VWAP
- Scenario engine: IF price > X → bullish continuation, IF X-Y → range, IF < X → bearish
- Signals list with confidence
- Backtest module (later)

### 5. STOCKS (`/stocks`)
- Screener: Search, Market(NSE/BSE), Sector, Market Cap, Trend filters, RSI range, Above EMA200, Volume > Avg
- Results table: Stock, Price, %, RSI, Trend, Volume, AI View
- Stock detail page (later)

### 6. ETFs (`/etfs`)
- ETF Center: NIFTY ETFs, NEXT 50, MIDCAP, SMALLCAP, BANK, IT, GOLD, SILVER, INTERNATIONAL
- Per ETF: Price, AUM, Expense Ratio, Tracking Diff, Volume, Liquidity, 1M/6M/1Y/3Y/5Y returns
- ETF comparison table

### 7. NEWS (`/news`)
- Market Moving section with AI summaries
- Categories: Market, RBI, Earnings, Global, Commodities, Currency, Geopolitics, Corporate, IPO
- Per article: Title, source, time, Why it matters, Potential impact, Related stocks

### 8. AI (`/ai`)
- AI Market Intelligence dashboard
- Regime gauge (BULLISH/BEARISH/NEUTRAL + score)
- Dimension bars: Trend, Momentum, Breadth, Volatility, Options
- Why? checklist
- Warning signs
- View invalidation triggers

### 9. RESEARCH (`/research`)
- ETF/index fund guide
- Options risk management guide
- Strategy documentation

## Build Order

Phase 1 — Foundation (Week 1-2)
  Data provider abstraction, PostgreSQL, Redis, market collectors, REST API, auth, logging/monitoring

Phase 2 — Core UI (Week 3-4)
  New Home, Markets dashboard, Stocks screener, ETFs page

Phase 3 — Options (Week 5-6)
  Option chain, OI, PCR, Max pain, IV, Options Intelligence

Phase 4 — AI (Week 7-8)
  Market regime, trend/momentum/volatility engines, scenario engine, explainable AI

Phase 5 — Research (Week 9-10)
  News with AI summarization, global markets, macro, corporate actions

Phase 6 — Strategy Module (Week 11-12)
  HSS strategy integrated as one Trading Strategy module
