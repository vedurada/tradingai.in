# TradingAI.in — Product Specification

## Overview
TradingAI.in is a financial market intelligence platform providing analytics and decision-support for Indian and global markets.

## Scope
- Market data (NIFTY, BANKNIFTY, SENSEX, VIX)
- Options analysis (chains, OI, PCR, Max Pain)
- Trading signals and strategies
- Stock intelligence
- Global markets
- AI market analysis (based on structured backend data)
- News and events
- Backtesting

## Architecture Rules
1. Frontend displays data, never calculates market values
2. Backend handles all calculations
3. No API secrets in frontend code
4. Data providers use abstract interfaces
5. PostgreSQL for persistence, Redis for real-time caching
6. FastAPI backend, Next.js frontend
7. Docker-based deployment
8. No trading execution — analytics only
9. AI output derived from backend data, never invented values
10. Market calculations NOT in React components

## Technology Stack
- Frontend: Next.js 14, React 18, TypeScript 5.5, Tailwind CSS 3.4
- Backend: FastAPI, Python 3.12, Pydantic
- Database: PostgreSQL 16, Redis 7
- Charts: TradingView Lightweight Charts (future)
- Deployment: Docker, docker-compose, Nginx
- CI/CD: GitHub Actions (future)

## Non-Goals
- Trading execution
- Broker integrations
- Real-time market data feeds (Phase 1 uses mock data)
- ML model serving (Phase 1)
- User authentication (Phase 1)