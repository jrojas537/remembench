"""
Remembench — Webhook Routing

Enables users to register URLs for real-time pushing of Anomaly Events, effectively
acting as a foundational backbone for SaaS alert integrations and MCP Tool wrappers.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth_jwt import get_current_user
from app.database import get_db
from app.logging import get_logger
from app.models_auth import User, WebhookSubscription
from app.schemas import WebhookCreate, WebhookResponse

logger = get_logger("routes.webhooks")
router = APIRouter()


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_in: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new active Webhook destination securely tied to the current User's tenant ID.
    The response payload dictates a generated 'secret_token' so the user can HMAC-verify payloads.
    """
    # Check bounds (limit 5 per user to easily mitigate malicious spam targets)
    result = await db.execute(select(WebhookSubscription).where(WebhookSubscription.user_id == current_user.id))
    existing_hooks = result.scalars().all()
    if len(existing_hooks) >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum limit of 5 webhooks reached per user tier."
        )

    db_webhook = WebhookSubscription(
        user_id=current_user.id,
        url=webhook_in.url,
        name=webhook_in.name,
        min_severity=webhook_in.min_severity,
        is_active=webhook_in.is_active
    )
    
    db.add(db_webhook)
    await db.commit()
    await db.refresh(db_webhook)

    logger.info("webhook_created", user_id=str(current_user.id), webhook_id=str(db_webhook.id))
    return db_webhook


@router.get("/", response_model=List[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns an index of all webhooks owned mechanically by the authenticated user.
    """
    result = await db.execute(select(WebhookSubscription).where(WebhookSubscription.user_id == current_user.id))
    return result.scalars().all()


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Safely tears down a user's webhook notification flow based on valid IDs.
    """
    result = await db.execute(
        select(WebhookSubscription)
        .where(WebhookSubscription.id == webhook_id)
        .where(WebhookSubscription.user_id == current_user.id)
    )
    webhook = result.scalars().first()
    
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook configuration missing or unauthorized.")

    await db.delete(webhook)
    await db.commit()
    
    logger.info("webhook_deleted", user_id=str(current_user.id), webhook_id=str(webhook_id))
    return
