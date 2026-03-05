import asyncio
import httpx
from datetime import datetime, timedelta
from app.main import app
import logging
from app.config import settings
import json

# We silence the debug logs so we can see the print lines clearly
logging.getLogger("adapter.rss").setLevel(logging.CRITICAL)
logging.getLogger("web_search_adapter").setLevel(logging.CRITICAL)
logging.getLogger("adapter.gdelt").setLevel(logging.CRITICAL)

async def run_stress_test():
    print("Starting 20-Query ASGI Database Ingestion Stress Test...\n")
    
    industries = ["pizza_full_service", "wireless_retail", "gyms", "hotels"]
    markets = ["Detroit", "Chicago", "New York City", "Austin", "Seattle", "Los Angeles"]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    s_date = start_date.strftime("%Y-%m-%d")
    e_date = end_date.strftime("%Y-%m-%d")
    
    # Collect 20 queries
    test_cases = []
    for ind in industries:
        for mkt in markets:
            test_cases.append((ind, mkt))
            
    success = 0
    failed = 0
    
    # httpx.ASGITransport ensures we trigger the FastAPI lifespan() events 
    # which binds the global HTTP connections and limits.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        for i, (ind, mkt) in enumerate(test_cases[:20], 1):
            print(f"[{i}/20] Ingesting {ind} in {mkt}...")
            
            try:
                # 1. Ingestion Phase
                params = {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "industry": ind,
                    "geo_label": mkt
                }
                # Must use the secret bypass logic if relying on API boundaries
                headers = {"X-API-Key": settings.api_key or "dev-mode"}
                
                # 1. Ingestion Phase
                print(f"  -> Sending HTTP POST to /api/v1/ingestion/run")
                ingest_res = await client.post("/api/v1/ingestion/run", params=params, headers=headers)
                if ingest_res.status_code == 200:
                    summary = ingest_res.json()
                    print(f"  -> INGEST SUCCESS: Fetched {summary['total_fetched']}, Inserted {summary['inserted']} records natively.")
                else:
                    print(f"  -> INGEST FAILED: {ingest_res.status_code} - {ingest_res.text}")
                    failed += 1
                    continue
                
                # 2. Briefing Phase via Agent API
                print(f"  -> Sending HTTP GET for Executive Briefing")
                briefing_res = await client.get(
                    f"/api/v1/agent/briefing", 
                    params={"industry": ind, "geoLabel": mkt, "days": 2},
                    headers=headers
                )
                
                if briefing_res.status_code == 200:
                    briefing = briefing_res.json()
                    data = briefing.get("briefing", {})
                    # Double-parsed due to router abstraction
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except:
                            pass
                    if isinstance(data, dict) and "overall_threat_score" in data:
                        print(f"  -> BRIEFING SUCCESS: Threat level {data['overall_threat_score']} - Sentiment: {data.get('market_sentiment')}")
                    else:
                        print(f"  -> BRIEFING FORMAT ERROR: Not a valid structured dict.")
                else:
                    print(f"  -> BRIEFING FAILED: {briefing_res.status_code}")
                    
                success += 1
                
            except Exception as e:
                print(f"  -> FAILED: {str(e)[:100]}")
                failed += 1
                
            await asyncio.sleep(2)
            
    print(f"\n--- Test Complete ---")
    print(f"Total: 20 | Success: {success} | Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
