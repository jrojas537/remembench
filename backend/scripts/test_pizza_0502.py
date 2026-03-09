import asyncio
import os
from datetime import datetime
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.adapters.web_search import WebSearchAdapter

async def test_search():
    os.environ["WEB_SEARCH_ENABLED"] = "true"
    adapter = WebSearchAdapter()
    
    start_date = datetime(2025, 5, 1)
    end_date = datetime(2025, 5, 3)
    
    print(f"Testing Pizza Search between {start_date.date()} and {end_date.date()}...")
    events = await adapter.fetch_events(
        start_date=start_date,
        end_date=end_date,
        industry="pizza_all",
        geo_label="Detroit Metro"
    )
    
    print(f"Got {len(events)} events.")
    for e in events:
        print(f"- [{e.source}] {e.title}")
        print(f"  {e.description[:150]}...")
        print("---")

asyncio.run(test_search())
