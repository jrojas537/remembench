import asyncio
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.adapters.holidays import HolidayAdapter

async def test_run():
    adapter = HolidayAdapter()
    res = await adapter.fetch_events(
        start_date=datetime(2025, 5, 20),
        end_date=datetime(2025, 5, 30),
        geo_label="Detroit Metro",
        industry="all"
    )
    print(f"Found {len(res)} events:")
    for r in res:
        print(f" - {r.start_date.date()}: {r.title} ({r.description})")

asyncio.run(test_run())
