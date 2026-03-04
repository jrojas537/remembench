import asyncio
from datetime import datetime
from dotenv import load_dotenv

from app.database import async_session_factory
from app.services import IngestionService

# 10 weeks from 2024, 10 weeks from 2026
TEST_DATES = [
    # 2024 Historical
    (datetime(2024, 1, 1), datetime(2024, 1, 7)),
    (datetime(2024, 2, 10), datetime(2024, 2, 17)),
    (datetime(2024, 3, 14), datetime(2024, 3, 21)),
    (datetime(2024, 4, 1), datetime(2024, 4, 7)),
    (datetime(2024, 6, 15), datetime(2024, 6, 22)),
    (datetime(2024, 7, 4), datetime(2024, 7, 11)),
    (datetime(2024, 9, 1), datetime(2024, 9, 7)),
    (datetime(2024, 10, 31), datetime(2024, 11, 6)),
    (datetime(2024, 11, 20), datetime(2024, 11, 27)),
    (datetime(2024, 12, 20), datetime(2024, 12, 27)),
    
    # 2026 Recent/Future
    (datetime(2026, 1, 1), datetime(2026, 1, 7)),
    (datetime(2026, 1, 15), datetime(2026, 1, 22)),
    (datetime(2026, 2, 1), datetime(2026, 2, 7)),
    (datetime(2026, 2, 14), datetime(2026, 2, 21)),
    (datetime(2026, 3, 1), datetime(2026, 3, 7)),
    (datetime(2026, 3, 8), datetime(2026, 3, 15)),
    (datetime(2026, 4, 1), datetime(2026, 4, 7)),
    (datetime(2026, 5, 1), datetime(2026, 5, 7)),
    (datetime(2026, 6, 1), datetime(2026, 6, 7)),
    (datetime(2026, 7, 1), datetime(2026, 7, 7)),
]

async def main():
    load_dotenv()
    ingestion = IngestionService()
    
    for i, (start, end) in enumerate(TEST_DATES, 1):
        print(f"\n[{i}/20] Running ingestion for {start.date()} to {end.date()}...")
        async with async_session_factory() as db:
            stats = await ingestion.ingest(
                db=db,
                start_date=start,
                end_date=end,
                industry="pizza_full_service",
                geo_label="Detroit Metro",
                latitude=42.3314,
                longitude=-83.0458
            )
            print(f"Stats: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
