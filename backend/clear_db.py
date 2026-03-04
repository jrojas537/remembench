import asyncio
from sqlalchemy import text
from app.database import async_session_factory

async def main():
    async with async_session_factory() as db:
        await db.execute(text("DELETE FROM impact_events"))
        await db.commit()
        print("Successfully wiped previous duplicated impact_events data!")

if __name__ == "__main__":
    asyncio.run(main())
