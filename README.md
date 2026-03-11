# ⚡ Remembench (v1.0.0 Stable Core)

**YoY Performance Context Engine** — Surfaces weather, promotions, holidays, events, and disruptions that influence business performance in specific industries, markets, and date ranges.

[![Version: v1.0.0](https://img.shields.io/badge/Version-v1.0.0--Stable-success.svg)](#)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is in V1.0.0?

The `V1` branch represents the first fully stable, production-ready iteration of the Remembench core engine. 
*   **Enterprise Security Layer:** Integrated globally distributed Rate Limiting (`slowapi`) backed by Redis, explicitly preventing LLM token extortion attacks and database connection starvation on heavy geospatial aggregation routes.
*   **Zero-Latency Semantic Caching:** Appends an MD5 hash map interceptor in front of generative functions, serving duplicate AI briefings directly from Redis in ~0.05s (99% latency reduction) with 12-hour TTLs rather than paying Anthropic.
*   **Decoupled Architecture:** Solidified Next.js 16 frontend and FastAPI Python backend, communicating via REST.
*   **Automated Ingestion Pipeline:** Celery Beat orchestration integrating Open-Meteo, NOAA CDO, GDELT global news, specialized industry RSS feeds, and native `python-holidays` computations.
*   **Intelligent Deduplication:** Integrated semantic deduplication via local `SentenceTransformers` and rapid LLM batch classification via Anthropic Claude.
*   **Fully Documented Codebase:** 100% of major Python backend functions and Next.js frontend components are documented with architectural docstrings and JSDoc type hinting.

---

Remembench answers the critical data science question: **"What external context drove this sudden performance delta?"**

It asynchronously scrapes noisy internet data—weather sensors, RSS alerts, news scraping APIs, semantic web-searches via Exa and Tavily—and normalizes it via local embeddings and Anthropic Claude 3 Haiku LLM into a highly structured `ImpactEvent` topology.

By mapping previously abstract data points into hard analytical numbers (e.g. *Severity: 0.8*, *Category: Competitor Promotion*), operators can isolate noise from their raw YoY metric curves in an interactive Next.js dashboard.

📖 **Deep Dives:**
*   [Technical Architecture & LLM Data Flow](ARCHITECTURE.md)
*   [Developer & Contribution Guide](CONTRIBUTING.md)
*   [User Guide & Tutorials](docs/USER_GUIDE.md)
*   [Complete API Reference](docs/API_REFERENCE.md)

## Supported Industries

| Industry | Markets | Categories |
|----------|---------|------------|
| 📱 **Wireless Retail** | NYC, LA, Chicago, Houston, Dallas + 5 more | Weather, Competitor Promo, Outage, Holiday, News |
| 🍕 **Pizza — Full Service** | Detroit, Dearborn, Warren, Ann Arbor + 6 more | Weather, Food Safety, Delivery Disruption, Supply Chain, Labor |
| 🛵 **Pizza — Delivery** | Detroit metro area (10 markets) | Same as Full Service + Driver/Labor Shortage |
| 🍺 **Pizza — Bar & Restaurant** | Detroit metro area (10 markets) | Same + Liquor License, Sports Events |
| 📦 **Pizza — Carry-Out** | Detroit metro area (10 markets) | Same as Full Service |

> Adding a new industry is a single entry in `backend/app/industries.py` — no code changes required elsewhere.

## Architecture

Please reference [ARCHITECTURE.md](ARCHITECTURE.md) for a complete system diagram, caching flow (including Redis Idempotency and PostgreSQL zero-token deduplication), and a breakdown of how our adapters scale concurrently.

---

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
| `GET` | `/events/stats/summary` | Category and AI grouping statistics |
| `GET` | `/events/{event_id}` | Get single event by UUID |
| `GET` | `/events/briefing` | Generate an AI Executive Briefing from current filters |

**Query Parameters (GET /events/):**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `industry` | string | `wireless_retail` | Industry vertical key |
| `category` | string | — | Filter by semantic category (e.g. competitor_promo)|
| `source` | string | — | Filter by data source |
| `geo_label` | string | — | Filter by market (partial match) |
| `confidence` | string | — | Filter by LLM Confidence (e.g. HIGH, MEDIUM) |
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
| **Exa Search** | Yes | Neural historical web search & events | Global |
| **Tavily** | Yes | Live search & LLM-optimized parsing | Global, live |
| **Abstract API** | Yes | Public holidays (deprecated to native) | Global, annual |

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
