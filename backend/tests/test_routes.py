"""
Integration Tests — API Routes

Tests FastAPI endpoints via httpx AsyncClient with mocked database.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.routes.deps_auth import get_current_user


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
async def client(mock_session):
    async def override_get_db():
        yield mock_session
    
    async def override_get_current_user():
        return {"id": "testsuite-mock-user", "email": "test@example.com"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestIndustriesAPI:

    @pytest.mark.asyncio
    async def test_get_industries(self, client):
        resp = await client.get("/api/v1/industries/")
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data
        groups = data["groups"]
        assert "wireless" in groups
        assert "pizza" in groups
        # 1 wireless + 3 pizza = 4 total configs
        total = sum(len(v) for v in groups.values())
        assert total == 4

    @pytest.mark.asyncio
    async def test_industries_have_markets(self, client):
        resp = await client.get("/api/v1/industries/")
        groups = resp.json()["groups"]
        for group_key, configs in groups.items():
            for config in configs:
                assert "markets" in config
                assert len(config["markets"]) > 0

    @pytest.mark.asyncio
    async def test_pizza_markets_have_detroit(self, client):
        resp = await client.get("/api/v1/industries/")
        pizza_configs = resp.json()["groups"]["pizza"]
        # Check first pizza config (full service)
        labels = [m["geo_label"] for m in pizza_configs[0]["markets"]]
        assert any("Detroit" in label for label in labels)


class TestHealthAPI:

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_has_version(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.json()["version"] == "0.2.0"


class TestEventValidation:

    @pytest.mark.asyncio
    async def test_create_requires_body(self, client):
        resp = await client.post("/api/v1/events/")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_severity_rejected(self, client):
        resp = await client.post("/api/v1/events/", json={
            "source": "test", "category": "weather",
            "title": "Bad", "start_date": "2025-01-15T00:00:00",
            "severity": 1.5,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_title_rejected(self, client):
        resp = await client.post("/api/v1/events/", json={
            "source": "test", "category": "weather",
            "title": "", "start_date": "2025-01-15T00:00:00",
        })
        assert resp.status_code == 422


class TestEventListing:

    @pytest.mark.asyncio
    async def test_list_returns_200(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        resp = await client.get("/api/v1/events/")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_limit_over_500_rejected(self, client):
        resp = await client.get("/api/v1/events/", params={"limit": 501})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_offset_rejected(self, client):
        resp = await client.get("/api/v1/events/", params={"offset": -1})
        assert resp.status_code == 422


class TestEventStats:

    @pytest.mark.asyncio
    async def test_stats_returns_200(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        resp = await client.get("/api/v1/events/stats/summary")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_stats_respects_industry_param(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        resp = await client.get("/api/v1/events/stats/summary",
                                params={"industry": "pizza_delivery"})
        assert resp.json()["industry"] == "pizza_delivery"


class TestNotFound:

    @pytest.mark.asyncio
    async def test_nonexistent_event_404(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        resp = await client.get(f"/api/v1/events/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_uuid_422(self, client):
        resp = await client.get("/api/v1/events/not-a-uuid")
        assert resp.status_code == 422
