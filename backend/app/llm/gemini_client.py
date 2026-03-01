import os
import google.generativeai as genai
from app.config import settings
from app.llm.base import BaseLLMClient

class GeminiClient(BaseLLMClient):
    """Google Gemini LLM implementation."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_name = settings.gemini_model

    async def complete(self, system: str, user: str) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        
        # Gemini expects system instructions in the GenerativeModel constructor or as a special part
        # We can construct it locally to keep the `complete` method dynamic
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system
        )
        
        # Run asynchronously
        response = await model.generate_content_async(
            contents=user,
            generation_config={"temperature": 0.0}
        )
        return response.text
