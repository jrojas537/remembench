import json
import re
from datetime import datetime
from app.llm import get_llm_client
from app.logging import get_logger

logger = get_logger("services.classification")

class ClassificationService:
    """
    Uses the active LLM provider to classify raw event text into
    structured data: summary, severity score, and confidence.
    """

    def __init__(self):
        self.llm = get_llm_client()

    async def classify_event(self, text: str, industry: str) -> dict:
        """
        Passes raw text to the LLM to extract meaning.
        Returns a dict conforming to the expected event schema.
        """
        system_prompt = f"""You are an expert data analyst for the '{industry}' industry.
Analyze the following event text and extract key metrics for competitive intelligence.
Respond ONLY with a valid JSON object matching this schema, completely unformatted (no markdown blocks like ```json):
{{
    "severity": float, // 0.0 to 1.0 (1.0 = extremely high impact on operations/sales)
    "confidence": float, // 0.0 to 1.0 (How certain are you this event actually happened and is relevant)
    "category": string, // e.g., "weather", "macro_economic", "competitor_action", "supply_chain", "holiday", "local_event", "sports"
    "subcategory": string, // e.g., "bogo_promo", "network_outage", "winter_storm", "price_hike"
    "summary": string, // A clear, 1-2 sentence description of the event
    "competitor_actions": [
        {{
            "name": string, // Target competitor entity name (e.g. "Verizon", "Domino's")
            "action_type": string, // One of: "Promotion", "Outage", "Acquisition", "Price Change", "Legal", "General"
            "threat_level": float, // 0.0 to 1.0 (How dangerous is this move to our operations)
            "summary": string // Short semantic summary of the action
        }}
    ],
    "event_start_date": string, // Optional. YYYY-MM-DD. Start date of the event or promotion if it differs from the publication date. Null if generic.
    "event_end_date": string // Optional. YYYY-MM-DD. End date of the event or promotion if it is ongoing. Null if it is a single day event.
}}
"""

        try:
            response_text = await self.llm.complete(system=system_prompt, user=text, json_mode=True)
            
            # Clean potential markdown wrapping (e.g. from Anthropic)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            return json.loads(cleaned_text.strip())
            
        except Exception as e:
            logger.error("llm_classification_failed", error=str(e), text_snippet=text[:100])
            # Return safe default fallbacks if LLM fails
            return {
                "severity": 0.5,
                "confidence": 0.5,
                "category": "competitor_promo",
                "summary": text[:200],
                "competitor_actions": []
            }

    async def classify_events_batch(self, events_texts: list[str], industry: str, search_start: datetime | None = None, search_end: datetime | None = None) -> list[dict]:
        """
        Passes a batched array of unstructured strings to the LLM for parallel evaluation.
        Significantly reduces 'system prompt' token taxation by asking the model to evaluate
        10 events simultaneously and return exactly 10 matching JSON schemas in an array.
        
        If the model hallucinates or breaks the JSON schema mapping, the internal catch block
        falls back to injecting generic neutral rows explicitly averting entire ingestion failures.
        
        Args:
            events_texts: List of raw scraped strings (up to 2000 chars each)
            industry: The active vertical key binding the context (e.g. 'car_wash')
            
        Returns:
            list[dict]: Strongly typed Python objects mimicking the Pydantic schema required by PostGres.
        """
        if not events_texts:
            return []

        # Number each text so the LLM can align the output list properly
        numbered_texts = [f"Item {i}:\n{text}" for i, text in enumerate(events_texts)]
        payload = "\n\n---\n\n".join(numbered_texts)

        system_prompt = f"""You are an expert data analyst for the '{industry}' industry.
Analyze the following batch of event texts and extract key metrics for competitive intelligence.
Respond ONLY with a valid JSON array containing EXACTLY {len(events_texts)} objects in the exact same order as the input items.
The response must be completely unformatted (no markdown blocks like ```json).

Context: The user's active dashboard search window spans from {search_start.date() if search_start else 'unknown'} to {search_end.date() if search_end else 'unknown'}.
If an event is a generic ongoing coupon or promotion that is ACTIVE during this search window, you MUST set the `event_start_date` and `event_end_date` safely to cover its active period so it remains visible to the user, bypassing its original publication date.


Each object in the array must match this schema:
{{
    "severity": float, // 0.0 to 1.0 (1.0 = extremely high impact on operations/sales)
    "confidence": float, // 0.0 to 1.0 (How certain are you this event actually happened and is relevant)
    "category": string, // e.g., "weather", "macro_economic", "competitor_action", "supply_chain", "holiday", "local_event", "sports"
    "subcategory": string, // e.g., "bogo_promo", "network_outage", "winter_storm", "price_hike"
    "summary": string, // A clear, 1-2 sentence description of the event. IF this is a promotion or deal, you MUST include the exact price, discount amount, or promotion specifics here.
    "competitor_actions": [
        {{
            "name": string, // Target competitor entity name (e.g. "Verizon", "Domino's")
            "action_type": string, // One of: "Promotion", "Outage", "Acquisition", "Price Change", "Legal", "General"
            "threat_level": float, // 0.0 to 1.0 (How dangerous is this move to our operations)
            "summary": string // Short semantic summary of the action
        }}
    ],
    "event_start_date": string, // Optional. YYYY-MM-DD. Start date of the event or promotion if it differs from the publication date. Null if generic.
    "event_end_date": string // Optional. YYYY-MM-DD. End date of the event or promotion if it is ongoing. Null if it is a single day event.
}}
"""

        try:
            response_text = await self.llm.complete(system=system_prompt, user=payload, json_mode=True)
            
            # Clean potential markdown wrapping
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            results = json.loads(cleaned_text.strip())
            
            if not isinstance(results, list) or len(results) != len(events_texts):
                 raise ValueError("LLM returned malformed list structure length mismatch.")
                 
            # Ensure standard type coercion for all inner dict values
            return [{
                "severity": float(res.get("severity", 0.5)),
                "confidence": float(res.get("confidence", 0.5)),
                "category": str(res.get("category", "news")),
                "summary": str(res.get("summary", "No summary provided by LLM.")),
                "competitor_actions": res.get("competitor_actions", []),
                "details": res.get("details", {}),
                "event_start_date": res.get("event_start_date", None),
                "event_end_date": res.get("event_end_date", None)
            } for res in results]
            
        except Exception as e:
            logger.error("llm_batch_classification_failed", error=str(e), text_snippet=payload[:100])
            # Return safe default fallbacks bound strictly to schema expectations if the LLM fails
            return [{
                "severity": 0.5,
                "confidence": 0.3,
                "category": "news",
                "summary": "LLM classification bypassed due to upstream generation error: " + text[:150],
                "competitor_actions": []
            } for text in events_texts]

    async def generate_executive_briefing(self, events: list[dict], industry: str) -> dict:
        """
        Synthesizes a high-level strategic executive brief based on recent historically extracted data.
        
        Performance Architecture & Semantic Caching:
        - Context Optimization: Explicitly slices the array to the Top 50 recent events, parsing 
          only semantic titles/descriptions to protect LLM context windows bounds.
        - Idempotent Interceptor: A deterministic MD5 hash of the payload + industry creates a unique fingerprint.
        - Zero-Latency Cache: Bypasses network I/O and Anthropic token generation synchronously returning 
          responses from Redis for repeated dashboard views.
        - Expiration: Cache items inherit an automated 12-hour TTL (`EX=43200`) retaining market freshness.
        
        Args:
            events: List of fully classified events mapped from the primary DB fetch.
            industry: Target vertical context controlling the internal system prompt orientation.
            
        Returns:
            dict: The executive synthesis JSON including sentiment, threat scores, and macro trends.
        """
        if not events:
            return {
                "executive_summary": "No events found in the current timeframe to analyze.",
                "overall_threat_score": 0.0,
                "market_sentiment": "Stable",
                "immediate_actions_recommended": [],
                "key_opportunities": []
            }

        import hashlib
        import redis.asyncio as redis
        from app.config import settings

        # Truncate to reasonable limits to avoid token overflow
        event_texts: list[str] = []
        for e in events[:50]:
            title = e.get('title', 'Unknown')
            cat = e.get('category', 'Unknown')
            sev = e.get('severity', 0)
            desc = e.get('description', '')
            if desc is None:
                desc = ""
                
            event_texts.append(f"[{cat} - Severity: {sev}] {title}: {desc[:200]}")

        payload = "\n".join(event_texts)

        # -- REDIS CACHE INTERCEPT --
        # We uniquely identify identical requests (same industry + identical text chunk).
        cache_key_string = f"{industry}::{payload}"
        cache_key = "llm_briefing_" + hashlib.md5(cache_key_string.encode('utf-8')).hexdigest()
        
        # Connect to the existing Celery broker explicitly as an async cache
        redis_client = redis.from_url(settings.redis_url)
        try:
            cached_briefing = await redis_client.get(cache_key)
            if cached_briefing:
                logger.info("llm_briefing_cache_hit", key=cache_key)
                return json.loads(cached_briefing)
        except Exception as e:
            logger.warning("redis_cache_read_failure", error=str(e))
            pass # Failsafe open if Redis dies; allow the LLM to process anyway

        system_prompt = f"""You are a Chief Strategy Officer for the '{industry}' industry.
You are scanning the following list of recent impact events. 
Synthesize these events into a structured JSON Executive Briefing.
Do NOT list individual events. Instead, identify the macro trends.
Are competitors launching new features? Is weather disrupting supply chains? Is sentiment negative?

Respond ONLY with a valid JSON object representing the briefing. Never print markdown wrapping (like ```json), just the raw object.
The JSON must map exactly to this schema:
{{
    "executive_summary": string, // Paragraph overviewing the broad impact and significance.
    "overall_threat_score": float, // 0.0 to 1.0 (Aggregated metric of negative pressure in this market)
    "key_opportunities": list[string], // Bullet points outlining market gaps or promotional opportunities.
    "immediate_actions_recommended": list[string], // Tactical next steps for operators based on intelligence.
    "market_sentiment": string // Exactly one of: "Bullish", "Bearish", "Volatile", "Stable"
}}
        """

        try:
            response_text = await self.llm.complete(system=system_prompt, user=payload, json_mode=True)
            
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
                
            final_json = json.loads(cleaned_text.strip())
            
            # Save the successful response back to Redis for 12 hours (43200 seconds)
            try:
                await redis_client.set(cache_key, json.dumps(final_json), ex=43200)
            except Exception as e:
                logger.warning("redis_cache_write_failure", error=str(e))
                
            return final_json
        except Exception as e:
            logger.error("llm_briefing_failed", error=str(e))
            return {
                "executive_summary": "Unable to generate AI briefing at this time due to an LLM service error.",
                "overall_threat_score": 0.5,
                "key_opportunities": [],
                "immediate_actions_recommended": [],
                "market_sentiment": "Stable"
            }
        finally:
            await redis_client.aclose()
