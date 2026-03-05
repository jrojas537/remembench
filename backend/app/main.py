"""
Remembench — FastAPI Application Entry Point

Sets up middleware, registers route modules, and configures
the application for both development and production.

Routes:
    /api/v1/events       — Impact event CRUD
    /api/v1/yoy          — Year-over-Year comparisons
    /api/v1/ingestion    — Data ingestion triggers
    /api/v1/industries   — Industry registry (for frontend)
    /api/v1/health       — Health check
"""

from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging import get_logger, setup_logging

# Set up structured logging before anything else
setup_logging(settings.log_level)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown hooks."""
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
