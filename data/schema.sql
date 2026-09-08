-- Initial database schema for TradingAI.in

CREATE TABLE IF NOT EXISTS instruments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'index',
    exchange VARCHAR(10) NOT NULL DEFAULT 'NSE',
    segment VARCHAR(20) NOT NULL DEFAULT 'equity',
    lot_size INTEGER DEFAULT 1,
    tick_size DECIMAL(10, 5) DEFAULT 0.05,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_instruments_symbol ON instruments(symbol);
CREATE INDEX idx_instruments_exchange ON instruments(exchange);
CREATE INDEX idx_instruments_active ON instruments(is_active);

CREATE TABLE IF NOT EXISTS market_quotes (
    id BIGSERIAL PRIMARY KEY,
    instrument_id INTEGER REFERENCES instruments(id),
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(15, 5) NOT NULL,
    change DECIMAL(15, 5),
    change_pct DECIMAL(10, 4),
    open DECIMAL(15, 5),
    high DECIMAL(15, 5),
    low DECIMAL(15, 5),
    previous_close DECIMAL(15, 5),
    volume BIGINT DEFAULT 0,
    open_interest BIGINT DEFAULT 0,
    bid_price DECIMAL(15, 5),
    ask_price DECIMAL(15, 5),
    market_status VARCHAR(20) DEFAULT 'Closed',
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_market_quotes_symbol ON market_quotes(symbol);
CREATE INDEX idx_market_quotes_timestamp ON market_quotes(timestamp DESC);
CREATE INDEX idx_market_quotes_recent ON market_quotes(symbol, timestamp DESC);

CREATE TABLE IF NOT EXISTS ohlcv (
    id BIGSERIAL PRIMARY KEY,
    instrument_id INTEGER REFERENCES instruments(id),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(15, 5) NOT NULL,
    high DECIMAL(15, 5) NOT NULL,
    low DECIMAL(15, 5) NOT NULL,
    close DECIMAL(15, 5) NOT NULL,
    volume DECIMAL(20, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE INDEX idx_ohlcv_symbol_timeframe ON ohlcv(symbol, timeframe);
CREATE INDEX idx_ohlcv_symbol_timeframe_time ON ohlcv(symbol, timeframe, timestamp DESC);
CREATE INDEX idx_ohlcv_timeframe_time ON ohlcv(timeframe, timestamp DESC);

CREATE TABLE IF NOT EXISTS option_contracts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    expiry VARCHAR(20) NOT NULL,
    strike DECIMAL(15, 2) NOT NULL,
    option_type VARCHAR(2) NOT NULL CHECK (option_type IN ('CE', 'PE')),
    last_price DECIMAL(15, 5),
    open_interest BIGINT DEFAULT 0,
    change_in_oi BIGINT DEFAULT 0,
    volume BIGINT DEFAULT 0,
    implied_volatility DECIMAL(10, 4),
    bid DECIMAL(15, 5),
    ask DECIMAL(15, 5),
    delta DECIMAL(10, 6),
    gamma DECIMAL(10, 6),
    theta DECIMAL(10, 6),
    vega DECIMAL(10, 6),
    greeks_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, expiry, strike, option_type)
);

CREATE INDEX idx_option_contracts_symbol_expiry ON option_contracts(symbol, expiry);
CREATE INDEX idx_option_contracts_symbol_expiry_strike ON option_contracts(symbol, expiry, strike);
CREATE INDEX idx_option_contracts_symbol_expiry_type ON option_contracts(symbol, expiry, option_type);

CREATE TABLE IF NOT EXISTS option_chain_snapshots (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    expiry VARCHAR(20) NOT NULL,
    underlying_price DECIMAL(15, 5) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    call_contracts JSONB DEFAULT '[]',
    put_contracts JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_option_chain_snapshots_symbol_expiry ON option_chain_snapshots(symbol, expiry);
CREATE INDEX idx_option_chain_snapshots_timestamp ON option_chain_snapshots(timestamp DESC);

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('BUY', 'SELL', 'HOLD', 'WATCH')),
    confidence DECIMAL(5, 2) DEFAULT 0.0,
    entry_price DECIMAL(15, 5),
    target_price DECIMAL(15, 5),
    stop_loss DECIMAL(15, 5),
    strategy VARCHAR(50),
    timeframe VARCHAR(10),
    status VARCHAR(20) DEFAULT 'OPEN',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_direction ON signals(direction);
CREATE INDEX idx_signals_status ON signals(status);

CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    headline VARCHAR(500) NOT NULL,
    source VARCHAR(100),
    category VARCHAR(50),
    published_at TIMESTAMP,
    url VARCHAR(500),
    related_symbols TEXT[],
    related_sectors TEXT[],
    ai_summary TEXT,
    sentiment VARCHAR(20),
    impact_score DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_news_published ON news(published_at DESC);
CREATE INDEX idx_news_symbols ON news USING GIN(related_symbols);
CREATE INDEX idx_news_category ON news(category);