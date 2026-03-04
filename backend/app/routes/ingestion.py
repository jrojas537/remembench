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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.database import get_db
from app.logging import get_logger
from app.services import IngestionService

logger = get_logger("routes.ingestion")

router = APIRouter()


@router.post("/run", dependencies=[Depends(require_api_key)])
async def run_ingestion(
    start_date: datetime = Query(..., description="Start of period to ingest"),
    end_date: datetime = Query(..., description="End of period to ingest"),
    industry: str = Query("wireless_retail", description="Industry vertical to ingest for"),
    latitude: float | None = Query(None, ge=-90.0, le=90.0),
    longitude: float | None = Query(None, ge=-180.0, le=180.0),
    geo_label: str | None = Query(None, description="Market name"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Manually trigger ingestion for a specific date range, market, and industry.

    Runs all configured adapters for the specified industry and returns
    a summary of what was fetched and inserted.
    Requires X-API-Key header.
    """
    if end_date <= start_date:
        raise HTTPException(
            status_code=422,
            detail="end_date must be after start_date",
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
            logger.warning(f"Could not lookup coordinates for {geo_label}: {e}")

    # =========================================================================
    # Tier 2 Optimization: Global Idempotent Caching
    # =========================================================================
    from app.cache import get_redis
    redis_client_generator = get_redis()
    redis_client = await anext(redis_client_generator)
    
    # Construct a unique fingerprint for this exact ingestion request
    cache_key = f"ingestion:{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}:{industry}:{geo_label or 'global'}"
    
    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            import json
            logger.info(f"Ingestion cache hit for {cache_key} - skipping external adapters.")
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"Redis cache check failed: {e}")

    service = IngestionService()
    result = await service.ingest(
        db=db,
        start_date=start_date,
        end_date=end_date,
        industry=industry,
        latitude=latitude,
        longitude=longitude,
        geo_label=geo_label,
    )
    
    # Store successful run in cache
    try:
        import json
        
        # Calculate dynamic cache expiration based on how old the data is
        import datetime as dt
        today = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        
        # Strip tzinfo for naive comparison if needed
        end_dt_naive = end_date.replace(tzinfo=None)
        days_ago = (today - end_dt_naive).days
        
        if days_ago > 14:
            # Historical dataset - won't change, cache permanently
            await redis_client.set(cache_key, json.dumps(result))
            logger.info(f"Permanently cached historical ingestion: {cache_key}")
        else:
            # Recent/Future dataset - might update, cache for 4 hours
            await redis_client.setex(cache_key, 14400, json.dumps(result))
            logger.info(f"Cached active ingestion for 4 hours: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to write to Redis cache: {e}")
        
    return result


@router.post("/backfill", dependencies=[Depends(require_api_key)])
async def trigger_backfill(
    start_date: str = Query(..., description="ISO date string (e.g. 2024-01-01)"),
    end_date: str = Query(..., description="ISO date string (e.g. 2024-12-31)"),
    industry: str = Query("wireless_retail", description="Industry vertical"),
    geo_label: str | None = Query(None, description="Specific market to backfill"),
) -> dict:
    """
    Trigger an async historical backfill via Celery.

    Returns immediately with a task ID that can be used to check
    progress. The actual ingestion runs in a Celery worker.
    """
    from app.tasks import run_historical_backfill

    task = run_historical_backfill.delay(start_date, end_date, industry, geo_label)
    return {
        "status": "queued",
        "task_id": task.id,
        "industry": industry,
        "start_date": start_date,
        "end_date": end_date,
        "geo_label": geo_label,
    }
