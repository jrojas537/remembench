from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    """
    Abstract base class for LLM providers.
    Ensures a consistent interface for classifying events regardless of the backend.
    """

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """
        Generate a text completion given a system prompt and a user prompt.
        
        Args:
            system: The system instruction guiding the model's behavior.
            user: The input text to process.
            
        Returns:
            The model's text response.
        """
        pass
