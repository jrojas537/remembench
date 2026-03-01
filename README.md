# ⚡ Remembench

**YoY Performance Context Engine** — Surfaces weather, promotions, holidays, events, and disruptions that influence business performance in specific industries, markets, and date ranges.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What It Does

Remembench answers the question: **"What happened during this period that could explain the performance delta?"**

It ingests contextual data from multiple sources (weather APIs, news feeds, holiday calendars, competitor promotions) and normalizes everything into **Impact Events** — a universal schema that works across industries. Analysts use these events to:

- Adjust YoY comparisons for factors beyond their control
- Forecast more accurately by understanding historical context
- Identify patterns (e.g., Super Bowl Sunday = +40% pizza delivery)
- Avoid false conclusions from raw YoY metrics

## Supported Industries

| Industry | Markets | Categories |
|----------|---------|------------|
| 📱 **Wireless Retail** | NYC, LA, Chicago, Houston, Dallas + 5 more | Weather, Competitor Promo, Outage, Holiday, News |
| 🍕 **Pizza — Full Service** | Detroit, Dearborn, Warren, Ann Arbor + 6 more | Weather, Food Safety, Delivery Disruption, Supply Chain, Labor |
| 🛵 **Pizza — Delivery** | Detroit metro area (10 markets) | Same as Full Service + Driver/Labor Shortage |
| 🍺 **Pizza — Bar & Restaurant** | Detroit metro area (10 markets) | Same + Liquor License, Sports Events |
| 📦 **Pizza — Carry-Out** | Detroit metro area (10 markets) | Same as Full Service |

> Adding a new industry is a single entry in `backend/app/industries.py` — no code changes required elsewhere.

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│    Nginx    │────▶│   FastAPI    │
│  Dashboard  │     │   Reverse   │     │   Backend    │
│  (port 3000)│     │   Proxy     │     │  (port 8000) │
└─────────────┘     └─────────────┘     └──────┬───────┘
                                               │
                    ┌──────────────────────────┤
                    │                          │
              ┌─────▼─────┐            ┌───────▼──────┐
              │  PostgreSQL │            │    Redis     │
              │  + PostGIS  │            │   (Celery)   │
              │  (port 5432)│            │  (port 6379) │
              └─────────────┘            └──────┬───────┘
                                               │
                                    ┌──────────┤──────────┐
                                    │          │          │
                              ┌─────▼──┐ ┌────▼───┐ ┌───▼────┐
                              │ Worker │ │  Beat  │ │Backfill│
                              │(nightly)│ │(sched) │ │(manual)│
                              └────────┘ └────────┘ └────────┘
```

### Data Pipeline

```
  Open-Meteo ──┐
  NOAA CDO  ───┤
  GDELT     ───┼──▶ IngestionService ──▶ Dedup ──▶ PostgreSQL
  RSS Feeds ───┤        │                              │
  Holidays  ───┘    industry-aware              ImpactEvents table
                    queries/classification
```

### Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| **Industry Registry** | `backend/app/industries.py` | Centralized config for all verticals |
| **Adapters** | `backend/app/adapters/` | Source-specific data fetching |
| **Ingestion Service** | `backend/app/services/` | Orchestration + dedup + batch upsert |
| **Impact Events API** | `backend/app/routes/anomaly_events.py` | CRUD endpoints |
| **YoY Comparison** | `backend/app/routes/yoy_comparison.py` | Cross-year analysis engine |
| **Celery Tasks** | `backend/app/tasks.py` | Nightly, weekly, and backfill jobs |
| **Dashboard** | `frontend/app/page.js` | Interactive industry-aware UI |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Production (Docker)

```bash
# 1. Clone and configure
git clone <repo-url> && cd Remembench
cp .env.example .env
# Edit .env with your API keys (NOAA_CDO_TOKEN, ABSTRACT_API_KEY)

# 2. Launch all services
docker compose up -d --build

# 3. Access
open http://localhost       # Dashboard
open http://localhost/api/docs  # API Documentation (Swagger)
```

### Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install && npm run dev
```

---

## API Reference

**Base URL:** `/api/v1`

### Impact Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/events/` | Create a new impact event |
| `GET` | `/events/` | List events with filters |
| `GET` | `/events/stats/summary` | Category statistics |
| `GET` | `/events/{event_id}` | Get single event by UUID |

**Query Parameters (GET /events/):**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `industry` | string | `wireless_retail` | Industry vertical key |
| `category` | string | — | Filter by category |
| `source` | string | — | Filter by data source |
| `geo_label` | string | — | Filter by market (partial match) |
| `limit` | int | 50 | Max results (1–500) |
| `offset` | int | 0 | Pagination offset |

