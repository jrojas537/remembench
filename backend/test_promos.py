import asyncio
from datetime import datetime
from dotenv import load_dotenv

from app.database import async_session_factory
from app.services import IngestionService

async def main():
    load_dotenv()
    ingestion = IngestionService()
    
    start_date = datetime.strptime("2025-03-07", "%Y-%m-%d")
    end_date = datetime.strptime("2025-03-13", "%Y-%m-%d")
    
    print(f"Running targeted test for {start_date.date()} to {end_date.date()}...")
    async with async_session_factory() as db:
        stats = await ingestion.ingest(
            db=db,
            start_date=start_date,
            end_date=end_date,
            industry="pizza_all",
            latitude=42.3314, # Detroit
            longitude=-83.0458,
            geo_label="Detroit Metro"
        )
        print(f"Stats: {stats}")

    await ingestion.close_adapters()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
