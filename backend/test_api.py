import asyncio
import httpx
import time
import uuid
from datetime import datetime
from httpx import ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.routes.deps_auth import get_current_user
from app.database import get_db

async def mock_auth():
    return {"id": "test-user", "email": "test@example.com"}

async def override_get_db():
    session = AsyncMock()
    
    # Create fake events for the LLM
    mock_event = MagicMock()
    mock_event.id = uuid.uuid4()
    mock_event.source = "mock"
    mock_event.source_id = "1"
    mock_event.category = "news"
    mock_event.subcategory = "test"
    mock_event.title = "Local competitor launched new promo."
    mock_event.description = "We found 50% discounts nearby."
    mock_event.severity = 0.8
    mock_event.confidence = 0.9
    mock_event.start_date = datetime.now()
    mock_event.end_date = datetime.now()
    mock_event.geo_radius_km = 10.0
    mock_event.geo_label = "Detroit"
    mock_event.industry = "pizza_full_service"
    mock_event.raw_payload = {}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    
    # We also need to handle the aggregate summary mock specifically if called
    mock_result.all.return_value = []
    
    session.execute.return_value = mock_result
    yield session

app.dependency_overrides[get_current_user] = mock_auth
app.dependency_overrides[get_db] = override_get_db

async def test_apis():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("=== 1. Testing Industries API ===")
        resp = await client.get("/api/v1/industries/")
        print("Status:", resp.status_code)
        
        print("\n=== 2. Testing Car Wash Events ===")
        start_time = time.time()
        resp = await client.get("/api/v1/events/?industry=car_wash&limit=5")
        duration = time.time() - start_time
        print(f"Status: {resp.status_code} in {duration:.2f}s")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Events found: {len(data)}")
            for e in data:
                print(f"- [{e['category']}] {e['title'][:50]}")

        print("\n=== 3. Testing Pizza Full Service Events ===")
        start_time = time.time()
        resp = await client.get("/api/v1/events/?industry=pizza_full_service&limit=5")
        duration = time.time() - start_time
        print(f"Status: {resp.status_code} in {duration:.2f}s")
        events_to_brief = []
        if resp.status_code == 200:
            data = resp.json()
            print(f"Events found: {len(data)}")
            for e in data:
                print(f"- [{e['category']}] {e['title'][:50]}")
                events_to_brief.append(e)

        print("\n=== 4. Testing YoY Compare (Pizza) ===")
        start_time = time.time()
        resp = await client.get("/api/v1/yoy/compare?industry=pizza_full_service&start_date=2024-03-01T00:00:00Z&end_date=2024-03-31T23:59:59Z")
        duration = time.time() - start_time
        print(f"Status: {resp.status_code} in {duration:.2f}s")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Current Period Events: {data['current_period']['total_events']}")
            print(f"Prior Period Events: {sum(p['total_events'] for p in data['prior_periods'])}")
            
        print("\n=== 5. Testing Executive Briefing Caching ===")
        if not events_to_brief:
            print("No events found to test briefing.")
            return

        briefing_payload = {"industry": "pizza_full_service", "events": events_to_brief}
        
        print("  -> First Call (Expected LLM delay)...")
        start_time = time.time()
        resp1 = await client.post("/api/v1/events/briefing", json=briefing_payload)
        duration1 = time.time() - start_time
        print(f"  Status: {resp1.status_code} in {duration1:.2f}s")
        
        print("  -> Second Call (Expected Redis Cache Instant)...")
        start_time = time.time()
        resp2 = await client.post("/api/v1/events/briefing", json=briefing_payload)
        duration2 = time.time() - start_time
        print(f"  Status: {resp2.status_code} in {duration2:.2f}s")
        
        if resp1.status_code == 200:
            print("\nBriefing Snippet:", resp1.json().get("briefing", {}).get("executive_summary", "No summary")[:100], "...")

if __name__ == "__main__":
    asyncio.run(test_apis())
