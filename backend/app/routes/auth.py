"""
Remembench — Auth Routes

Handles User Registration and Login. 
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth_jwt import (
    Token,
    UserCreate,
    UserResponse,
    create_access_token,
    get_password_hash,
    verify_password,
    UserLogin,
)
from app.database import get_db
from app.logging import get_logger
from app.models_auth import User, UserPreference

logger = get_logger("routes.auth")
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    Creates a new user account and sets up empty default preferences.
    """
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        logger.warning("auth_registration_failed_email_exists", email=user_in.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password and create user
    hashed_pwd = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )
    db.add(db_user)
    
    # Must flush to get user.id before creating preferences
    await db.flush() 
    
    # Create default preferences for the new user
    db_prefs = UserPreference(user_id=db_user.id)
    db.add(db_prefs)

    await db.commit()
    # Explicitly load preferences so the response model can build
    await db.refresh(db_user, attribute_names=["preferences"])

    logger.info("auth_user_registered", user_id=str(db_user.id), email=db_user.email)
    return db_user


@router.post("/login", response_model=Token)
async def login_for_access_token(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return a JWT token.
    Uses JSON body `email` and `password` inside `UserLogin`. 
    """
    # Retrieve user
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        logger.warning("auth_login_failed_invalid_credentials", email=user_in.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning("auth_login_failed_inactive_user", email=user_in.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Generate token
    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info("auth_user_logged_in", user_id=str(user.id), email=user.email)
    
    return {"access_token": access_token, "token_type": "bearer"}
