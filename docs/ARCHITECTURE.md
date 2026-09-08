# Architecture Document

## System Architecture

```
┌─────────────────────────┐
│   Next.js + React       │ ← Frontend (Port 3000)
│   TypeScript + Tailwind │
└───────────┬─────────────┘
            │ REST / WebSocket
┌───────────▼─────────────┐
│   FastAPI               │ ← Backend (Port 8000)
│   Python 3.12           │
└──┬──────┬──────┬──────┬──┘
   │      │      │      │
   ▼      ▼      ▼      ▼
 Market  Options  News  Analytics
 Provider          Service
   │
   ▼
┌──────────┐    ┌──────────┐
│PostgreSQL│    │  Redis   │ ← Caching / Real-time
│(Persist) │    │(Latest)  │
└──────────┘    └──────────┘
```

## Data Flow

1. External API → Data Collector → Normalizer → Redis (latest) + PostgreSQL (historical)
2. Frontend requests → FastAPI → Redis (cached) or PostgreSQL (historical)
3. Frontend → WebSocket (real-time updates when implemented)

## Key Principles

- Separation of concerns: UI ≠ Logic ≠ Data
- Provider abstraction for data sources
- Environment variables for all secrets
- Type hints everywhere
- Structured logging
- API versioning (/api/v1/)
- CORS properly configured

## Component Boundaries

- `frontend/src/components/` - React components (pure display)
- `backend/app/` - FastAPI application
- `backend/app/providers/` - Data provider abstraction
- `backend/app/services/` - Business logic
- `backend/app/analytics/` - Market calculations
- `data/` - Database schema and migrations