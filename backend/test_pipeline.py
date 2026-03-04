import asyncio
from datetime import datetime
import json
from difflib import SequenceMatcher

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
    print(f"Initially found {len(events)} events.")
    
    # 1. Deduplication
    unique_events = []
    seen_texts = []
    
    for ev in events:
        text_to_analyze = ev.raw_payload.get("content", ev.description) if ev.raw_payload else ev.description
        if not text_to_analyze:
            continue
            
        is_duplicate = False
        for seen in seen_texts:
            if SequenceMatcher(None, text_to_analyze, seen).ratio() > 0.85:
                is_duplicate = True
                break
                
        if not is_duplicate:
            seen_texts.append(text_to_analyze)
            unique_events.append(ev)

    print(f"After Semantic Deduplication: {len(unique_events)} unique events remain.")
    
    # 2. Batch Classification
    print("\nRunning Batched Classification (Chunk size 10)...")
    texts = [ev.raw_payload.get("content", ev.description) if ev.raw_payload else ev.description for ev in unique_events]
    
    # Just run the first batch for testing
    if texts:
        batch = texts[:10]
        print(f"Sending batch of {len(batch)} items to LLM in one API call...")
        try:
            results = await class_svc.classify_events_batch(batch, "pizza_all")
            print(f"Success! Received {len(results)} items back in array.")
            for i, res in enumerate(results):
                print(f"\n--- Item {i} parsed ---")
                print("Category:", res.get("category"))
                print("Title:", res.get("summary"))
        except Exception as e:
            print("Batch classification failed:", e)
            
if __name__ == "__main__":
    asyncio.run(main())
