"""
Billing API Router
Handles integration with Stripe for Checkout / Customer Sessions and Webhook events.
"""
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models_auth import User
from app.routes.deps_auth import get_current_user
from app.config import settings
from app.stripe_client import create_checkout_session, create_portal_session

# Set up standard logger
import logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Billing"])

@router.post("/create-checkout-session")
async def create_checkout(
    lookup_key: str, 
    success_url: str, 
    cancel_url: str, 
    user: User = Depends(get_current_user)
):
    """Generate a linked Stripe checkout URL to upgrade a user's subscription tier."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured on this server.")
    
    try:
        url = create_checkout_session(
            user_id=str(user.id),
            email=user.email,
            lookup_key=lookup_key,
            success_url=success_url,
            cancel_url=cancel_url
        )
        return {"url": url}
    except Exception as e:
        logger.error(f"Checkout generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-portal-session")
async def create_portal(
    return_url: str, 
    user: User = Depends(get_current_user)
):
    """Generate a link for a user to manage their active Stripe subscription."""
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="User does not have an active Stripe integration.")
        
    try:
        url = create_portal_session(user.stripe_customer_id, return_url)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Listen to server-to-server webhook events dispatched from Stripe to sync our internal database state."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None

    if not settings.stripe_webhook_secret:
        return Response(status_code=400) # Integration not active

    # 1. Verify Request Origin (Cryptography check to ensure sender is truly Stripe)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.warning("Invalid Payload on Stripe Webhook")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.warning("Invalid Signature on Stripe Webhook")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Extract Event Logic
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Extract passed through internal UUID
            user_id = session.get('client_reference_id')
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')
            
            if user_id:
                # Update User Object
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                db_user = result.scalars().first()
                if db_user:
                    db_user.stripe_customer_id = customer_id
                    db_user.stripe_subscription_id = subscription_id
                    db_user.subscription_status = "active"
                    db_user.tier = "premium"
                    await db.commit()
                    logger.info(f"Successfully upgraded user {user_id} to PRO")
                    
        elif event['type'] == 'customer.subscription.updated' or event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            sub_id = subscription.get('id')
            status = subscription.get('status') 

            # Find matching user by stripe_subscription_id
            stmt = select(User).where(User.stripe_subscription_id == sub_id)
            result = await db.execute(stmt)
            db_user = result.scalars().first()
            if db_user:
                db_user.subscription_status = status
                
                # If deleted, downgrade them
                if status == 'canceled' or status == 'unpaid':
                    db_user.tier = "free"
                    db_user.stripe_subscription_id = None
                    
                await db.commit()
                logger.info(f"Successfully synced subscription status {status} for user {db_user.id}")

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    return {"status": "success"}
