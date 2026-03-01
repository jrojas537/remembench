"""
Unit Tests — Pydantic Schemas

Tests validation rules, edge cases, and boundary conditions
for ImpactEventCreate, YoYQueryParams, and HealthResponse schemas.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.schemas import (
    ImpactEventCreate,
    ImpactEventResponse,
    YoYQueryParams,
    HealthResponse,
)


# ------------------------------------------------------------------ #
#  ImpactEventCreate — Happy Path                                     #
# ------------------------------------------------------------------ #

class TestImpactEventCreateValid:
    """Verify valid event creation with various inputs."""

    def test_minimal_required_fields(self):
        event = ImpactEventCreate(
            source="test",
            category="weather",
            title="Test Event",
            start_date=datetime(2025, 1, 15),
        )
        assert event.source == "test"
        assert event.severity == 0.5  # default
        assert event.confidence == 0.5  # default
        assert event.industry == "wireless_retail"  # default

    def test_full_event_with_all_fields(self):
        event = ImpactEventCreate(
            source="open-meteo",
            source_id="om-2025-01-15-det-blizzard",
            category="weather",
            subcategory="blizzard",
            title="Blizzard in Detroit",
            description="25cm of snow",
            severity=0.9,
            confidence=0.85,
            start_date=datetime(2025, 1, 15),
            end_date=datetime(2025, 1, 16),
            latitude=42.33,
            longitude=-83.05,
            geo_radius_km=15.0,
            geo_label="Detroit",
            industry="pizza_full_service",
            raw_payload={"snowfall_cm": 25},
        )
        assert event.industry == "pizza_full_service"
        assert event.raw_payload == {"snowfall_cm": 25}

    def test_nullable_fields_default_to_none(self):
        event = ImpactEventCreate(
            source="test",
            category="news",
            title="Generic event",
            start_date=datetime(2025, 6, 1),
        )
        assert event.source_id is None
        assert event.description is None
        assert event.end_date is None
        assert event.latitude is None
        assert event.longitude is None
        assert event.raw_payload is None


# ------------------------------------------------------------------ #
#  ImpactEventCreate — Validation Boundaries                          #
# ------------------------------------------------------------------ #

class TestImpactEventValidation:
    """Test field validation rules and edge cases."""

    def test_severity_at_lower_bound(self):
        event = ImpactEventCreate(
            source="test", category="weather",
            title="Low", start_date=datetime(2025, 1, 1),
            severity=0.0,
        )
        assert event.severity == 0.0

    def test_severity_at_upper_bound(self):
        event = ImpactEventCreate(
            source="test", category="weather",
            title="High", start_date=datetime(2025, 1, 1),
            severity=1.0,
        )
        assert event.severity == 1.0

    def test_severity_below_zero_rejected(self):
        with pytest.raises(ValidationError, match="severity"):
            ImpactEventCreate(
                source="test", category="weather",
                title="Bad", start_date=datetime(2025, 1, 1),
                severity=-0.1,
            )

    def test_severity_above_one_rejected(self):
        with pytest.raises(ValidationError, match="severity"):
            ImpactEventCreate(
                source="test", category="weather",
                title="Bad", start_date=datetime(2025, 1, 1),
                severity=1.1,
            )

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(ValidationError, match="confidence"):
            ImpactEventCreate(
                source="test", category="weather",
                title="Bad", start_date=datetime(2025, 1, 1),
                confidence=-0.5,
            )

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError, match="confidence"):
            ImpactEventCreate(
                source="test", category="weather",
                title="Bad", start_date=datetime(2025, 1, 1),
                confidence=1.5,
            )

    def test_latitude_out_of_range_rejected(self):
        with pytest.raises(ValidationError, match="latitude"):
            ImpactEventCreate(
                source="test", category="weather",
                title="Bad", start_date=datetime(2025, 1, 1),
                latitude=91.0,
            )

    def test_longitude_out_of_range_rejected(self):
        with pytest.raises(ValidationError, match="longitude"):
            ImpactEventCreate(
                source="test", category="weather",
                title="Bad", start_date=datetime(2025, 1, 1),
                longitude=-181.0,
            )

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError, match="title"):
            ImpactEventCreate(
                source="test", category="weather",
                title="", start_date=datetime(2025, 1, 1),
            )

    def test_missing_source_rejected(self):
        with pytest.raises(ValidationError, match="source"):
            ImpactEventCreate(
                category="weather",
                title="No source", start_date=datetime(2025, 1, 1),
            )

    def test_missing_category_rejected(self):
        with pytest.raises(ValidationError, match="category"):
            ImpactEventCreate(
                source="test",
                title="No cat", start_date=datetime(2025, 1, 1),
            )

    def test_geo_radius_negative_rejected(self):
        with pytest.raises(ValidationError, match="geo_radius_km"):
            ImpactEventCreate(
                source="test", category="weather",
                title="Bad", start_date=datetime(2025, 1, 1),
                geo_radius_km=-5.0,
            )


# ------------------------------------------------------------------ #
#  YoYQueryParams — Validation                                        #
# ------------------------------------------------------------------ #

class TestYoYQueryParams:
    """Test Year-over-Year query parameter validation."""

    def test_valid_query(self):
        params = YoYQueryParams(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            lookback_years=2,
            industry="pizza_delivery",
        )
        assert params.lookback_years == 2

    def test_end_date_must_be_after_start(self):
        with pytest.raises(ValidationError, match="end_date"):
            YoYQueryParams(
                start_date=datetime(2025, 6, 1),
                end_date=datetime(2025, 5, 1),  # Before start
            )

    def test_end_date_equal_to_start_rejected(self):
        with pytest.raises(ValidationError, match="end_date"):
            YoYQueryParams(
                start_date=datetime(2025, 6, 1),
                end_date=datetime(2025, 6, 1),  # Same = not after
            )

    def test_lookback_zero_rejected(self):
        with pytest.raises(ValidationError, match="lookback_years"):
            YoYQueryParams(
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31),
                lookback_years=0,
            )

    def test_lookback_six_rejected(self):
        with pytest.raises(ValidationError, match="lookback_years"):
            YoYQueryParams(
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31),
                lookback_years=6,
            )

    def test_radius_too_large_rejected(self):
        with pytest.raises(ValidationError, match="radius_km"):
            YoYQueryParams(
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31),
                radius_km=501,
            )

    def test_default_industry_is_wireless(self):
        params = YoYQueryParams(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
        )
        assert params.industry == "wireless_retail"

    def test_categories_filter_accepts_list(self):
        params = YoYQueryParams(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            categories=["weather", "food_safety"],
        )
        assert params.categories == ["weather", "food_safety"]


# ------------------------------------------------------------------ #
#  HealthResponse                                                     #
# ------------------------------------------------------------------ #

class TestHealthResponse:
    """Test health check response schema."""

    def test_defaults(self):
        h = HealthResponse()
        assert h.status == "ok"
        assert h.version == "0.2.0"
        assert h.database == "unknown"

    def test_custom_values(self):
        h = HealthResponse(status="degraded", database="disconnected")
        assert h.status == "degraded"
        assert h.database == "disconnected"
