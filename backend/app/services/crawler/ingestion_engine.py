"""Multi-source coupon ingestion engine."""
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.ai import ai_engine
from app.services.validation import scoring_engine

logger = logging.getLogger(__name__)


class IngestionEngine:
    """Multi-source coupon discovery and ingestion pipeline."""

    def __init__(self):
        self.user_agent = settings.CRAWLER_USER_AGENT
        self.timeout = settings.CRAWLER_TIMEOUT

    async def crawl_source(self, source_url: str, source_type: str, merchant_name: str) -> List[Dict[str, Any]]:
        """Crawl a single source and extract coupons."""
        try:
            content = await self._fetch_content(source_url)
            if not content:
                return []

            # Clean content
            cleaned = self._clean_content(content)

            # Extract coupons using AI
            raw_coupons = await ai_engine.extract_coupons(cleaned, merchant_name)

            # Process and score each coupon
            processed = []
            for coupon in raw_coupons:
                coupon["source_url"] = source_url
                coupon["source_type"] = source_type
                coupon["merchant_name"] = merchant_name
                coupon["crawled_at"] = datetime.now(timezone.utc).isoformat()

                # Calculate fingerprint for deduplication
                coupon["fingerprint"] = self._generate_fingerprint(coupon)

                # Score
                scores = scoring_engine.calculate_confidence(coupon)
                coupon.update(scores)

                if scoring_engine.should_index(scores):
                    processed.append(coupon)

            logger.info(f"Extracted {len(processed)} coupons from {source_url}")
            return processed

        except Exception as e:
            logger.error(f"Error crawling {source_url}: {e}")
            return []

    async def _fetch_content(self, url: str) -> Optional[str]:
        """Fetch page content."""
        headers = {"User-Agent": self.user_agent}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _clean_content(self, html: str) -> str:
        """Clean HTML content, extract relevant text."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Limit content size
        return text[:5000]

    def _generate_fingerprint(self, coupon: Dict[str, Any]) -> str:
        """Generate unique fingerprint for deduplication."""
        components = [
            coupon.get("title", ""),
            coupon.get("code", ""),
            coupon.get("merchant_name", ""),
            str(coupon.get("discount_value", "")),
        ]
        raw = "|".join(components).lower().strip()
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def deduplicate(self, coupons: List[Dict[str, Any]], existing_fingerprints: set) -> List[Dict[str, Any]]:
        """Remove duplicate coupons."""
        unique = []
        seen = set(existing_fingerprints)

        for coupon in coupons:
            fp = coupon.get("fingerprint", "")
            if fp and fp not in seen:
                seen.add(fp)
                unique.append(coupon)

        logger.info(f"Deduplication: {len(coupons)} -> {len(unique)} coupons")
        return unique

    async def process_user_submission(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Process a user-submitted coupon."""
        submission["source_type"] = "user_submitted"
        submission["crawled_at"] = datetime.now(timezone.utc).isoformat()
        submission["fingerprint"] = self._generate_fingerprint(submission)

        # Validate with AI
        validation = await ai_engine.validate_coupon(submission)
        submission["ai_confidence"] = validation.get("confidence", 0.5)
        submission["ai_extracted"] = False

        # Score
        scores = scoring_engine.calculate_confidence(submission)
        submission.update(scores)

        return submission


ingestion_engine = IngestionEngine()
