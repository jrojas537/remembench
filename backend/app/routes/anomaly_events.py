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


@router.post(
    "/",
    response_model=ImpactEventResponse,
    status_code=201,
    summary="Create Impact Event",
    response_description="The newly created Impact Event record.",
    dependencies=[Depends(require_api_key)],
)
async def create_event(
    event: ImpactEventCreate,
    db: AsyncSession = Depends(get_db),
) -> ImpactEvent:
    """
    Create a new structured impact event representing a business disruption factor.

    This endpoint is designed for internal adapter consumption. If explicit spatial
    coordinates (`latitude`, `longitude`) are passed, the backend automatically 
    synthesizes a generic PostGIS point geometry for advanced proximity calculations.
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

    # Convert native lat/long to PostGIS spatial tracking point
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


@router.get(
    "/",
    response_model=list[ImpactEventResponse],
    summary="List Impact Events",
    response_description="A list of historical impact events filtered by parameters.",
)
async def list_events(
    category: str | None = Query(None, description="Filter by event taxonomy category"),
    source: str | None = Query(None, description="Filter by ingest source (e.g. gdelt, noaa-cdo)"),
    geo_label: str | None = Query(None, description="Search by approximate tracking market name"),
    industry: str = Query("wireless_retail", description="Explicit industry vertical scope"),
    start_date: datetime | None = Query(None, description="Only fetch events occurring after this timestamp"),
    end_date: datetime | None = Query(None, description="Only fetch events occurring before this timestamp"),
    limit: int = Query(50, ge=1, le=500, description="Clamp the max page results between 1 and 500"),
    offset: int = Query(0, ge=0, description="Standard offset pagination"),
    db: AsyncSession = Depends(get_db),
) -> list[ImpactEvent]:
    """
    Query the Impact Event database using a robust filter set.

    Ordered sequentially latest to oldest. Automatically cascades down to fetch all
    child verticals related to the primary query `industry`.
    """
    from app.industries import get_related_industry_keys
    
    related_keys = get_related_industry_keys(industry)
    query = select(ImpactEvent).where(ImpactEvent.industry.in_(related_keys))

    if category:
        query = query.where(ImpactEvent.category == category)
    if source:
        query = query.where(ImpactEvent.source == source)
    if geo_label:
        # Prevent SQL injection natively through SQLAlchemy parameterized `icontains`
        query = query.where(ImpactEvent.geo_label.icontains(geo_label))
    if start_date:
        query = query.where(ImpactEvent.start_date >= start_date)
    if end_date:
        query = query.where(ImpactEvent.start_date <= end_date)

    query = query.order_by(ImpactEvent.start_date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    
    return list(result.scalars().all())


@router.get(
    "/stats/summary",
    summary="Get Anomaly Summary Statistics",
    response_description="A structured taxonomy breakdown detailing aggregate frequency and combined severity trends.",
)
async def anomaly_stats(
    industry: str = Query("wireless_retail", description="The target industry vertical"),
    start_date: datetime | None = Query(None, description="Bounding time-series filter"),
    end_date: datetime | None = Query(None, description="Bounding time-series filter"),
    geo_label: str | None = Query(None, description="Optional bounding filter for physical market coordinates"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Aggregates database totals rapidly for top-line visual macro-trends.
    """
    from app.industries import get_related_industry_keys
    
    related_keys = get_related_industry_keys(industry)
    
    stmt = (
        select(
            ImpactEvent.category,
            func.count(ImpactEvent.id).label("count"),
            func.avg(ImpactEvent.severity).label("avg_severity"),
        )
        .where(ImpactEvent.industry.in_(related_keys))
    )
    
    if start_date:
        stmt = stmt.where(ImpactEvent.start_date >= start_date)
    if end_date:
        stmt = stmt.where(ImpactEvent.start_date <= end_date)
        
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


@router.get(
    "/{event_id}",
    response_model=ImpactEventResponse,
    summary="Get Specific Event",
    response_description="Returns absolute properties for the targeted Database record.",
)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ImpactEvent:
    """Retrieve singular event properties safely mapping up to an exact `uuid.UUID` endpoint."""
    result = await db.execute(
        select(ImpactEvent).where(ImpactEvent.id == event_id)
    )
    
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Requested Impact Event UUID could not be located")
        
    return event
