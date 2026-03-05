import asyncio
import httpx
from datetime import datetime, timedelta, timezone

API_BASE = "http://localhost:8000/api/v1"
# Update headers with local valid credentials or API key if necessary, assuming testing locally without auth if not strictly enforced, else we will need it
HEADERS = {"X-API-Key": "test_key_if_needed"} # Replace as needed

async def test_ingestion():
    # 1. Test Historical Ingestion (e.g. Early 2024)
    print("--- Testing Historical Ingestion (2024) ---")
    start_2024 = "2024-03-01T00:00:00Z"
    end_2024 = "2024-03-07T00:00:00Z"
    
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                f"{API_BASE}/ingestion/run",
                params={
                    "start_date": start_2024,
                    "end_date": end_2024,
                    "industry": "pizza_delivery",
                    "geo_label": "Detroit Metro"
                }
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("Historical Payload:", resp.json())
            else:
                print("Failed:", resp.text)
        except Exception as e:
            print("Failed to run 2024 historical test:", str(e))

    # 2. Test Recent/Future Ingestion (e.g. Current Time / 2026)
    print("\n--- Testing Recent Ingestion (2026) ---")
    now = datetime.now(timezone.utc)
    start_2026 = (now - timedelta(days=3)).isoformat()
    end_2026 = now.isoformat()

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                f"{API_BASE}/ingestion/run",
                params={
                    "start_date": start_2026,
                    "end_date": end_2026,
                    "industry": "pizza_delivery",
                    "geo_label": "Detroit Metro"
                }
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("Recent Payload:", resp.json())
            else:
                print("Failed:", resp.text)
        except Exception as e:
            print("Failed to run 2026 recent test:", str(e))

if __name__ == "__main__":
    asyncio.run(test_ingestion())
