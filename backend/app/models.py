"""
Remembench — Database Models

SQLAlchemy ORM models for the Remembench contextual intelligence platform.
The ImpactEvent is the core table: every external data source (weather,
news, promotions, holidays, etc.) normalizes into this single schema.

The YoY comparison and forecasting engine queries only this table,
completely decoupled from source-specific adapter logic.
"""

import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all Remembench models."""
    pass


class ImpactEvent(Base):
    """
    Universal Impact Event — the core data model for Remembench.

    Every factor that could influence business performance in a given
    date range, market, and industry vertical is stored here. This
    includes weather events, competitor promotions, holidays, local
    events, service outages, supply chain disruptions, and news.

    The model is intentionally industry-agnostic; the `industry` column
    determines which vertical the event belongs to, while the `category`
    and `subcategory` fields classify the type of impact.

    PostGIS geography column enables spatial queries for market-level
    analysis (e.g., "all events within 50km of Detroit").
    """

    __tablename__ = "impact_events"

    # --- Primary Key ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # --- Source Identification ---
    # These fields track where the data came from and enable deduplication.
    # The (source, source_id) pair is unique per event.
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Origin adapter: 'open-meteo', 'noaa-cdo', 'gdelt', 'rss', 'holiday-api'",
    )
    source_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True,
        comment="Unique ID from the source system for deduplication",
    )

    # --- Classification ---
    # Category is the primary grouping (weather, competitor_promo, etc.)
    # and subcategory provides more specific typing within that group.
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Impact type: 'weather', 'competitor_promo', 'holiday', 'news', etc.",
    )
    subcategory: Mapped[str | None] = mapped_column(
        String(128), nullable=True,
        comment="Specific subtype: 'blizzard', 'bogo_deal', 'food_safety', etc.",
    )

    # --- Content ---
    title: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Short human-readable summary of the event",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Detailed description with context for analysts",
    )

    # --- Impact Scoring ---
    # Severity measures how much this event could impact the business.
    # Confidence measures how reliable the data source is.
    severity: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="Impact magnitude 0.0 (negligible) to 1.0 (severe)",
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="Data quality confidence 0.0 (uncertain) to 1.0 (verified)",
    )

    # --- Temporal ---
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        comment="When the event started (or the date it occurred)",
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When the event ended (null = point-in-time event)",
    )

    # --- Geographic ---
    geography = Column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
        comment="PostGIS POINT for the event epicenter",
    )
    geo_radius_km: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Estimated geographic impact radius in kilometers",
    )
    geo_label: Mapped[str | None] = mapped_column(
        String(256), nullable=True, index=True,
        comment="Human-readable location: 'Detroit', 'NYC', 'National'",
    )

    # --- Industry Vertical ---
    industry: Mapped[str] = mapped_column(
        String(64), nullable=False, default="wireless_retail", index=True,
        comment="Industry vertical key from the industry registry",
    )

    # --- Audit Trail ---
    raw_payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Complete source data preserved for audit and debugging",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # --- Composite Indexes ---
    # Optimized for the most common query patterns:
    # 1. YoY lookup: industry + category + date range
    # 2. Market analysis: geo_label + date range
    # 3. Deduplication: source + source_id (partial unique)
    __table_args__ = (
        Index(
            "ix_impact_events_yoy_lookup",
            "industry", "category", "start_date",
        ),
        Index(
            "ix_impact_events_geo_date",
            "geo_label", "start_date",
        ),
        Index(
            "ix_impact_events_source_dedup",
            "source", "source_id",
            unique=True,
            postgresql_where=text("source_id IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        """Concise debug representation showing key identifiers."""
        id_str = str(self.id)[:8] if self.id else "None"
        title_str = (self.title or "")[:40]
        return (
            f"<ImpactEvent(id={id_str}, source={self.source!r}, "
            f"category={self.category!r}, title={title_str!r})>"
        )
