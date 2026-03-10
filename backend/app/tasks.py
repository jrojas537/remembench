"""
Remembench — Celery Worker & Scheduled Tasks

Handles the automated data pipeline:
- Nightly ingestion: pulls yesterday's data for all industries/markets
- Weekly deep sync: re-ingests the past 7 days to catch delayed data
- On-demand backfill: triggered via API for historical analysis

Tasks iterate over the industry registry to ensure all configured
industries and their markets are covered automatically.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from app.config import settings

# ---------------------------------------------------------------------------
#  Celery App Configuration
# ---------------------------------------------------------------------------

celery_app = Celery(
    "remembench",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,             # Re-queue failed tasks
    worker_prefetch_multiplier=1,    # One task at a time per worker
)

# ---------------------------------------------------------------------------
#  Scheduled Tasks — Celery Beat
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    # Pull yesterday's data for all industries at 2 AM UTC
    "nightly-ingestion": {
        "task": "app.tasks.run_nightly_ingestion",
        "schedule": crontab(hour=2, minute=0),
    },
    # Re-ingest past 7 days every Sunday to catch delayed updates
    "weekly-deep-sync": {
        "task": "app.tasks.run_weekly_deep_sync",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
    },
}

task_logger = get_task_logger(__name__)


# ---------------------------------------------------------------------------
#  Async Runner
# ---------------------------------------------------------------------------

def _run_async(coro_func, *args, **kwargs):
    """
    Run an async coroutine function from a synchronous Celery task securely.

    Uses asyncio.run() for proper cleanup (Python 3.11+). Falls back
    to manual event loop creation if called within an existing thread loop context
    preventing double-exhaustion of coroutine objects.
    """
    try:
        # Throws RuntimeError if no running loop
        asyncio.get_running_loop()
        has_loop = True
    except RuntimeError:
        has_loop = False

    if has_loop:
        # If the thread already has a loop, we must create a new one natively
        # or nest it via tools like nest_asyncio if strictly required. 
        # For typical Celery prefork contexts, creating a new un-attached loop works:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_func(*args, **kwargs))
        finally:
            loop.close()
    else:
        return asyncio.run(coro_func(*args, **kwargs))


# ---------------------------------------------------------------------------
#  Task: Nightly Ingestion
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.run_nightly_ingestion",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes between retries
)
def run_nightly_ingestion(self):
    """
    Pull yesterday's data for ALL industries and their markets.

    Iterates over the industry registry so newly added industries
    are automatically picked up without code changes.
    """
    from app.industries import INDUSTRIES
    from app.services import IngestionService
    from app.services.webhooks import broadcast_anomalies
    from app.database import async_session_factory

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = yesterday.replace(hour=23, minute=59, second=59)

    async def _ingest():
        service = IngestionService()
        results = []
        async with async_session_factory() as db:
            try:
                for industry_key, config in INDUSTRIES.items():
                    for market in config.markets:
                        result = await service.ingest(
                            db=db,
                            start_date=start,
                            end_date=end,
                            industry=industry_key,
                            latitude=market.latitude,
                            longitude=market.longitude,
                            geo_label=market.geo_label,
                        )
                        results.extend(result)
                await db.commit()
                if results:
                    await broadcast_anomalies(db, results)
            except Exception:
                await db.rollback()
                raise
        return results

    try:
        return _run_async(_ingest)
    except Exception as exc:
        task_logger.error("nightly_ingestion_failed", exc_info=True)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
#  Task: Weekly Deep Sync
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.run_weekly_deep_sync",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def run_weekly_deep_sync(self):
    """
    Re-ingest the past 7 days for all industries and markets.

    Catches delayed data updates, corrected records, and events
    that may have been published after the nightly run.
    """
    from app.industries import INDUSTRIES
    from app.services import IngestionService
    from app.services.webhooks import broadcast_anomalies
    from app.database import async_session_factory

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    async def _ingest():
        service = IngestionService()
        results = []
        async with async_session_factory() as db:
            try:
                for industry_key, config in INDUSTRIES.items():
                    for market in config.markets:
                        result = await service.ingest(
                            db=db,
                            start_date=start,
                            end_date=now,
                            industry=industry_key,
                            latitude=market.latitude,
                            longitude=market.longitude,
                            geo_label=market.geo_label,
                        )
                        results.extend(result)
                await db.commit()
                if results:
                    await broadcast_anomalies(db, results)
            except Exception:
                await db.rollback()
                raise
        return results

    try:
        return _run_async(_ingest)
    except Exception as exc:
        task_logger.error("weekly_deep_sync_failed", exc_info=True)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
#  Task: On-Demand Historical Backfill
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.run_historical_backfill", bind=True)
def run_historical_backfill(
    self,
    start_date: str,
    end_date: str,
    industry: str = "wireless_retail",
    geo_label: str | None = None,
):
    """
    On-demand backfill for a specific date range and industry.

    Called via the /api/v1/ingestion/backfill endpoint when an analyst
    wants to analyze a new historical period.
    """
    from app.industries import get_industry
    from app.services import IngestionService
    from app.services.webhooks import broadcast_anomalies
    from app.database import async_session_factory

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    config = get_industry(industry)

    async def _ingest():
        service = IngestionService()
        results = []
        async with async_session_factory() as db:
            try:
                # Use only the specified market, or all markets for this industry
                markets = config.markets
                if geo_label:
                    markets = [
                        m for m in config.markets
                        if m.geo_label.lower() == geo_label.lower()
                    ]
                    if not markets:
                        # Custom market not in registry — still ingest
                        from app.industries import Market
                        markets = [Market(geo_label=geo_label, latitude=0.0, longitude=0.0)]

                for market in markets:
                    result = await service.ingest(
                        db=db,
                        start_date=start,
                        end_date=end,
                        industry=industry,
                        latitude=market.latitude if market.latitude != 0.0 else None,
                        longitude=market.longitude if market.longitude != 0.0 else None,
                        geo_label=market.geo_label,
                    )
                    results.extend(result)
                await db.commit()
                if results:
                    await broadcast_anomalies(db, results)
            except Exception:
                await db.rollback()
                raise
        return results

    return _run_async(_ingest)


# ---------------------------------------------------------------------------
#  Task: Live Dashboard Ingestion
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.run_live_ingestion", bind=True)
def run_live_ingestion(
    self,
    start_date: str,
    end_date: str,
    industry: str,
    latitude: float | None = None,
    longitude: float | None = None,
    geo_label: str | None = None,
):
    """
    On-demand background ingestion for the live frontend dashboard.

    Called via the /api/v1/ingestion/run endpoint when a user requests
    a live dashboard refresh, preventing HTTP blocking on LLM queries.
    """
    from app.services import IngestionService
    from app.services.webhooks import broadcast_anomalies
    from app.database import async_session_factory

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    async def _ingest():
        service = IngestionService()
        async with async_session_factory() as db:
            try:
                result = await service.ingest(
                    db=db,
                    start_date=start,
                    end_date=end,
                    industry=industry,
                    latitude=latitude,
                    longitude=longitude,
                    geo_label=geo_label,
                )
                await db.commit()
                if result:
                    await broadcast_anomalies(db, result)
                return result
            except Exception:
                await db.rollback()
                raise

    return _run_async(_ingest)
