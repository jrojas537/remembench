from app.config import settings
from app.llm.base import BaseLLMClient

def get_llm_client() -> BaseLLMClient:
    """
    Factory function to get the configured LLM client based on settings.llm_provider.
    Returns:
        An instance of a class that inherits from BaseLLMClient.
    """
    provider = settings.llm_provider.strip().lower()

    if provider == "openai":
        from app.llm.openai_client import OpenAIClient
        return OpenAIClient()
    
    elif provider == "gemini":
        from app.llm.gemini_client import GeminiClient
        return GeminiClient()
    
    elif provider == "anthropic":
        from app.llm.anthropic_client import AnthropicClient
        return AnthropicClient()
    
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
