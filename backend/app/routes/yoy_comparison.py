"""
Remembench — YoY Comparison Routes

Core business logic: compares impact events across matching date ranges
in different years to answer "what was different last year that could
explain this performance delta?"

This is the primary value engine of Remembench — it takes a date range
and industry, finds all contextual events, then looks back N years to
find the equivalent periods so analysts can adjust forecasts.
"""

from datetime import datetime
import asyncio
from dateutil.relativedelta import relativedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging import get_logger
from app.models import ImpactEvent
from app.auth import require_api_key
from app.schemas import (
    ImpactEventResponse,
    YoYComparisonResponse,
    YoYPeriodSummary,
)

logger = get_logger("routes.yoy_comparison")

router = APIRouter()


async def _get_period_events(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    industry: str,
    geo_label: str | None = None,
    categories: list[str] | None = None,
) -> list[ImpactEvent]:
    """
    Fetch impact events for a specific date range and industry.

    Supports optional geographic and category filtering.
    Results are sorted chronologically.
    """
    from app.industries import get_related_industry_keys
    related_keys = get_related_industry_keys(industry)
    
    query = select(ImpactEvent).where(
        and_(
            ImpactEvent.industry.in_(related_keys),
            ImpactEvent.end_date >= start,
            ImpactEvent.start_date <= end,
        )
    )

    if geo_label:
        # Safe from SQL injection — icontains uses parameterized queries
        query = query.where(ImpactEvent.geo_label.icontains(geo_label))
    if categories:
        query = query.where(ImpactEvent.category.in_(categories))

    query = query.order_by(ImpactEvent.start_date)
    result = await db.execute(query)
    return list(result.scalars().all())


def _build_period_summary(
    year: int,
    start: datetime,
    end: datetime,
    events: list[ImpactEvent],
) -> YoYPeriodSummary:
    """
    Build a structured summary for a time period's impact events.

    Computes per-category counts and average severity — the data
    needed for the YoY comparison dashboard.
    """
    category_counts: dict[str, int] = {}
    total_severity = 0.0

    for event in events:
        category_counts[event.category] = category_counts.get(event.category, 0) + 1
        total_severity += event.severity

    avg_severity = total_severity / len(events) if events else 0.0

    return YoYPeriodSummary(
        year=year,
        period_start=start,
        period_end=end,
        total_events=len(events),
        events_by_category=category_counts,
        avg_severity=round(avg_severity, 3),
        events=[ImpactEventResponse.model_validate(e) for e in events],
    )


def _find_significant_deltas(
    current: YoYPeriodSummary,
    prior: YoYPeriodSummary,
) -> list[dict]:
    """
    Identify categories with meaningful differences between periods.

    This is the key insight generator — it answers "what was different
    last year?" For example: 3 severe weather events in 2024 vs 0 in 2025
    could explain why foot traffic is up this year.

    Significance levels:
    - high: delta >= 3 events (major contextual difference)
    - medium: delta >= 1 (notable difference)
    - low: no difference
    """
    deltas: list[dict] = []
    all_categories = set(current.events_by_category.keys()) | set(prior.events_by_category.keys())

    for cat in all_categories:
        current_count = current.events_by_category.get(cat, 0)
        prior_count = prior.events_by_category.get(cat, 0)
        diff = current_count - prior_count

        if diff != 0:
            deltas.append({
                "category": cat,
                "current_year_count": current_count,
                "prior_year_count": prior_count,
                "delta": diff,
                "direction": "more" if diff > 0 else "fewer",
                "significance": "high" if abs(diff) >= 3 else "medium" if abs(diff) >= 1 else "low",
            })

    # Most significant differences first
    deltas.sort(key=lambda d: abs(d["delta"]), reverse=True)
    return deltas


@router.get("/compare", response_model=YoYComparisonResponse, dependencies=[Depends(require_api_key)])
async def compare_yoy(
    start_date: datetime = Query(..., description="Start of the target period"),
    end_date: datetime = Query(..., description="End of the target period"),
    lookback_years: int = Query(1, ge=1, le=5, description="Years to look back"),
    geo_label: str | None = Query(None, description="Filter by market name"),
    categories: list[str] | None = Query(None, description="Filter by categories"),
    industry: str = Query("wireless_retail", description="Industry vertical"),
    db: AsyncSession = Depends(get_db),
) -> YoYComparisonResponse:
    """
    Compare impact events for a date range against prior years.

    Example: comparing Feb 1-28 2025 against Feb 1-28 2024 for the
    Detroit pizza market. If there was a major blizzard in 2024 but
    not 2025, that context helps explain why sales are up this year.
    """
    # Current period
    current_events = await _get_period_events(
        db, start_date, end_date, industry, geo_label, categories
    )
    current_summary = _build_period_summary(
        start_date.year, start_date, end_date, current_events
    )

    # Prior periods — one summary per lookback year
    prior_summaries: list[YoYPeriodSummary] = []
    all_deltas: list[dict] = []

    async def fetch_and_summarize(years_back: int) -> YoYPeriodSummary:
        prior_start = start_date - relativedelta(years=years_back)
        prior_end = end_date - relativedelta(years=years_back)

        prior_events = await _get_period_events(
            db, prior_start, prior_end, industry, geo_label, categories
        )
        return _build_period_summary(
            prior_start.year, prior_start, prior_end, prior_events
        )

    tasks = [fetch_and_summarize(y) for y in range(1, lookback_years + 1)]
    results = await asyncio.gather(*tasks)

    for prior_summary in results:
        prior_summaries.append(prior_summary)

        # Find what changed between this year and the prior year
        deltas = _find_significant_deltas(current_summary, prior_summary)
        for d in deltas:
            d["compared_year"] = prior_summary.year
        all_deltas.extend(deltas)

    logger.info(
        "yoy_comparison_complete",
        industry=industry,
        current_year=start_date.year,
        lookback_years=lookback_years,
        current_events=current_summary.total_events,
        prior_events_total=sum(p.total_events for p in prior_summaries),
        significant_deltas=len(all_deltas),
    )

    return YoYComparisonResponse(
        current_period=current_summary,
        prior_periods=prior_summaries,
        significant_deltas=all_deltas,
    )
