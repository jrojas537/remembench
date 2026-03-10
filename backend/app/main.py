"""
Remembench — FastAPI Application Entry Point

This module serves as the functional brain of the FastAPI web server. It is primarily
responsible for 3 core operations:
1. Context Lifecycle: Enforcing a globally pooled, high-capacity asynchronous 
   HTTP client (`httpx.AsyncClient`) across all scraping adapters to circumvent socket 
   starvation.
2. Middleware Instantiation: Activating CORS origins (via `frontend` configurations) 
   and OWASP strict security headers (`X-XSS-Protection`, etc.).
3. Semantic Routing: Exposing endpoints bounded strictly to `/api/v1` namespace 
   across specialized domains ranging from AI classification (`impact_events`) 
   to ETL execution (`ingestion`).

Routes:
    /api/v1/events       — YoY Impact event CRUD & AI Briefings
    /api/v1/yoy          — Year-over-Year geospatial comparison engine
    /api/v1/ingestion    — Manual data ingestion triggers for the Celery tasks
    /api/v1/industries   — Static industry registry endpoints
    /api/v1/health       — Database / Postgres health check verification
"""

from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.logging import get_logger, setup_logging

# Set up structured logging before anything else
setup_logging(settings.log_level)
logger = get_logger("main")

# ---------------------------------------------------------------------------
# Global Rate Limiting Architecture
# ---------------------------------------------------------------------------
# We leverage `slowapi` to inject sliding-window rate limit checks before 
# yielding to the asynchronous router stack. By pushing the memory tracker
# onto the robust Redis cluster (`settings.redis_url`) rather than an in-memory 
# Python dict, we ensure state is synchronized across all Uvicorn worker threads 
# and horizontally scaled Docker replicas natively.
limiter = Limiter(
    key_func=get_remote_address, 
    default_limits=["120/minute"], 
    storage_uri=settings.redis_url
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle — startup and shutdown hooks.
    
    Instantiates a single global `httpx.AsyncClient` bounded directly to the active 
    event loop here. This definitively prevents socket starvation and solves the 
    'Event loop is closed' unhandled exceptions caused by adapters lazily evaluating
    disjoint thread pools. 
    """
    logger.info(
        "app_starting",
        app_name=settings.app_name,
        debug=settings.debug,
    )
    
    # Initialize global high-capacity HTTP client for downstream adapters
    # Limits caps active concurrent DB/API scrapes preventing socket starvation
    app.state.http_client = httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=50, 
            max_keepalive_connections=15
        ),
        timeout=httpx.Timeout(30.0, read=60.0)
    )
    
    yield
    
    logger.info("app_shutting_down")
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()


# --- Application ---
app = FastAPI(
    title=settings.app_name,
    description=(
        "Remembench — YoY Performance Context Engine. "
        "Surfaces weather, promotions, holidays, events, and disruptions "
        "that impact specific industries, markets, and date ranges."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# --- CORS Middleware ---
# Origins are configurable via CORS_ORIGINS env var (see config.py)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate Limiting & Protection Middleware
# ---------------------------------------------------------------------------
# App state injection is required by FastAPI to execute global constraints.
# `SlowAPIMiddleware` intercepts requests pre-routing and returns HTTP 429 bounds
# gracefully explicitly preventing brute-force database exhaustion loops.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Adds standard OWASP recommended security headers to all responses."""
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# --- Route Registration ---
from app.routes import auth, users, billing, impact_events, yoy_comparison, ingestion, health, industries  # noqa: E402
from app.api.v1 import agent

app.include_router(
    agent.router,
    prefix=settings.api_prefix,
)

app.include_router(
    auth.router,
    prefix=f"{settings.api_prefix}/auth",
    tags=["Authentication"],
)
app.include_router(
    users.router,
    prefix=f"{settings.api_prefix}/users",
    tags=["Users"],
)
app.include_router(
    billing.router,
    prefix=f"{settings.api_prefix}/billing",
    tags=["Billing"],
)
app.include_router(
    impact_events.router,
    prefix=f"{settings.api_prefix}/events",
    tags=["Impact Events"],
)
app.include_router(
    yoy_comparison.router,
    prefix=f"{settings.api_prefix}/yoy",
    tags=["YoY Comparison"],
)
app.include_router(
    ingestion.router,
    prefix=f"{settings.api_prefix}/ingestion",
    tags=["Data Ingestion"],
)
app.include_router(
    industries.router,
    prefix=f"{settings.api_prefix}/industries",
    tags=["Industries"],
)
app.include_router(
    health.router,
    prefix=settings.api_prefix,
    tags=["Health"],
)