### YoY Comparison

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/yoy/compare` | Compare periods across years |

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `start_date` | datetime | — | Start of target period |
| `end_date` | datetime | — | End of target period |
| `lookback_years` | int | 1 | Years to look back (1–5) |
| `industry` | string | `wireless_retail` | Industry vertical |
| `geo_label` | string | — | Filter by market |
| `categories` | list | — | Filter by categories |

### Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingestion/run` | Manual ingestion trigger |
| `POST` | `/ingestion/backfill` | Async historical backfill |

### Industries

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/industries/` | List all industries (grouped) |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check + DB status |

---

## Data Sources

| Source | API Key Required | Data Type | Coverage |
|--------|:---:|-----------|----------|
| **Open-Meteo** | No | Historical weather (temp, snow, rain, wind) | Global, daily |
| **NOAA CDO** | Yes (free) | US weather stations | US, daily |
| **GDELT Project** | No | Global news + events | Global, real-time |
| **RSS Feeds** | No | Industry news (carrier/restaurant) | Per-industry |
| **Abstract API** | Yes (free) | Public holidays | Global, annual |

---

## Testing

```bash
cd backend
pip install pytest pytest-asyncio httpx

# Run full suite
python -m pytest tests/ -v

# Run specific module
python -m pytest tests/test_adapters.py -v
python -m pytest tests/test_industries.py -v
```

**Test Coverage (112 tests):**

| Module | Tests | What's Covered |
|--------|------:|---------------|
| `test_industries.py` | 33 | Registry, markets, feeds, helpers |
| `test_adapters.py` | 33 | Weather thresholds, null handling, severity |
| `test_schemas.py` | 22 | Validation boundaries, edge cases |
| `test_routes.py` | 14 | API integration with mocked DB |
| `test_services.py` | 10 | Dedup algorithm, holiday severity |

---

## Configuration

All configuration is via environment variables. See `.env.example` for the complete list.

| Variable | Required | Default | Description |
|----------|:---:|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `REDIS_URL` | Yes | — | Redis connection for Celery |
| `NOAA_CDO_TOKEN` | No | — | NOAA Climate Data Online API key |
| `ABSTRACT_API_KEY` | No | — | Abstract API holidays key |
| `CORS_ORIGINS` | No | `localhost:3000` | Allowed CORS origins |
| `LOG_LEVEL` | No | `INFO` | Logging level |

---

## Project Structure

```
Remembench/
├── backend/
│   ├── app/
│   │   ├── adapters/           # Data source adapters
│   │   │   ├── base.py         #   Base adapter with retry logic
│   │   │   ├── open_meteo.py   #   Weather (Open-Meteo API)
│   │   │   ├── noaa_cdo.py     #   Weather (NOAA stations)
│   │   │   ├── gdelt.py        #   News & events (GDELT)
│   │   │   ├── carrier_rss.py  #   Industry RSS feeds
│   │   │   └── holidays.py     #   Public holidays
│   │   ├── routes/             # API endpoints
│   │   │   ├── anomaly_events.py   # Impact event CRUD
│   │   │   ├── yoy_comparison.py   # YoY analysis engine
│   │   │   ├── ingestion.py        # Manual ingestion triggers
│   │   │   ├── industries.py       # Industry registry API
│   │   │   └── health.py           # Health check
│   │   ├── services/           # Business logic
│   │   │   └── __init__.py     #   IngestionService (orchestration)
│   │   ├── config.py           # Pydantic settings
│   │   ├── database.py         # Async SQLAlchemy session
│   │   ├── industries.py       # Industry registry (central config)
│   │   ├── logging.py          # Structlog configuration
│   │   ├── main.py             # FastAPI application entry
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   └── tasks.py            # Celery worker tasks
│   ├── tests/                  # Full test suite (112 tests)
│   ├── requirements.txt        # Python dependencies
│   └── pyproject.toml          # Pytest configuration
├── frontend/
│   ├── app/
│   │   ├── layout.js           # Next.js layout + metadata
│   │   ├── page.js             # Dashboard (industry switcher, charts)
│   │   └── globals.css         # Design system + category badges
│   └── package.json
├── nginx/nginx.conf            # Reverse proxy config
├── docker-compose.yml          # Full-stack deployment
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## Automated Scheduling

| Task | Schedule | Description |
|------|----------|-------------|
| **Nightly Ingestion** | 2:00 AM UTC | Pulls yesterday's data for all industries + markets |
| **Weekly Deep Sync** | Monday 3:00 AM UTC | Re-ingests past 7 days (catches delayed data) |
| **On-Demand Backfill** | Manual | Historical analysis via API or Celery |

---

## Adding a New Industry

1. Define markets, queries, and feeds in `backend/app/industries.py`
2. Add category badge styles in `frontend/app/globals.css`
3. Add industry option + demo data in `frontend/app/page.js`
4. That's it — adapters, routes, and tasks are industry-agnostic

---

## License

MIT
