"""
Remembench — Users Routes

Handles fetching current user profile and updating preferences.
Requires a valid JWT token.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_jwt import UserResponse, UserPreferenceUpdate, UserPreferenceResponse
from app.database import get_db
from app.logging import get_logger
from app.models_auth import User
from app.routes.deps_auth import get_current_user

logger = get_logger("routes.users")
router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently authenticated user's profile and preferences.
    """
    return current_user


@router.put("/me/preferences", response_model=UserPreferenceResponse)
async def update_user_preferences(
    prefs_in: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the authenticated user's preferences (like default industry and market).
    """
    prefs = current_user.preferences
    
    # Update only provided fields
    update_data = prefs_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prefs, key, value)
        
    db.add(prefs)
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(
        "auth_user_preferences_updated", 
        user_id=str(current_user.id),
        industry=prefs.default_industry,
    )
    
    return prefs
