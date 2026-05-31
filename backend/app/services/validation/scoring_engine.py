"""Coupon confidence scoring engine."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Multi-factor coupon confidence scoring."""

    # Weight configuration
    WEIGHTS = {
        "source_trust": 0.20,
        "freshness": 0.25,
        "success_rate": 0.25,
        "duplicate": 0.15,
        "expiry": 0.15,
    }

    # Source trust base scores
    SOURCE_TRUST_SCORES = {
        "official_page": 0.95,
        "promotion_page": 0.85,
        "rss_feed": 0.80,
        "sitemap": 0.75,
        "deal_page": 0.60,
        "email": 0.70,
        "user_submitted": 0.40,
    }

    def calculate_confidence(self, coupon_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate all confidence scores for a coupon."""
        source_trust = self._source_trust_score(coupon_data)
        freshness = self._freshness_score(coupon_data)
        success = self._success_score(coupon_data)
        duplicate = self._duplicate_score(coupon_data)
        expiry = self._expiry_confidence(coupon_data)

        # Weighted final score
        final = (
            source_trust * self.WEIGHTS["source_trust"]
            + freshness * self.WEIGHTS["freshness"]
            + success * self.WEIGHTS["success_rate"]
            + duplicate * self.WEIGHTS["duplicate"]
            + expiry * self.WEIGHTS["expiry"]
        )

        return {
            "source_trust_score": round(source_trust, 3),
            "freshness_score": round(freshness, 3),
            "success_score": round(success, 3),
            "duplicate_score": round(duplicate, 3),
            "expiry_confidence": round(expiry, 3),
            "final_confidence": round(final, 3),
        }

    def _source_trust_score(self, data: Dict[str, Any]) -> float:
        """Calculate source trust score."""
        source_type = data.get("source_type", "user_submitted")
        base_score = self.SOURCE_TRUST_SCORES.get(source_type, 0.5)

        # Adjust based on merchant trust
        merchant_trust = data.get("merchant_trust_score", 0.5)
        return (base_score * 0.7) + (merchant_trust * 0.3)

    def _freshness_score(self, data: Dict[str, Any]) -> float:
        """Calculate freshness score based on age."""
        crawled_at = data.get("crawled_at")
        if not crawled_at:
            return 0.5

        if isinstance(crawled_at, str):
            crawled_at = datetime.fromisoformat(crawled_at.replace("Z", "+00:00"))

        now = datetime.now(timezone.utc)
        age_hours = (now - crawled_at).total_seconds() / 3600

        if age_hours < 1:
            return 1.0
        elif age_hours < 6:
            return 0.95
        elif age_hours < 24:
            return 0.85
        elif age_hours < 72:
            return 0.70
        elif age_hours < 168:  # 1 week
            return 0.55
        elif age_hours < 720:  # 30 days
            return 0.35
        else:
            return 0.15

    def _success_score(self, data: Dict[str, Any]) -> float:
        """Calculate success score based on usage feedback."""
        total_uses = data.get("total_uses", 0)
        success_count = data.get("success_count", 0)
        fail_count = data.get("fail_count", 0)

        if total_uses == 0:
            return 0.5  # No data, neutral score

        success_rate = success_count / max(total_uses, 1)

        # Apply Bayesian smoothing (prior: 50% success rate with 5 virtual observations)
        alpha = success_count + 2.5
        beta = fail_count + 2.5
        smoothed = alpha / (alpha + beta)

        return smoothed

    def _duplicate_score(self, data: Dict[str, Any]) -> float:
        """Calculate duplicate confidence (1.0 = unique, lower = likely duplicate)."""
        is_duplicate = data.get("is_duplicate", False)
        duplicate_count = data.get("duplicate_count", 0)

        if is_duplicate:
            return 0.3
        if duplicate_count > 5:
            return 0.5
        if duplicate_count > 2:
            return 0.7
        return 1.0

    def _expiry_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate confidence that the coupon is still valid."""
        expires_at = data.get("expires_at")
        if not expires_at:
            return 0.5  # Unknown expiry

        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError:
                return 0.5

        now = datetime.now(timezone.utc)

        if expires_at < now:
            return 0.1  # Expired

        hours_until_expiry = (expires_at - now).total_seconds() / 3600

        if hours_until_expiry > 720:  # 30+ days
            return 0.95
        elif hours_until_expiry > 168:  # 7+ days
            return 0.90
        elif hours_until_expiry > 48:
            return 0.80
        elif hours_until_expiry > 24:
            return 0.70
        elif hours_until_expiry > 6:
            return 0.60
        else:
            return 0.50  # Expiring soon

    def should_index(self, scores: Dict[str, float]) -> bool:
        """Determine if a coupon should be indexed for search."""
        return scores.get("final_confidence", 0) > 0.2

    def get_rank_tier(self, final_confidence: float) -> str:
        """Get ranking tier for display."""
        if final_confidence >= 0.8:
            return "excellent"
        elif final_confidence >= 0.6:
            return "good"
        elif final_confidence >= 0.4:
            return "fair"
        elif final_confidence >= 0.2:
            return "low"
        else:
            return "poor"


scoring_engine = ScoringEngine()
