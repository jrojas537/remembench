import pytest
import os
from datetime import datetime
from fastapi.testclient import TestClient
from mcp.server.fastmcp import FastMCP

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import ImpactEvent

@pytest.mark.anyio
async def test_agent_anomalies_low_detail(mock_db):
    """
    Test that the low-detail endpoint correctly returns highly compressed semantic text lines
    rather than verbose JSON blobs.
    """
    # Create a mock event
    event = ImpactEvent(
        source_id="mock_src_1",
        industry="pizza_full_service",
        category="Weather",
        subcategory="Snow",
        title="Major Snowstorm",
        description="A massive snowstorm hit the city shutting down localized delivery.",
        geo_label="Detroit",
        start_date=datetime(2026, 2, 14),
        end_date=datetime(2026, 2, 15),
        severity=0.85,
        confidence=0.9
    )
    mock_db.add(event)
    await mock_db.commit()

    # Query the Agent API
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/agent/anomalies",
            params={
                "industry": "pizza_full_service",
                "start_date": "2026-02-10",
                "end_date": "2026-02-20",
                "market": "Detroit",
                "detail_level": "low"
            }
        )

    assert response.status_code == 200
    data = response.json()
    
    assert "events_summary" in data
    assert data["count"] == 1
    
    # Assert compression format
    summary_line = data["events_summary"]
    assert "* [2026-02-14] (Weather: 0.85) Major Snowstorm" in summary_line
    # Crucially, assert the massive description and DB metadata is MISSING
    assert "A massive snowstorm hit the city shutting down localized delivery." not in summary_line

@pytest.mark.anyio
async def test_agent_anomalies_high_detail(mock_db):
    """
    Test that high-detail returns JSON, but specifically JSON that has stripped out
    unnecessary database fields like created_at, updated_at, and source_id.
    """
    event = ImpactEvent(
        source_id="mock_src_2",
        industry="pizza_full_service",
        category="Holiday",
        subcategory="Federal",
        title="Presidents Day",
        description="Federal holiday.",
        geo_label="Detroit",
        start_date=datetime(2026, 2, 16),
        end_date=datetime(2026, 2, 16),
        severity=0.5,
        confidence=1.0
    )
    mock_db.add(event)
    await mock_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/agent/anomalies",
            params={
                "industry": "pizza_full_service",
                "start_date": "2026-02-15",
                "end_date": "2026-02-20",
                "detail_level": "high"
            }
        )

    assert response.status_code == 200
    data = response.json()
    event_payload = data["events"][0]
    
    # Assert stripped
    assert "created_at" not in event_payload
    assert "updated_at" not in event_payload
    assert "source_id" not in event_payload
    
    # Assert relevant details present
    assert event_payload["title"] == "Presidents Day"
    assert event_payload["severity"] == 0.5
