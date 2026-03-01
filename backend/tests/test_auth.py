"""
Integration Tests — Auth Routes

Tests FastAPI authentication endpoints.
"""

from unittest.mock import AsyncMock, MagicMock
from jose import jwt

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.auth_jwt import get_password_hash, SECRET_KEY, ALGORITHM
from app.models_auth import User, UserPreference


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
async def client(mock_session):
    async def override_get_db():
        yield mock_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestAuthAPI:

    @pytest.mark.asyncio
    async def test_register_user_success(self, client, mock_session):
        # Mock empty result so user does not exist
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_session.execute.return_value = mock_result

        # When adding to db, simulate what SQLAlchemy does minimally
        def side_effect(instance):
            if isinstance(instance, User):
                instance.id = "123e4567-e89b-12d3-a456-426614174000"
                instance.is_active = True
                instance.is_admin = False
                instance.tier = "free"
            if isinstance(instance, UserPreference):
                instance.id = "pref-uuid"

        mock_session.add.side_effect = side_effect

        resp = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "Password123!",
            "first_name": "Test",
            "last_name": "User"
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert mock_session.add.call_count == 2
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_register_email_exists(self, client, mock_session):
        # Mock user exists
        dummy_user = User(email="test@example.com")
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = dummy_user
        mock_session.execute.return_value = mock_result

        resp = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "Password123!"
        })

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Email already registered"

    @pytest.mark.asyncio
    async def test_login_success(self, client, mock_session):
        # Mock user exists with correct password
        hashed_pw = get_password_hash("Password123!")
        dummy_user = User(
            id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            hashed_password=hashed_pw,
            is_active=True
        )
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = dummy_user
        mock_session.execute.return_value = mock_result

        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "Password123!"
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify token contents
        payload = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123e4567-e89b-12d3-a456-426614174000"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client, mock_session):
        hashed_pw = get_password_hash("CorrectPassword!")
        dummy_user = User(email="test@example.com", hashed_password=hashed_pw)
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = dummy_user
        mock_session.execute.return_value = mock_result

        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword!"
        })

        assert resp.status_code == 401

class TestUsersAPI:

    @pytest.mark.asyncio
    async def test_get_me_success(self, client, mock_session):
        # Mock User query
        dummy_user = User(
            id="123e4567-e89b-12d3-a456-426614174000", 
            email="test@example.com", 
            is_active=True,
            is_admin=False,
            tier="free"
        )
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = dummy_user
        mock_session.execute.return_value = mock_result

        # Generate a valid token
        token = jwt.encode({"sub": str(dummy_user.id)}, SECRET_KEY, algorithm=ALGORITHM)

        resp = await client.get("/api/v1/users/me", headers={
            "Authorization": f"Bearer {token}"
        })

        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"
