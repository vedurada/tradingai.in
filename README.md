# TradingAI.in

A production-quality financial market intelligence platform for Indian and global markets.

## Architecture

- **Frontend**: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- **Backend**: FastAPI + Python 3.12 + Pydantic
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Deployment**: Docker + docker-compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.12+ (for local development)

### Docker (Recommended)

```bash
docker compose up -d
```

Then visit:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

### Local Development

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Database Setup
```bash
docker compose up -d postgres redis
psql -h localhost -U tradingai -d tradingai -f data/schema.sql
```

## Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Backend lint
cd backend
pip install flake8 mypy
flake8 app/ tests/
mypy app/ tests/

# Frontend build
cd frontend
npm run build
```

## Project Structure

```
tradingai/
├── frontend/          # Next.js + React + TypeScript
│   ├── src/
│   │   ├── app/       # Next.js pages & API routes
│   │   ├── components/ # Reusable components
│   │   ├── lib/       # Utilities
│   │   ├── types/     # TypeScript types
│   │   └── styles/    # Global styles
│   └── package.json
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── providers/ # Data provider abstraction
│   │   ├── services/  # Business logic
│   │   ├── analytics/ # Market calculations
│   │   └── main.py    # FastAPI app factory
│   ├── tests/         # Unit tests
│   └── requirements.txt
├── docker-compose.yml
├── data/schema.sql
└── docs/
    ├── PRODUCT.md
    ├── ARCHITECTURE.md
    └── DATABASE.md
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET /api/v1/health | Health check |
| GET /api/v1/market/overview | Full market overview |
| GET /api/v1/market/nifty | NIFTY data |
| GET /api/v1/market/banknifty | BANKNIFTY data |
| GET /api/v1/market/sensex | SENSEX data |
| GET /api/v1/market/vix | India VIX data |

## Environment Variables

Create a `.env` file:

```env
ENVIRONMENT=development
DEBUG=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tradingai
DB_USER=tradingai
DB_PASSWORD=tradingai
REDIS_HOST=localhost
REDIS_PORT=6379
API_VERSION=v1
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

## License

Internal use only. TradingAI is an analytics and decision-support platform — not a trading execution system.