"""Groq AI Provider."""
import httpx
from typing import Optional

from app.core.config import settings
from app.services.ai.providers.base import BaseAIProvider


class GroqProvider(BaseAIProvider):
    """Groq API provider using LLaMA models."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or settings.GROQ_MODEL)

    @property
    def provider_name(self) -> str:
        return "groq"

    async def complete(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
        """Send completion request to Groq API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that analyzes coupon search queries. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT) as client:
            response = await client.post(self.API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
