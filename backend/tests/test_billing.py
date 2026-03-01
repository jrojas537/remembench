"""
Integration Tests — Billing Routes

Tests FastAPI Stripe Billing endpoints including webhook verification logic.
"""
import stripe
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.models_auth import User

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
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


class TestBillingWebhook:

    @pytest.mark.asyncio
    @patch("stripe.Webhook.construct_event")
    @patch("app.routes.billing.settings.stripe_webhook_secret", new="test_secret")
    async def test_webhook_unauthorized_signature(self, mock_construct_event, client):
        
        # Simulate an unauthorized request hitting the webhook endpoint
        mock_construct_event.side_effect = stripe.SignatureVerificationError(
            "Invalid sig", sig_header="bad_sig"
        )
        
        resp = await client.post("/api/v1/billing/webhook", json={"id": "evt_test"}, headers={"stripe-signature": "bad_sig"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid signature"


    @pytest.mark.asyncio
    @patch("stripe.Webhook.construct_event")
    @patch("app.routes.billing.settings.stripe_webhook_secret", new="test_secret")
    async def test_webhook_checkout_completed(self, mock_construct_event, client, mock_session):
        # Mock stripe SDK return event
        mock_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": "123e4567-e89b-12d3-a456-426614174000",
                    "customer": "cus_12345",
                    "subscription": "sub_12345"
                }
            }
        }
        mock_construct_event.return_value = mock_event
        
        # Mock the DB User that would be updated
        dummy_user = User(
            id="123e4567-e89b-12d3-a456-426614174000", 
            email="test@example.com", 
            is_active=True
        )
        
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = dummy_user
        mock_session.execute.return_value = mock_result
        
        resp = await client.post("/api/v1/billing/webhook", json={}, headers={"stripe-signature": "good_sig"})
        
        # Verify
        assert resp.status_code == 200
        assert mock_session.commit.called
        assert dummy_user.tier == "pro"
        assert dummy_user.stripe_customer_id == "cus_12345"
        assert dummy_user.subscription_status == "active"
