import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://remembench:changeme@127.0.0.1:5432/remembench")
    async with engine.begin() as conn:
        res = await conn.execute(text("UPDATE impact_events SET category = 'pizza_promotions' WHERE category = 'competitor_promo' AND industry LIKE 'pizza%';"))
        print(f"Updated {res.rowcount} rows")

if __name__ == "__main__":
    asyncio.run(main())
