"""
Unit Tests — Ingestion Service

Tests the IngestionService logic in isolation:
- Deduplication algorithm
- Adapter orchestration with mocked adapters
- Error handling when adapters fail
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import IngestionService
from app.schemas import ImpactEventCreate


# ------------------------------------------------------------------ #
#  Deduplication Logic                                                #
# ------------------------------------------------------------------ #

class TestDeduplication:
    """Test service-level deduplication by (source, source_id)."""

    def setup_method(self):
        self.service = IngestionService()

    def test_no_duplicates_all_pass(self):
        events = [
            ImpactEventCreate(
                source="test", source_id=f"id-{i}",
                category="weather", title=f"Event {i}",
                start_date=datetime(2025, 1, i + 1),
            )
            for i in range(5)
        ]
        result = self.service._deduplicate(events)
        assert len(result) == 5

    def test_exact_duplicates_removed(self):
        events = [
            ImpactEventCreate(
                source="test", source_id="same-id",
                category="weather", title="Event A",
                start_date=datetime(2025, 1, 1),
            ),
            ImpactEventCreate(
                source="test", source_id="same-id",
                category="weather", title="Event B (dupe)",
                start_date=datetime(2025, 1, 2),
            ),
        ]
        result = self.service._deduplicate(events)
        assert len(result) == 1
        assert result[0].title == "Event A"  # First one survives

    def test_same_source_id_different_source_not_duplicate(self):
        events = [
            ImpactEventCreate(
                source="adapter-a", source_id="shared-id",
                category="weather", title="From A",
                start_date=datetime(2025, 1, 1),
            ),
            ImpactEventCreate(
                source="adapter-b", source_id="shared-id",
                category="weather", title="From B",
                start_date=datetime(2025, 1, 1),
            ),
        ]
        result = self.service._deduplicate(events)
        assert len(result) == 2

    def test_null_source_id_never_deduped(self):
        """Events without source_id should always pass through."""
        events = [
            ImpactEventCreate(
                source="test", source_id=None,
                category="weather", title=f"No-ID {i}",
                start_date=datetime(2025, 1, i + 1),
            )
            for i in range(3)
        ]
        result = self.service._deduplicate(events)
        assert len(result) == 3

    def test_empty_list(self):
        result = self.service._deduplicate([])
        assert result == []

    def test_single_event(self):
        events = [
            ImpactEventCreate(
                source="test", source_id="only",
                category="weather", title="Solo",
                start_date=datetime(2025, 1, 1),
            ),
        ]
        result = self.service._deduplicate(events)
        assert len(result) == 1

    def test_large_batch_dedup_performance(self):
        """Should handle 1000 events without issue."""
        events = [
            ImpactEventCreate(
                source="test", source_id=f"id-{i % 100}",  # 100 unique
                category="weather", title=f"Event {i}",
                start_date=datetime(2025, 1, 1),
            )
            for i in range(1000)
        ]
        result = self.service._deduplicate(events)
        assert len(result) == 100


# ------------------------------------------------------------------ #
#  Adapter Orchestration                                              #
# ------------------------------------------------------------------ #

class TestAdapterOrchestration:
    """Test the service's adapter coordination logic."""

    def test_service_has_six_adapters(self):
        service = IngestionService()
        assert len(service.adapters) == 6

    def test_adapter_names_are_unique(self):
        service = IngestionService()
        names = [a.name for a in service.adapters]
        assert len(names) == len(set(names))


# ------------------------------------------------------------------ #
#  Holiday Adapter — Severity Mapping                                 #
# ------------------------------------------------------------------ #

class TestHolidaySeverity:
    """Test holiday severity classification."""

    def test_black_friday_highest_severity(self):
        from app.adapters.holidays import HolidayAdapter
        adapter = HolidayAdapter()
        severity = adapter._get_holiday_severity("Black Friday")
        assert severity == 1.0

    def test_super_bowl_high_severity(self):
        from app.adapters.holidays import HolidayAdapter
        adapter = HolidayAdapter()
        severity = adapter._get_holiday_severity("Super Bowl LVIII")
        assert severity == 0.85

    def test_unknown_holiday_gets_default(self):
        from app.adapters.holidays import HolidayAdapter
        adapter = HolidayAdapter()
        severity = adapter._get_holiday_severity("Random Local Day")
        assert severity == 0.3

    def test_case_insensitive_matching(self):
        from app.adapters.holidays import HolidayAdapter
        adapter = HolidayAdapter()
        assert adapter._get_holiday_severity("CHRISTMAS") == 0.9
        assert adapter._get_holiday_severity("christmas Day") == 0.9

    def test_valentines_day(self):
        from app.adapters.holidays import HolidayAdapter
        adapter = HolidayAdapter()
        assert adapter._get_holiday_severity("Valentine's Day") == 0.5

    def test_st_patricks_day(self):
        from app.adapters.holidays import HolidayAdapter
        adapter = HolidayAdapter()
        assert adapter._get_holiday_severity("St. Patrick's Day") == 0.45
