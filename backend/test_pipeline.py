import asyncio
from datetime import datetime
import json

from app.adapters.web_search import WebSearchAdapter
from app.services.classification import ClassificationService
from dotenv import load_dotenv

async def main():
    load_dotenv()
    start = datetime(2025, 3, 10)
    end = datetime(2025, 3, 16)
    
    adapter = WebSearchAdapter()
    class_svc = ClassificationService()
    
    print("Fetching events from WebSearch...")
    events = await adapter.fetch_events(start, end, "pizza_all", geo_label="Detroit Metro")
    print(f"Found {len(events)} events.")
    for ev in events:
        print("\n=== Raw event ===")
        print("URL:", ev.raw_payload.get('url'))
        print("Text preview:", ev.description[:200])
        print("Classifying...")
        try:
            res = await class_svc.classify_event(ev.description, "pizza_all")
            print("Classification:", json.dumps(res, indent=2))
        except Exception as e:
            print("Error classifying:", e)

if __name__ == "__main__":
    asyncio.run(main())
