"""
Stripe Integration Client
Wrapper for handling Stripe subscriptions and generating checkout URLs.
"""
import stripe
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe API Key
stripe.api_key = settings.stripe_secret_key

def create_checkout_session(user_id: str, email: str, lookup_key: str, success_url: str, cancel_url: str):
    """Generates a checkout session for a designated subscription tier."""
    if not stripe.api_key:
        logger.error("Stripe Secret Key is missing.")
        raise ValueError("Stripe configuration error")
        
    try:
        # Resolve the lookup_key to a real Price ID using the API
        prices = stripe.Price.list(
            lookup_keys=[lookup_key],
            expand=["data.product"]
        )
        if not prices.data:
            raise ValueError(f"Price lookup_key '{lookup_key}' not found in Stripe. Please create it.")
            
        price_id = prices.data[0].id

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url + '?success=true&session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url + '?canceled=true',
            customer_email=email,
            client_reference_id=user_id, # Link this checkout session to our internal UUID
        )
        return checkout_session.url
        
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {str(e)}")
        raise e

def create_portal_session(customer_id: str, return_url: str):
    """Generates a customer portal session for a logged in user to manage their subscription."""
    if not stripe.api_key:
        raise ValueError("Stripe configuration error")
        
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return portal_session.url
    except Exception as e:
        logger.error(f"Error creating Stripe portal session: {str(e)}")
        raise e
