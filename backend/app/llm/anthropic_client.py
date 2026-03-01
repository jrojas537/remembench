import anthropic
from app.config import settings
from app.llm.base import BaseLLMClient

class AnthropicClient(BaseLLMClient):
    """Anthropic Claude LLM implementation."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key or "dummy_key")
        self.model = settings.anthropic_model

    async def complete(self, system: str, user: str) -> str:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.0,
            system=system,
            messages=[
                {"role": "user", "content": user}
            ]
        )
        return response.content[0].text
