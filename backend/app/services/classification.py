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
    "details": {{
        "competitor_name": string | null, // Name of the competitor if mentioned (e.g., "Verizon", "Dominos")
        "promotion_details": string | null, // Specifics of a deal (e.g., "50% off", "iPhone 15 BOGO")
        "detailed_impact": string, // Why this matters specifically for a business in this industry
        "source_link": string | null // The original URL if clearly present in the text
    }}
}}
"""

        try:
            response_text = await self.llm.complete(system=system_prompt, user=text)
            
            # Use regex to robustly extract the first JSON block amidst conversational hallucination
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not match:
                raise ValueError("No JSON object found in LLM response")
            
            cleaned_text = match.group(0)
            return json.loads(cleaned_text)
            
        except Exception as e:
            logger.error("llm_classification_failed", error=str(e), text_snippet=text[:100])
            # Return safe default fallbacks if LLM fails
            return {
                "severity": 0.5,
                "confidence": 0.5,
                "category": "competitor_promo",
                "summary": text[:200]
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
    "details": {{
        "competitor_name": string | null, // Name of the competitor if mentioned (e.g., "Verizon", "Dominos")
        "promotion_details": string | null, // Specifics of a deal (e.g., "50% off", "iPhone 15 BOGO")
        "detailed_impact": string, // Why this matters specifically for a business in this industry
        "source_link": string | null // The original URL if clearly present in the text
    }}
}}
"""

        try:
            response_text = await self.llm.complete(system=system_prompt, user=payload)
            
            # We strictly extract JSON arrays handling LLM markdown variations
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not match:
                raise ValueError("No JSON array bounds found in LLM response wrapper")
            
            cleaned_text = match.group(0)
            results = json.loads(cleaned_text)
            
            if not isinstance(results, list) or len(results) != len(events_texts):
                 raise ValueError("LLM returned malformed list structure length mismatch.")
                 
            # Ensure standard type coercion for all inner dict values
            return [{
                "severity": float(res.get("severity", 0.5)),
                "confidence": float(res.get("confidence", 0.5)),
                "category": str(res.get("category", "news")),
                "summary": str(res.get("summary", "No summary provided by LLM."))
            } for res in results]
            
        except Exception as e:
            logger.error("llm_batch_classification_failed", error=str(e), text_snippet=payload[:100])
            # Return safe default fallbacks bound strictly to schema expectations if the LLM fails
            return [{
                "severity": 0.5,
                "confidence": 0.3,
                "category": "news",
                "summary": "LLM classification bypassed due to upstream generation error: " + text[:150]
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
Synthesize these events into a 2-3 sentence 'Executive Briefing'.
Do NOT list individual events. Instead, identify the macro trends.
Are competitors launching new features? Is weather disrupting supply chains? Is sentiment negative?
Highlight the most critical insights and end with a 1-sentence recommendation.
Respond ONLY with the plain text briefing. Do not use markdown formatting.
        """

        try:
            response_text = await self.llm.complete(system=system_prompt, user=payload)
            return response_text.strip()
        except Exception as e:
            logger.error("llm_briefing_failed", error=str(e))
            return "Unable to generate AI briefing at this time due to an LLM service error."
