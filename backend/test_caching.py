import asyncio
from datetime import datetime, timezone, timedelta
from app.database import async_session_factory
from app.routes.ingestion import run_ingestion

async def test_cache():
    # Make a run that simulates a historical request (older than 14 days)
    start = datetime(2024, 3, 7, tzinfo=timezone.utc)
    end = datetime(2024, 3, 13, tzinfo=timezone.utc)
    
    print("--- RUN 1: Should Hit Network and Insert ---")
    async with async_session_factory() as db:
        res1 = await run_ingestion(start, end, "pizza_all", 42.3314, -83.0458, "Detroit Metro", db)
        print(f"Run 1 Fetched: {res1.get('total_fetched')}")
        
    print("\n--- RUN 2: Should Hit Cache Instantly ---")
    async with async_session_factory() as db:
        res2 = await run_ingestion(start, end, "pizza_all", 42.3314, -83.0458, "Detroit Metro", db)
        print(f"Run 2 Cached Total: {res2.get('total_fetched')}")

if __name__ == "__main__":
    asyncio.run(test_cache())
