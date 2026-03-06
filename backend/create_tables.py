import asyncio
from app.database import _get_engine
from app.models import Base
from app.models_auth import User, UserPreference

async def init_models():
    engine = _get_engine()
    async with engine.begin() as conn:
        print("Dropping and creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_models())
