"""
Unit Tests — YoY Comparison Logic

Tests the core comparison functions that power the YoY analysis engine:
- Period summary building
- Significant delta detection
- Category difference classification
"""

import pytest
import uuid
from datetime import datetime

from app.routes.yoy_comparison import (
    _build_period_summary,
    _find_significant_deltas,
)
from app.schemas import YoYPeriodSummary, ImpactEventResponse


# ------------------------------------------------------------------ #
#  Helper: Build a mock period summary                                #
# ------------------------------------------------------------------ #

def _make_summary(
    year: int,
    events_by_category: dict[str, int],
    avg_severity: float = 0.5,
) -> YoYPeriodSummary:
    """Create a YoYPeriodSummary for testing deltas."""
    total = sum(events_by_category.values())
    return YoYPeriodSummary(
        year=year,
        period_start=datetime(year, 1, 1),
        period_end=datetime(year, 1, 31),
        total_events=total,
        events_by_category=events_by_category,
        avg_severity=avg_severity,
        events=[],
    )


# ------------------------------------------------------------------ #
#  Period Summary Building                                            #
# ------------------------------------------------------------------ #

class TestBuildPeriodSummary:
    """Test _build_period_summary function."""

    def test_empty_events_returns_zero_summary(self):
        summary = _build_period_summary(
            year=2025,
            start=datetime(2025, 1, 1),
            end=datetime(2025, 1, 31),
            events=[],
        )
        assert summary.year == 2025
        assert summary.total_events == 0
        assert summary.avg_severity == 0.0
        assert summary.events_by_category == {}

    def test_single_category(self):
        # Create mock event objects with required attributes
        class MockEvent:
            def __init__(self, category, severity):
                self.category = category
                self.severity = severity
                self.id = uuid.uuid4()
                self.source = "test"
                self.source_id = None
                self.subcategory = None
                self.title = "Test"
                self.description = None
                self.confidence = 0.5
                self.start_date = datetime(2025, 1, 15)
                self.end_date = None
                self.geo_radius_km = None
                self.geo_label = "Detroit"
                self.industry = "pizza_full_service"
                self.raw_payload = None
                self.created_at = datetime(2025, 1, 15)
                self.updated_at = datetime(2025, 1, 15)

        events = [
            MockEvent("weather", 0.8),
            MockEvent("weather", 0.6),
        ]
        summary = _build_period_summary(
            year=2025,
            start=datetime(2025, 1, 1),
            end=datetime(2025, 1, 31),
            events=events,
        )
        assert summary.total_events == 2
        assert summary.events_by_category == {"weather": 2}
        assert summary.avg_severity == pytest.approx(0.7, abs=0.001)

    def test_multiple_categories(self):
        class MockEvent:
            def __init__(self, category, severity):
                self.category = category
                self.severity = severity
                self.id = uuid.uuid4()
                self.source = "test"
                self.source_id = None
                self.subcategory = None
                self.title = "Test"
                self.description = None
                self.confidence = 0.5
                self.start_date = datetime(2025, 1, 15)
                self.end_date = None
                self.geo_radius_km = None
                self.geo_label = None
                self.industry = "wireless_retail"
                self.raw_payload = None
                self.created_at = datetime(2025, 1, 15)
                self.updated_at = datetime(2025, 1, 15)

        events = [
            MockEvent("weather", 0.9),
            MockEvent("holiday", 0.5),
            MockEvent("holiday", 0.3),
            MockEvent("news", 0.2),
        ]
        summary = _build_period_summary(
            year=2025,
            start=datetime(2025, 1, 1),
            end=datetime(2025, 1, 31),
            events=events,
        )
        assert summary.events_by_category == {
            "weather": 1,
            "holiday": 2,
            "news": 1,
        }
        assert summary.total_events == 4


# ------------------------------------------------------------------ #
#  Significant Delta Detection                                        #
# ------------------------------------------------------------------ #

class TestFindSignificantDeltas:
    """Test the delta detection engine."""

    def test_no_difference_returns_empty(self):
        current = _make_summary(2025, {"weather": 2, "holiday": 1})
        prior = _make_summary(2024, {"weather": 2, "holiday": 1})
        deltas = _find_significant_deltas(current, prior)
        assert deltas == []

    def test_more_events_current_year(self):
        current = _make_summary(2025, {"weather": 5})
        prior = _make_summary(2024, {"weather": 2})
        deltas = _find_significant_deltas(current, prior)
        assert len(deltas) == 1
        assert deltas[0]["category"] == "weather"
        assert deltas[0]["delta"] == 3
        assert deltas[0]["direction"] == "more"
        assert deltas[0]["significance"] == "high"

    def test_fewer_events_current_year(self):
        current = _make_summary(2025, {"weather": 1})
        prior = _make_summary(2024, {"weather": 4})
        deltas = _find_significant_deltas(current, prior)
        assert deltas[0]["delta"] == -3
        assert deltas[0]["direction"] == "fewer"
        assert deltas[0]["significance"] == "high"

    def test_medium_significance(self):
        current = _make_summary(2025, {"weather": 3})
        prior = _make_summary(2024, {"weather": 2})
        deltas = _find_significant_deltas(current, prior)
        assert deltas[0]["significance"] == "medium"

    def test_new_category_in_current(self):
        current = _make_summary(2025, {"weather": 2, "food_safety": 1})
        prior = _make_summary(2024, {"weather": 2})
        deltas = _find_significant_deltas(current, prior)
        assert len(deltas) == 1
        assert deltas[0]["category"] == "food_safety"
        assert deltas[0]["current_year_count"] == 1
        assert deltas[0]["prior_year_count"] == 0

    def test_category_disappeared(self):
        current = _make_summary(2025, {"weather": 2})
        prior = _make_summary(2024, {"weather": 2, "outage": 3})
        deltas = _find_significant_deltas(current, prior)
        assert len(deltas) == 1
        assert deltas[0]["category"] == "outage"
        assert deltas[0]["delta"] == -3

    def test_multiple_deltas_sorted_by_magnitude(self):
        current = _make_summary(2025, {"weather": 5, "holiday": 1, "news": 0})
        prior = _make_summary(2024, {"weather": 1, "holiday": 0, "news": 2})
        deltas = _find_significant_deltas(current, prior)
        # Should be sorted by |delta| descending
        magnitudes = [abs(d["delta"]) for d in deltas]
        assert magnitudes == sorted(magnitudes, reverse=True)

    def test_both_empty_returns_empty(self):
        current = _make_summary(2025, {})
        prior = _make_summary(2024, {})
        deltas = _find_significant_deltas(current, prior)
        assert deltas == []
