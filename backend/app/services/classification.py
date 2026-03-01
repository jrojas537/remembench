import json
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
Analyze the following event text and extract key metrics.
Respond ONLY with a valid JSON object matching this schema, completely unformatted (no markdown blocks like ```json):
{{
    "severity": float, // 0.0 to 1.0 (1.0 = extremely high impact on operations/sales)
    "confidence": float, // 0.0 to 1.0 (How certain are you this event actually happened and is relevant)
    "category": string, // e.g., "weather", "macro_economic", "competitor_action", "supply_chain"
    "summary": string // A clear, 1-2 sentence description of the event
}}
"""

        try:
            response_text = await self.llm.complete(system=system_prompt, user=text)
            
            # Clean up formatting if the LLM ignores instructions and returns markdown blocks
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
                "severity": 0.0,
                "confidence": 0.0,
                "category": "unclassified",
                "summary": text[:200]
            }
