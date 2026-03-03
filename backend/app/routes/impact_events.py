"""
Remembench — Impact Event CRUD Routes

Provides endpoints for creating, listing, and retrieving impact events.
Impact events represent any factor (weather, promotion, holiday, etc.)
that could influence business performance in a given market and industry.

Route ordering note: /stats/summary MUST be defined before /{event_id}
because FastAPI matches routes top-to-bottom and would otherwise try
to parse "stats" as a UUID.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging import get_logger
from app.models import ImpactEvent
from app.schemas import ImpactEventCreate, ImpactEventResponse
from app.auth import require_api_key

logger = get_logger("routes.events")

router = APIRouter()


@router.post("/", response_model=ImpactEventResponse, status_code=201,
             dependencies=[Depends(require_api_key)])
async def create_event(
    event: ImpactEventCreate,
    db: AsyncSession = Depends(get_db),
) -> ImpactEvent:
    """
    Create a new impact event.

    Typically called by adapters during ingestion, not by end users.
    If latitude/longitude are provided, a PostGIS point is created
    for spatial queries.
    """
    db_event = ImpactEvent(
        source=event.source,
        source_id=event.source_id,
        category=event.category,
        subcategory=event.subcategory,
        title=event.title,
        description=event.description,
        severity=event.severity,
        confidence=event.confidence,
        start_date=event.start_date,
        end_date=event.end_date,
        geo_radius_km=event.geo_radius_km,
        geo_label=event.geo_label,
        industry=event.industry,
        raw_payload=event.raw_payload,
    )

    # Set PostGIS POINT geometry if coordinates are provided
    if event.latitude is not None and event.longitude is not None:
        db_event.geography = ST_SetSRID(
            ST_MakePoint(event.longitude, event.latitude), 4326
        )

    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    logger.info(
        "event_created",
        event_id=str(db_event.id),
        source=db_event.source,
        category=db_event.category,
        industry=db_event.industry,
    )
    return db_event


@router.get("/", response_model=list[ImpactEventResponse], dependencies=[Depends(require_api_key)])
async def list_events(
    category: str | None = Query(None, description="Filter by impact category"),
    source: str | None = Query(None, description="Filter by data source"),
    geo_label: str | None = Query(None, description="Filter by market name (partial match)"),
    industry: str = Query("wireless_retail", description="Industry vertical"),
    start_date: datetime | None = Query(None, description="Filter events on or after this date"),
    end_date: datetime | None = Query(None, description="Filter events on or before this date"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> list[ImpactEvent]:
    """
    List impact events with optional filters.

    Returns events sorted by date (newest first) for the specified
    industry. Supports filtering by category, source, market, and date range.
    """
    query = select(ImpactEvent).where(ImpactEvent.industry == industry)

    if category:
        query = query.where(ImpactEvent.category == category)
    if source:
        query = query.where(ImpactEvent.source == source)
    if geo_label:
        # Include both the specific market and "National" events
        query = query.where(
            (ImpactEvent.geo_label.icontains(geo_label)) | 
            (ImpactEvent.geo_label == "National")
        )
    if start_date:
        query = query.where(ImpactEvent.end_date >= start_date)
    if end_date:
        query = query.where(ImpactEvent.start_date <= end_date)

    query = query.order_by(ImpactEvent.start_date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


# NOTE: /stats/summary must come BEFORE /{event_id} — see module docstring.
@router.get("/stats/summary", dependencies=[Depends(require_api_key)])
async def event_stats(
    industry: str = Query("wireless_retail", description="Industry vertical"),
    start_date: datetime | None = Query(None, description="Filter events on or after this date"),
    end_date: datetime | None = Query(None, description="Filter events on or before this date"),
    geo_label: str | None = Query(None, description="Filter by market name (includes National)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get summary statistics of impact events per category.
    """
    stmt = (
        select(
            ImpactEvent.category,
            func.count(ImpactEvent.id).label("count"),
            func.avg(ImpactEvent.severity).label("avg_severity"),
        )
        .where(ImpactEvent.industry == industry)
    )
    if start_date:
        stmt = stmt.where(ImpactEvent.end_date >= start_date)
    if end_date:
        stmt = stmt.where(ImpactEvent.start_date <= end_date)
    if geo_label:
        # Include both the specific market and "National" events
        stmt = stmt.where(
            (ImpactEvent.geo_label.icontains(geo_label)) | 
            (ImpactEvent.geo_label == "National")
        )
        
    stmt = stmt.group_by(ImpactEvent.category)
    result = await db.execute(stmt)
    rows = result.all()
    return {
        "industry": industry,
        "categories": {
            row.category: {
                "count": row.count,
                "avg_severity": round(float(row.avg_severity), 3) if row.avg_severity else 0.0,
            }
            for row in rows
        },
    }


@router.get("/{event_id}", response_model=ImpactEventResponse, dependencies=[Depends(require_api_key)])
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ImpactEvent:
    """Retrieve a single impact event by its UUID."""
    result = await db.execute(
        select(ImpactEvent).where(ImpactEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
