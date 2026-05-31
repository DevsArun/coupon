"""Google Gemini AI Provider."""
import httpx
from typing import Optional

from app.core.config import settings
from app.services.ai.providers.base import BaseAIProvider


class GeminiProvider(BaseAIProvider):
    """Google Gemini API provider."""

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or settings.GEMINI_MODEL)

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def complete(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
        """Send completion request to Gemini API."""
        url = f"{self.API_URL}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"You are a helpful assistant that analyzes coupon search queries. Always respond with valid JSON only.\n\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }

        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
