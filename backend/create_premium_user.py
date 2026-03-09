import asyncio
from app.database import async_session_factory
from app.auth_jwt import get_password_hash
from app.models_auth import User, UserPreference
from sqlalchemy.future import select

async def main():
    print("Starting user provisioning...")
    async with async_session_factory() as db:
        email = "lammori@ammoriequity.com"
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        
        target_password = "AmmoryEquity#26"
        
        if user:
            print(f"User {email} already exists! Updating tier to premium and updating password.")
            user.tier = "premium"
            user.hashed_password = get_password_hash(target_password)
        else:
            print(f"Creating new premium user {email}...")
            user = User(
                email=email,
                hashed_password=get_password_hash(target_password),
                tier="premium",
                first_name="Ammory",
                last_name="Equity"
            )
            db.add(user)
            await db.flush()
            db_prefs = UserPreference(user_id=user.id)
            db.add(db_prefs)
            
        await db.commit()
        print(f"Success! {email} is now a Premium account.")

if __name__ == "__main__":
    asyncio.run(main())
