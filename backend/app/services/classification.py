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
    ]
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

    async def classify_events_batch(self, events_texts: list[str], industry: str) -> list[dict]:
        """
        Passes a batch of raw texts to the LLM to extract meaning.
        Returns a list of dicts conforming to the expected event schema.
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
    ]
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
                "competitor_actions": res.get("competitor_actions", [])
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

    async def generate_executive_briefing(self, events: list[dict], industry: str) -> str:
        """
        Reads an array of event dictionaries and synthesizes a high-level strategic brief.
        Truncates list size to avoid context-window overflows on heavy historical queries.
        """
        if not events:
            return "No events found in the current timeframe to analyze."

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
                
            return json.loads(cleaned_text.strip())
        except Exception as e:
            logger.error("llm_briefing_failed", error=str(e))
            return {
                "executive_summary": "Unable to generate AI briefing at this time due to an LLM service error.",
                "overall_threat_score": 0.5,
                "key_opportunities": [],
                "immediate_actions_recommended": [],
                "market_sentiment": "Stable"
            }
