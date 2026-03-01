"""
Remembench — Auth JWT Logic & Schemas

Handles password hashing and token generation. We keep schemas here
for simplicity. 
"""

import uuid
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

from app.config import settings

# Usually these are defined in your env config, falling back to static for fast execution.
SECRET_KEY = getattr(settings, "jwt_secret_key", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = getattr(settings, "jwt_algorithm", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = getattr(settings, "jwt_expire_minutes", 60 * 24 * 7) # 7 Days

# --- Auth Security Functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), 
        hashed_password.encode("utf-8")
    )

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Auth Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str | None = None


# --- User Schemas ---

class UserPreferenceBase(BaseModel):
    default_industry: str | None = Field(default="wireless_retail")
    default_market: str | None = Field(default=None)
    theme: str | None = Field(default="dark")

class UserPreferenceUpdate(UserPreferenceBase):
    pass

class UserPreferenceResponse(UserPreferenceBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_admin: bool
    tier: str
    preferences: UserPreferenceResponse | None = None

    model_config = {"from_attributes": True}
