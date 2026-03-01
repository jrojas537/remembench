"""
Remembench — Pydantic Schemas

Request/response serialization schemas, decoupled from SQLAlchemy models.
These ensure clean API contracts with validation, type coercion, and
human-readable error messages.

Schema hierarchy:
  ImpactEventBase → ImpactEventCreate (ingestion input)
                  → ImpactEventResponse (API output)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
#  Impact Event Schemas
# --------------------------------------------------------------------------- #

class ImpactEventBase(BaseModel):
    """
    Shared fields for impact event creation and display.

    These represent any factor (weather, promotion, holiday, disruption)
    that could affect business performance in a given market and industry.
    """

    source: str = Field(
        ..., max_length=64,
        description="Adapter that produced this event",
        examples=["open-meteo", "gdelt", "rss", "holiday-api"],
    )
    source_id: str | None = Field(
        None, max_length=256,
        description="Unique ID from the source system for deduplication",
    )

    # --- Classification ---
    category: str = Field(
        ..., max_length=64,
        description="Primary impact type",
        examples=["weather", "competitor_promo", "holiday", "news", "food_safety"],
    )
    subcategory: str | None = Field(
        None, max_length=128,
        description="Specific subtype within the category",
        examples=["blizzard", "bogo_deal", "federal_holiday"],
    )

    # --- Content ---
    title: str = Field(
        ..., min_length=1, max_length=512,
        description="Short human-readable summary",
    )
    description: str | None = Field(
        None,
        description="Detailed context for analysts",
    )

    # --- Impact Scoring ---
    severity: float = Field(
        0.5, ge=0.0, le=1.0,
        description="Impact magnitude: 0.0 (negligible) to 1.0 (severe)",
    )
    confidence: float = Field(
        0.5, ge=0.0, le=1.0,
        description="Data quality confidence: 0.0 (uncertain) to 1.0 (verified)",
    )

    # --- Temporal ---
    start_date: datetime = Field(
        ..., description="When the event started or occurred",
    )
    end_date: datetime | None = Field(
        None, description="When the event ended (null = point-in-time)",
    )

    # --- Geographic ---
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    geo_radius_km: float | None = Field(
        None, ge=0.0,
        description="Geographic impact radius in km",
    )
    geo_label: str | None = Field(
        None, max_length=256,
        description="Human-readable location name",
        examples=["Detroit", "New York City", "National"],
    )

    # --- Industry ---
    industry: str = Field(
        "wireless_retail", max_length=64,
        description="Industry vertical key from the registry",
    )


class ImpactEventCreate(ImpactEventBase):
    """Schema for creating a new impact event (used by adapters)."""
    
    # --- Raw Data ---
    raw_payload: dict | None = Field(
        None,
        description="Original source data preserved for audit",
    )


class ImpactEventResponse(ImpactEventBase):
    """Schema for returning an impact event from the API."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
#  YoY Comparison Schemas
# --------------------------------------------------------------------------- #

class YoYQueryParams(BaseModel):
    """
    Query parameters for Year-over-Year comparisons.

    The engine finds all impact events in the specified date range
    and industry, then looks back N years to find equivalent periods
    for comparison. This surfaces what was different last year that
    could explain performance deltas.
    """

    start_date: datetime = Field(..., description="Start of the target period")
    end_date: datetime = Field(..., description="End of the target period")
    lookback_years: int = Field(
        1, ge=1, le=5,
        description="How many prior years to compare against",
    )
    geo_label: str | None = Field(None, description="Filter by market name")
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    radius_km: float = Field(
        50.0, ge=1.0, le=500.0,
        description="Search radius for geographic queries",
    )
    categories: list[str] | None = Field(
        None,
        description="Filter to specific impact categories",
        examples=[["weather", "competitor_promo"]],
    )
    industry: str = Field(
        "wireless_retail",
        description="Industry vertical to analyze",
    )

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Validate that end_date comes after start_date."""
        start = info.data.get("start_date")
        if start and v <= start:
            msg = "end_date must be after start_date"
            raise ValueError(msg)
        return v


class YoYPeriodSummary(BaseModel):
    """Summary of impact events for a single year's period."""

    year: int
    period_start: datetime
    period_end: datetime
    total_events: int
    events_by_category: dict[str, int]
    avg_severity: float
    events: list[ImpactEventResponse]


class YoYComparisonResponse(BaseModel):
    """
    Full YoY comparison result.

    Shows the current period alongside one or more prior periods
    so analysts can see what factors were present (or absent)
    last year that might explain performance differences.
    """

    current_period: YoYPeriodSummary
    prior_periods: list[YoYPeriodSummary]
    significant_deltas: list[dict]


# --------------------------------------------------------------------------- #
#  Health / Meta
# --------------------------------------------------------------------------- #

class HealthResponse(BaseModel):
    """Health check response for monitoring."""
    status: str = "ok"
    version: str = "0.2.0"
    database: str = "unknown"
