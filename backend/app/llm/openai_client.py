import openai
from app.config import settings
from app.llm.base import BaseLLMClient

class OpenAIClient(BaseLLMClient):
    """OpenAI LLM implementation."""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.client = openai.AsyncOpenAI(api_key=self.api_key or "dummy_key")
        self.model = settings.openai_model

    async def complete(self, system: str, user: str, json_mode: bool = False) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")
            
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
