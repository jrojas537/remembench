import os
from google import genai
from google.genai import types
from app.config import settings
from app.llm.base import BaseLLMClient

class GeminiClient(BaseLLMClient):
    """Google Gemini LLM implementation."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
        self.model_name = settings.gemini_model

    async def complete(self, system: str, user: str) -> str:
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not set")
        
        # Run asynchronously using the modern SDK
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.0
            )
        )
        return response.text
