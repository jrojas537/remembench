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
    "category": string, // e.g., "weather", "macro_economic", "competitor_action", "supply_chain", "holiday", "local_event"
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
                "severity": 0.0,
                "confidence": 0.0,
                "category": "unclassified",
                "summary": text[:200]
            }
