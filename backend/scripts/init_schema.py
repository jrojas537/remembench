import asyncio
from app.database import engine, Base
import app.models # enforce model registration

async def init_db():
    async with engine.begin() as conn:
        print('Creating tables...')
        await conn.run_sync(Base.metadata.create_all)
        print('Done.')

if __name__ == '__main__':
    asyncio.run(init_db())
