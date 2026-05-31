"""AI Engine with provider fallback chain."""
import json
import time
import logging
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.services.ai.providers.groq_provider import GroqProvider
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.base import BaseAIProvider

logger = logging.getLogger(__name__)


class AIEngine:
    """AI Engine with multi-provider fallback support."""

    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}
        self.priority_chain: List[str] = []
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize AI providers based on configuration."""
        provider_map = {
            "groq": (GroqProvider, settings.GROQ_API_KEY),
            "gemini": (GeminiProvider, settings.GEMINI_API_KEY),
            "openai": (OpenAIProvider, settings.OPENAI_API_KEY),
        }

        priority_list = settings.AI_PROVIDER_PRIORITY.split(",")

        for provider_name in priority_list:
            provider_name = provider_name.strip()
            if provider_name in provider_map:
                cls, api_key = provider_map[provider_name]
                if api_key:
                    self.providers[provider_name] = cls(api_key)
                    self.priority_chain.append(provider_name)
                    logger.info(f"AI Provider initialized: {provider_name}")

        if not self.priority_chain:
            logger.warning("No AI providers configured. Using rule-based fallback.")

    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze a search query using AI to extract intent."""
        prompt = self._build_query_analysis_prompt(query)

        for provider_name in self.priority_chain:
            provider = self.providers[provider_name]
            try:
                start = time.time()
                result = await provider.complete(prompt)
                elapsed = (time.time() - start) * 1000
                logger.info(f"AI analysis via {provider_name} in {elapsed:.0f}ms")
                return self._parse_analysis(result, query)
            except Exception as e:
                logger.warning(f"AI provider {provider_name} failed: {e}")
                continue

        # Fallback to rule-based analysis
        return self._rule_based_analysis(query)

    async def extract_coupons(self, content: str, merchant: str) -> List[Dict[str, Any]]:
        """Extract structured coupon data from raw content using AI."""
        prompt = self._build_extraction_prompt(content, merchant)

        for provider_name in self.priority_chain:
            provider = self.providers[provider_name]
            try:
                result = await provider.complete(prompt)
                return self._parse_extraction(result)
            except Exception as e:
                logger.warning(f"Extraction via {provider_name} failed: {e}")
                continue

        return []

    async def validate_coupon(self, coupon_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate coupon data using AI."""
        prompt = self._build_validation_prompt(coupon_data)

        for provider_name in self.priority_chain:
            provider = self.providers[provider_name]
            try:
                result = await provider.complete(prompt)
                return self._parse_validation(result)
            except Exception as e:
                logger.warning(f"Validation via {provider_name} failed: {e}")
                continue

        return {"is_valid": True, "confidence": 0.5, "reason": "AI validation unavailable"}

    def _build_query_analysis_prompt(self, query: str) -> str:
        return f"""Analyze this coupon search query and extract structured intent. Return ONLY valid JSON.

Query: "{query}"

Return JSON with these fields:
{{
    "corrected_query": "spell-corrected version of query",
    "merchant": "detected merchant name or null",
    "intent": "coupon|deal|discount|cashback|free_shipping|general",
    "time_context": "today|this_week|this_month|specific_date|none",
    "discount_type": "percentage|flat|any",
    "category": "detected category or null",
    "keywords": ["relevant", "search", "keywords"],
    "confidence": 0.0 to 1.0
}}"""

    def _build_extraction_prompt(self, content: str, merchant: str) -> str:
        return f"""Extract coupon/deal information from this content for merchant: {merchant}

Content:
{content[:3000]}

Return ONLY a JSON array of coupons:
[{{
    "title": "coupon title",
    "code": "COUPON_CODE or null",
    "discount_value": number or null,
    "discount_unit": "percent|usd|flat",
    "description": "brief description",
    "expires_at": "YYYY-MM-DD or null",
    "terms": "any terms/conditions",
    "coupon_type": "code|deal|cashback|free_shipping|percentage|flat"
}}]"""

    def _build_validation_prompt(self, coupon_data: Dict[str, Any]) -> str:
        return f"""Validate this coupon data for accuracy and plausibility:

{json.dumps(coupon_data, indent=2)}

Return JSON:
{{
    "is_valid": true/false,
    "confidence": 0.0 to 1.0,
    "reason": "explanation",
    "issues": ["list of issues found"]
}}"""

    def _parse_analysis(self, raw: str, original_query: str) -> Dict[str, Any]:
        """Parse AI analysis response."""
        try:
            # Clean response
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            result = json.loads(raw.strip())
            result.setdefault("corrected_query", original_query)
            result.setdefault("confidence", 0.5)
            return result
        except (json.JSONDecodeError, Exception):
            return self._rule_based_analysis(original_query)

    def _parse_extraction(self, raw: str) -> List[Dict[str, Any]]:
        """Parse AI extraction response."""
        try:
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            result = json.loads(raw.strip())
            if isinstance(result, list):
                return result
            return []
        except (json.JSONDecodeError, Exception):
            return []

    def _parse_validation(self, raw: str) -> Dict[str, Any]:
        """Parse AI validation response."""
        try:
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            return json.loads(raw.strip())
        except (json.JSONDecodeError, Exception):
            return {"is_valid": True, "confidence": 0.5, "reason": "Parse error"}

    def _rule_based_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback rule-based query analysis."""
        query_lower = query.lower().strip()

        # Common merchant detection
        merchants = {
            "amazon": "Amazon", "nike": "Nike", "adidas": "Adidas",
            "walmart": "Walmart", "target": "Target", "ebay": "eBay",
            "bestbuy": "Best Buy", "best buy": "Best Buy",
            "hostinger": "Hostinger", "namecheap": "Namecheap",
            "nordvpn": "NordVPN", "expressvpn": "ExpressVPN",
            "surfshark": "Surfshark", "netflix": "Netflix",
            "spotify": "Spotify", "uber": "Uber",
            "doordash": "DoorDash", "grubhub": "Grubhub",
        }

        detected_merchant = None
        for key, name in merchants.items():
            if key in query_lower:
                detected_merchant = name
                break

        # Time context
        time_context = "none"
        time_words = {
            "today": "today", "this week": "this_week",
            "this month": "this_month", "february": "this_month",
            "january": "this_month", "march": "this_month",
        }
        for key, val in time_words.items():
            if key in query_lower:
                time_context = val
                break

        # Intent detection
        intent = "general"
        if any(w in query_lower for w in ["coupon", "code", "promo"]):
            intent = "coupon"
        elif any(w in query_lower for w in ["deal", "offer"]):
            intent = "deal"
        elif any(w in query_lower for w in ["discount", "off", "save"]):
            intent = "discount"
        elif "cashback" in query_lower:
            intent = "cashback"
        elif "free shipping" in query_lower:
            intent = "free_shipping"

        return {
            "corrected_query": query,
            "merchant": detected_merchant,
            "intent": intent,
            "time_context": time_context,
            "discount_type": "any",
            "category": None,
            "keywords": query_lower.split(),
            "confidence": 0.3,
        }


# Global AI engine instance
ai_engine = AIEngine()
