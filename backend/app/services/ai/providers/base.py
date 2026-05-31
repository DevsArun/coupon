"""Base AI Provider interface."""
from abc import ABC, abstractmethod
from typing import Optional


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def complete(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
        """Send completion request and return response text."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass
