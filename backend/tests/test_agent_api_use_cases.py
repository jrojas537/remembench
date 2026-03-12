import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.models import ImpactEvent
from app.database import get_db
from app.main import app

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base

from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def populated_db():
    events = [
        ImpactEvent(
            id="11111111-1111-1111-1111-111111111111",
            source_id="src_1",
            industry="pizza_full_service",
            category="Weather",
            title="Event 1",
            description="Desc 1",
            geo_label="New York",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 2),
            severity=0.5,
            confidence=0.8
        ),
        ImpactEvent(
            id="22222222-2222-2222-2222-222222222222",
            source_id="src_2",
            industry="pizza_full_service",
            category="Holiday",
            title="Event 2",
            description="Desc 2",
            geo_label="Detroit",
            start_date=datetime(2026, 1, 15),
            end_date=datetime(2026, 1, 15),
            severity=0.9,
            confidence=0.9
        ),
        ImpactEvent(
            id="33333333-3333-3333-3333-333333333333",
            source_id="src_3",
            industry="wireless_retail",
            category="Promo",
            title="Event 3",
            description="Desc 3",
            geo_label="Detroit",
            start_date=datetime(2026, 2, 1),
            end_date=datetime(2026, 2, 5),
            severity=0.3,
            confidence=0.95
        )
    ]
    
    mock_session = AsyncMock()
    
    async def mock_execute(query):
        try:
            compiled = query.compile(compile_kwargs={"literal_binds": True})
            q_str = str(compiled)
        except Exception:
            q_str = str(query)

        result_events = list(events)
        
        # Simple manual filtering based on test cases
        if "'pizza_full_service'" in q_str:
            result_events = [e for e in result_events if e.industry == "pizza_full_service"]
        elif "'wireless_retail'" in q_str:
            result_events = [e for e in result_events if e.industry == "wireless_retail"]

        if "'Detroit'" in q_str:
            result_events = [e for e in result_events if e.geo_label == "Detroit"]
        elif "'Los Angeles'" in q_str:
            result_events = [e for e in result_events if e.geo_label == "Los Angeles"]
            
        if "count" in q_str.lower():  
            # Some queries are select(func.count())
            pass
            
        if "'2026-01-31'" in q_str and "'2026-01-01'" in q_str and q_str.find("'2026-01-31'") < q_str.find("'2026-01-01'"):
            result_events = []
        elif "'2028-01-01'" in q_str:
            result_events = []
        elif "'2026-01-15'" in q_str:
            result_events = [e for e in result_events if e.start_date >= datetime(2026, 1, 15)]
            
        if "LIMIT 1" in q_str or "limit 1" in q_str.lower() or "limit = 1" in q_str.lower():
            result_events = result_events[:1]
            
        if "22222222-2222-2222-2222-222222222222" in q_str:
            result_events = [e for e in result_events if str(e.id) == "22222222-2222-2222-2222-222222222222"]
        elif "99999999-9999-9999-9999-999999999999" in q_str:
            result_events = []
            
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = result_events
        mock_result.scalar_one_or_none.return_value = result_events[0] if result_events else None
        
        # if the query actually returns a count
        if "count(" in q_str.lower():
            mock_result.scalar.return_value = len(result_events)
            
        return mock_result

    mock_session.execute.side_effect = mock_execute
    
    async def mock_get(model, pk):
        for e in events:
            if str(e.id) == str(pk):
                return e
        return None
        
    mock_session.get.side_effect = mock_get
    
    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.anyio
@pytest.mark.parametrize("use_case_num, params, expected_status, expected_fields", [
    # 1. Normal query, detail_level=low
    (1, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "detail_level": "low"}, 200, ["events_summary", "count"]),
    # 2. Normal query, detail_level=high
    (2, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "detail_level": "high"}, 200, ["events", "count"]),
    # 3. Limit parameter exceeding max allowed (pydantic should catch le=200) -> 422 Unprocessable Entity
    (3, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "limit": 201}, 422, ["detail"]),
    # 4. Limit parameter exactly at boundary
    (4, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "limit": 200}, 200, ["count"]),
    # 5. Missing industry -> 422
    (5, {"start_date": "2026-01-01", "end_date": "2026-01-31"}, 422, ["detail"]),
    # 6. Missing start_date -> 422
    (6, {"industry": "pizza_full_service", "end_date": "2026-01-31"}, 422, ["detail"]),
    # 7. Missing end_date -> 422
    (7, {"industry": "pizza_full_service", "start_date": "2026-01-01"}, 422, ["detail"]),
    # 8. Invalid date format start_date -> 422
    (8, {"industry": "pizza_full_service", "start_date": "01-01-2026", "end_date": "2026-01-31"}, 422, ["detail"]),
    # 9. Invalid date format end_date -> 422
    (9, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "not-a-date"}, 422, ["detail"]),
    # 10. start_date > end_date (Usually returns 200 with 0 results if unbounded by DB, or specific error depending on custom validation)
    (10, {"industry": "pizza_full_service", "start_date": "2026-01-31", "end_date": "2026-01-01"}, 200, ["count"]),
    # 11. market filter exact match
    (11, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "market": "Detroit"}, 200, ["count"]),
    # 12. market filter mismatch (should return 0)
    (12, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "market": "Los Angeles"}, 200, ["count"]),
    # 13. no events in date range (200 with 0 count)
    (13, {"industry": "pizza_full_service", "start_date": "2028-01-01", "end_date": "2028-01-31"}, 200, ["count"]),
    # 14. Boundary testing exactly on start_date
    (14, {"industry": "pizza_full_service", "start_date": "2026-01-15", "end_date": "2026-01-31"}, 200, ["count"]),
    # 15. Extreme limit = 1 ensures capping works
    (15, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "limit": 1}, 200, ["count"]),
    # 16. Extreme limit = 0 (If limit <= 0 allowed, might return 0)
    (16, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "limit": 0}, 200, ["count"]),
    # 17. Default detail_level acts as "low"
    (17, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31"}, 200, ["events_summary"]),
    # 18. Unknown detail_level -> falls through to "else:" mapping to high detail
    (18, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "detail_level": "unknown"}, 200, ["events", "count"]),
    # 19. SQL injection attempt in market string (Should be safely escaped by ORM, returning 0 results safely)
    (19, {"industry": "pizza_full_service", "start_date": "2026-01-01", "end_date": "2026-01-31", "market": "'; DROP TABLE users; --"}, 200, ["count"]),
])
async def test_agent_anomalies_use_cases(populated_db, use_case_num, params, expected_status, expected_fields):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/agent/anomalies", params=params)
        
    assert response.status_code == expected_status
    data = response.json()
    
    for field in expected_fields:
        assert field in data

    # Extra checks for specific use cases
    if use_case_num == 10:
        assert data["count"] == 0  # start > end -> no matches
    if use_case_num == 11:
        assert data["count"] == 1  # only Detroit pizza event
    if use_case_num == 12:
        assert data["count"] == 0  # Los Angeles has no events
    if use_case_num == 15:
        if "count" in data and "events" in data:
            assert len(data["events"]) <= 1

@pytest.mark.anyio
async def test_agent_anomaly_id_lookup_valid(populated_db):
    """Use case 20: Valid single event drill-down lookup"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Looking up Event 2
        response = await client.get("/api/v1/agent/anomaly/22222222-2222-2222-2222-222222222222")
        
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Event 2"
    assert data["market"] == "Detroit"
    assert "description" in data
    assert "raw_source_text" in data

@pytest.mark.anyio
async def test_agent_anomaly_id_lookup_invalid(populated_db):
    """Use case 21 (Bonus Edge Case): Invalid single event drill-down lookup -> 404"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/agent/anomaly/99999999-9999-9999-9999-999999999999")
        
    assert response.status_code == 404
