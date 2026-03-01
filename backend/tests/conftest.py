"""
Remembench Test Suite — Shared Fixtures

Provides reusable fixtures for all test modules:
- Async event loop for pytest-asyncio
- In-memory SQLite database (no Postgres needed)
- FastAPI TestClient with mocked DB dependency
- Sample event factories
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


# ------------------------------------------------------------------ #
#  Event Loop — required for pytest-asyncio                          #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="session")
def event_loop():
    """Create a shared event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ------------------------------------------------------------------ #
#  Sample Data Factories                                             #
# ------------------------------------------------------------------ #

def make_event_dict(**overrides) -> dict:
    """Create a valid ImpactEventCreate dict with sensible defaults."""
    now = datetime.utcnow()
    base = {
        "source": "test-adapter",
        "source_id": f"test-{uuid.uuid4().hex[:8]}",
        "category": "weather",
        "subcategory": "blizzard",
        "title": "Test Blizzard Event",
        "description": "Heavy snowfall for testing purposes.",
        "severity": 0.75,
        "confidence": 0.9,
        "start_date": now.isoformat(),
        "end_date": now.isoformat(),
        "latitude": 42.3314,
        "longitude": -83.0458,
        "geo_radius_km": 15.0,
        "geo_label": "Detroit",
        "industry": "pizza_full_service",
        "raw_payload": {"test": True},
    }
    base.update(overrides)
    return base


def make_wireless_event(**overrides) -> dict:
    """Create a wireless retail demo event."""
    return make_event_dict(
        category="outage",
        subcategory="network_outage",
        title="AT&T Network Outage",
        description="Nationwide outage affecting millions.",
        severity=0.95,
        geo_label="National",
        industry="wireless_retail",
        **overrides,
    )


def make_pizza_event(**overrides) -> dict:
    """Create a pizza industry demo event."""
    return make_event_dict(
        category="food_safety",
        subcategory="fda_recall",
        title="FDA Cheese Recall — Midwest",
        description="Mozzarella recall due to contamination.",
        severity=0.88,
        geo_label="Detroit",
        industry="pizza_full_service",
        **overrides,
    )


# ------------------------------------------------------------------ #
#  FastAPI Test Client (no database required)                        #
# ------------------------------------------------------------------ #

@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db
