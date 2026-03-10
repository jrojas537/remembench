"""
Remembench — Webhook Broadcast Service

Intercepts fully normalized ImpactEvents as they exit the LLM Classification pipeline.
Cross-references the active `WebhookSubscription` tables and dispatches 
standardized JSON payloads to user-defined endpoints asynchronously to 
enable instantaneous alerts in Slack, Zapier, Make, and arbitrary HTTP receivers.
"""

import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import List

import httpx
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models import ImpactEvent
from app.models_auth import WebhookSubscription
from app.schemas import WebhookEventPayload

logger = get_logger("services.webhooks")


def generate_signature(payload_bytes: bytes, secret: str) -> str:
    """Generates a SHA-256 HMAC signature so clients can verify the origin."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


async def broadcast_anomalies(db: AsyncSession, events: List[ImpactEvent]) -> None:
    """
    Core fanout engine. Checks if any new events exceed user-defined severity
    thresholds and pushes payloads to their registered webhooks immediately.
    """
    if not events:
        return

    # To optimize, we find events that are genuinely impactful before waking up the db
    notable_events = [e for e in events if e.severity >= 0.5]
    if not notable_events:
        return

    # Grab every active webhook system-wide
    # In an ultra-massive scale system, you would JOIN on user_id and industry preferences.
    # Because Remembench is curating high-signal data, we query active hooks and filter in memory.
    result = await db.execute(select(WebhookSubscription).where(WebhookSubscription.is_active == True))
    active_hooks = result.scalars().all()

    if not active_hooks:
        return

    logger.info("webhooks_broadcast_start", hooks_count=len(active_hooks), events=len(notable_events))

    # We enforce a strict timeout to ensure malicious or dead client servers 
    # cannot freeze our Celery worker threads.
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        for hook in active_hooks:
            # Determine which events meet THIS specific user's severity threshold
            # Note: Later we can add 'industry' filtering to the WebhookSubscription model
            trigger_events = [e for e in notable_events if e.severity >= hook.min_severity]
            
            for event in trigger_events:
                payload = WebhookEventPayload(
                    event_id=event.id,
                    title=event.title or "Unknown Event",
                    category=event.category or "uncategorized",
                    severity=event.severity,
                    confidence=event.confidence,
                    market=event.geo_label,
                    industry=event.industry,
                    timestamp=event.start_date.isoformat() if event.start_date else datetime.now(timezone.utc).isoformat()
                )
                
                payload_json = payload.model_dump_json()
                payload_bytes = payload_json.encode('utf-8')
                
                # Sign the payload
                signature = generate_signature(payload_bytes, hook.secret_token)
                
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Remembench-Webhook-Service/1.0",
                    "X-Remembench-Signature": signature,
                    "X-Remembench-Event-ID": str(event.id)
                }

                try:
                    response = await client.post(hook.url, content=payload_bytes, headers=headers)
                    logger.debug(
                        "webhook_dispatched", 
                        hook_id=str(hook.id), 
                        status=response.status_code,
                        event_id=str(event.id)
                    )
                except httpx.RequestError as exc:
                    logger.error(
                        "webhook_delivery_failed", 
                        hook_id=str(hook.id), 
                        url=hook.url, 
                        error=str(exc)
                    )
                    # We continue the loop; one dead webhook shouldn't break others
                    continue
