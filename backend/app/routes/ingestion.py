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
