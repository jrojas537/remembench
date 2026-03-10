import asyncio
from datetime import datetime, timezone
import json
from app.adapters.web_search import WebSearchAdapter
from app.services.classification import ClassificationService
from dotenv import load_dotenv

load_dotenv()

async def main():
    start = datetime(2025, 7, 8, tzinfo=timezone.utc)
    end = datetime(2025, 7, 8, 23, 59, 59, tzinfo=timezone.utc)
    
    adapter = WebSearchAdapter()
    print(f"Fetching for {start} to {end}...")
    events = await adapter.fetch_events(
        start_date=start,
        end_date=end,
        industry="pizza_full_service",
        latitude=42.3314,
        longitude=-83.0458,
        geo_label="Detroit Metro"
    )
    
    print(f"Fetched {len(events)} events from search.")
    for ev in events:
        print(f"[{ev.source}] {ev.description[:100]}...")

    classifier = ClassificationService()
    texts = [ev.raw_payload.get("content", ev.description) if ev.raw_payload else ev.description for ev in events]
    if texts:
        classifications = await classifier.classify_events_batch(texts, "pizza_full_service", search_start=start, search_end=end)
        for i, c in enumerate(classifications):
            print(f"--- Event {i} Classification ---")
            print(json.dumps(c, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
