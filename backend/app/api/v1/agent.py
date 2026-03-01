from typing import Optional, List
from datetime import datetime, date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models import ImpactEvent
# In a real system you might want standard auth or specific agent api keys.
# from app.auth import require_api_key

router = APIRouter(prefix="/agent", tags=["agent"])

@router.get("/anomalies", summary="Token-optimized anomaly search for AI Agents")
async def get_anomalies(
    db: AsyncSession = Depends(get_db),
    industry: str = Query(..., description="Target industry slug (e.g. 'wireless_retail', 'pizza_full_service')"),
    start_date: date = Query(..., description="Start date YYYY-MM-DD"),
    end_date: date = Query(..., description="End date YYYY-MM-DD"),
    market: Optional[str] = Query(None, description="Optional specific market (e.g., 'New York City')"),
    limit: int = Query(50, le=200, description="Max results (capped at 200)"),
    detail_level: str = Query("low", description="'low' returns just a bullet point summary. 'high' returns the full text schema.")
):
    """
    Highly compressed endpoint specifically built for LLM/Agent consumption.
    Strips raw JSON payloads and metadata to save token space in the context window.
    """
    # Start and end date are natively validated as YYYY-MM-DD format thanks to Pydantic typing
    
    query = select(ImpactEvent).where(
        and_(
            ImpactEvent.industry == industry,
            ImpactEvent.start_date >= start_date,
            ImpactEvent.start_date <= end_date
        )
    )

    if market:
        query = query.where(ImpactEvent.geo_label == market)

    query = query.order_by(ImpactEvent.start_date.desc()).limit(limit)
    result_set = await db.execute(query)
    events = result_set.scalars().all()

    if detail_level == "low":
        # Return a flat list of semantic strings to save JSON token overhead
        text_lines = []
        for e in events:
            date_str = e.start_date.strftime("%Y-%m-%d")
            # Ex: "* [2026-02-14] (weather: 0.8) Heavy Snow: 25cm in Detroit metro"
            line = f"* [{date_str}] ({e.category}: {e.severity:.2f}) {e.title}"
            text_lines.append(line)
        return {"events_summary": "\n".join(text_lines), "count": len(events)}
    
    else:
        # High detail - returns array but stripped of internal UUIDs and DB stamps
        payload = []
        for e in events:
            payload.append({
                "id": str(e.id),
                "date": e.start_date.strftime("%Y-%m-%d"),
                "category": e.category,
                "title": e.title,
                "description": e.description,
                "severity": round(e.severity, 2),
                "confidence": round(e.confidence, 2),
                "market": e.geo_label
            })
        return {"events": payload, "count": len(events)}

@router.get("/anomaly/{event_id}", summary="Fetch full descriptive payload for a single event")
async def get_anomaly_details(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Agent Drill-Down tool. After an agent identifies an interesting event using `detail_level=low`,
    it can fetch the full descriptive payload here.
    """
    event = await db.get(ImpactEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    return {
        "id": str(event.id),
        "date": event.start_date.strftime("%Y-%m-%d"),
        "category": event.category,
        "subcategory": event.subcategory,
        "title": event.title,
        "description": event.description,
        "severity": round(event.severity, 2),
        "confidence": round(event.confidence, 2),
        "market": event.geo_label,
        "raw_source_text": event.raw_payload.get("original_text", None) if event.raw_payload else None
    }
