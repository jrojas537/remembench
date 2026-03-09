import asyncio
import os
from datetime import datetime, timedelta
import sys

# add parent directory to path to reach app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.adapters.web_search import WebSearchAdapter

async def test_search():
    # Force Tavily/Exa on locally
    os.environ["WEB_SEARCH_ENABLED"] = "true"
    adapter = WebSearchAdapter()
    
    start_date = datetime.now() - timedelta(days=5)
    end_date = datetime.now()
    
    print(f"Testing Car Wash Search between {start_date.date()} and {end_date.date()}...")
    events = await adapter.fetch_events(
        start_date=start_date,
        end_date=end_date,
        industry="car_wash",
        geo_label="Detroit Metro"
    )
    
    print(f"Got {len(events)} events.")
    for e in events:
        print(f"- {e.title}")
        print(f"  {e.description[:100]}...")
        print("---")

asyncio.run(test_search())
