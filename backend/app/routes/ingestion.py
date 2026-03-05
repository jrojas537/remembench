"""
Remembench — Ingestion API Routes

Exposes endpoints for triggering data ingestion manually.
These complement the automated Celery Beat schedule and are
useful for:
- Initial data loading when setting up a new market
- Testing adapter behavior for a specific date range
- On-demand backfills for historical analysis
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.routes.deps_auth import get_current_user
from app.database import get_db
from app.logging import get_logger
from app.services import IngestionService

logger = get_logger("routes.ingestion")

router = APIRouter()


@router.post(
    "/run",
    summary="Trigger Manual Ingestion",
    response_description="A statistical dictionary block confirming database inserts and fetched source volume.",
    dependencies=[Depends(get_current_user)],
)
async def run_ingestion(
    start_date: datetime = Query(..., description="Start of bounding time-series to ingest"),
    end_date: datetime = Query(..., description="End of bounding time-series to ingest"),
    industry: str = Query("wireless_retail", description="Designated industry vertical code"),
    latitude: float | None = Query(None, ge=-90.0, le=90.0, description="Spatial core bounding reference"),
    longitude: float | None = Query(None, ge=-180.0, le=180.0, description="Spatial core bounding reference"),
    geo_label: str | None = Query(None, description="Human readable market name"),
    # db: AsyncSession = Depends(get_db), # db session deferred to backend worker
) -> dict[str, Any]:
    """
    Manually triggers the overarching intelligence ingestion pipeline for a date range.

    Iterates through all registered adapters for the vertical, executes remote fetching,
    LLM semantic classification, deduplication dropping, and inserts clean records into PostgreSQL.
    """
    if end_date <= start_date:
        raise HTTPException(
            status_code=422,
            detail="end_date must be strictly after start_date",
        )

    # Resolve bounding coordinates dynamically if a geo_label market was passed
    if geo_label and industry and (latitude is None or longitude is None):
        try:
            from app.industries import get_all_markets
            markets = get_all_markets(industry)
            for m in markets:
                if m.geo_label == geo_label:
                    latitude = m.latitude
                    longitude = m.longitude
                    break
        except Exception as e:
            logger.warning("coordinate_lookup_failed", geo_label=geo_label, error=str(e))

    # =========================================================================
    # Tier 2 Optimization: Global Idempotent Caching
    # =========================================================================
    
    import json
    import datetime as dt
    from typing import Any
    from app.cache import get_redis
    
    redis_client_generator = get_redis()
    redis_client = await anext(redis_client_generator)
    
    # Construct a unique fingerprint for this exact ingestion request
    cache_key = f"ingestion:{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}:{industry}:{geo_label or 'global'}"
    
    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            logger.info("ingestion_cache_hit", cache_key=cache_key)
            return json.loads(cached_result)
    except Exception as e:
        logger.warning("redis_cache_check_failed", error=str(e))

    # Dispatch explicitly to the Celery worker for headless processing
    from app.tasks import run_live_ingestion

    task = run_live_ingestion.delay(
        start_date.isoformat(),
        end_date.isoformat(),
        industry,
        latitude,
        longitude,
        geo_label,
    )
    
    logger.info("dispatched_live_ingestion", task_id=str(task.id), industry=industry)
        
    return {
        "status": "queued",
        "task_id": str(task.id),
        "industry": industry,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "geo_label": geo_label,
        "cached": False
    }


@router.get(
    "/task/{task_id}",
    summary="Check Task Status",
    dependencies=[Depends(get_current_user)],
)
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Check the status of an asynchronous ingestion task."""
    from celery.result import AsyncResult
    from app.tasks import celery_app
    
    result = AsyncResult(task_id, app=celery_app)
    
    # Optional parsing of result if SUCCESS
    res_data = None
    if result.ready():
        res_data = result.result
        
    return {
        "task_id": task_id,
        "status": result.status,  # PENDING, STARTED, SUCCESS, FAILURE
        "result": res_data
    }


@router.post(
    "/backfill",
    summary="Schedule Historical Backfill",
    response_description="A task dictionary containing the async Celery job ID.",
    dependencies=[Depends(require_api_key)],
)
async def trigger_backfill(
    start_date: str = Query(..., description="ISO 8601 date string (e.g. 2024-01-01)"),
    end_date: str = Query(..., description="ISO 8601 date string (e.g. 2024-12-31)"),
    industry: str = Query("wireless_retail", description="Industry vertical target"),
    geo_label: str | None = Query(None, description="Specific local market constraint"),
) -> dict[str, Any]:
    """
    Triggers a massive asynchronous historical backfill ingestion job via Celery.

    Returns immediately with a trackable job ID pointing to the detached worker queue.
    """
    from app.tasks import run_historical_backfill

    task = run_historical_backfill.delay(start_date, end_date, industry, geo_label)
    
    return {
        "status": "queued",
        "task_id": str(task.id),
        "industry": industry,
        "start_date": start_date,
        "end_date": end_date,
        "geo_label": geo_label,
    }
