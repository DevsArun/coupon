"""Meilisearch integration service."""
import logging
import time
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MeiliSearchService:
    """Service for managing Meilisearch operations."""

    def __init__(self):
        self.host = settings.MEILI_HOST
        self.api_key = settings.MEILI_MASTER_KEY
        self.index_name = settings.MEILI_INDEX_COUPONS
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, json: Any = None) -> Any:
        """Make HTTP request to Meilisearch."""
        url = f"{self.host}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, url, headers=self.headers, json=json)
            if response.status_code in (200, 201, 202):
                return response.json()
            elif response.status_code == 204:
                return None
            else:
                logger.error(f"Meilisearch error: {response.status_code} - {response.text}")
                return None

    async def initialize_index(self):
        """Create and configure the coupons index."""
        # Create index
        await self._request("POST", "/indexes", {
            "uid": self.index_name,
            "primaryKey": "id",
        })

        # Configure searchable attributes
        await self._request("PUT", f"/indexes/{self.index_name}/settings/searchable-attributes", [
            "title",
            "description",
            "code",
            "merchant_name",
            "merchant_aliases",
            "tags",
            "category",
        ])

        # Configure filterable attributes
        await self._request("PUT", f"/indexes/{self.index_name}/settings/filterable-attributes", [
            "merchant_id",
            "merchant_name",
            "coupon_type",
            "status",
            "is_verified",
            "is_featured",
            "is_exclusive",
            "category",
            "discount_value",
            "expires_at_ts",
        ])

        # Configure sortable attributes
        await self._request("PUT", f"/indexes/{self.index_name}/settings/sortable-attributes", [
            "final_confidence",
            "discount_value",
            "expires_at_ts",
            "created_at_ts",
            "views",
            "success_score",
        ])

        # Configure ranking rules
        await self._request("PUT", f"/indexes/{self.index_name}/settings/ranking-rules", [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
            "final_confidence:desc",
            "success_score:desc",
        ])

        # Configure typo tolerance
        await self._request("PATCH", f"/indexes/{self.index_name}/settings/typo-tolerance", {
            "enabled": True,
            "minWordSizeForTypos": {
                "oneTypo": 3,
                "twoTypos": 6,
            }
        })

        # Configure synonyms
        await self._request("PUT", f"/indexes/{self.index_name}/settings/synonyms", {
            "coupon": ["code", "promo", "voucher", "discount code"],
            "deal": ["offer", "promotion", "sale", "bargain"],
            "discount": ["off", "save", "savings", "reduction"],
            "cashback": ["cash back", "money back", "rebate"],
            "free shipping": ["no shipping cost", "delivery free"],
            "bogo": ["buy one get one", "buy 1 get 1"],
            "vpn": ["virtual private network"],
            "hosting": ["web hosting", "server hosting"],
        })

        # Configure stop words
        await self._request("PUT", f"/indexes/{self.index_name}/settings/stop-words", [
            "the", "a", "an", "and", "or", "but", "for", "with",
            "best", "top", "good", "great", "latest",
        ])

        logger.info("Meilisearch index configured successfully")

    async def index_coupon(self, coupon_data: Dict[str, Any]):
        """Index a single coupon document."""
        await self._request("POST", f"/indexes/{self.index_name}/documents", [coupon_data])

    async def index_coupons_batch(self, coupons: List[Dict[str, Any]]):
        """Batch index multiple coupons."""
        if not coupons:
            return
        await self._request("POST", f"/indexes/{self.index_name}/documents", coupons)
        logger.info(f"Indexed {len(coupons)} coupons to Meilisearch")

    async def delete_coupon(self, coupon_id: int):
        """Remove a coupon from the index."""
        await self._request("DELETE", f"/indexes/{self.index_name}/documents/{coupon_id}")

    async def search(
        self,
        query: str,
        filters: Optional[str] = None,
        sort: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        attributes_to_retrieve: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute search query against Meilisearch."""
        start = time.time()

        payload: Dict[str, Any] = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "showMatchesPosition": True,
            "attributesToHighlight": ["title", "description", "merchant_name"],
        }

        if filters:
            payload["filter"] = filters
        if sort:
            payload["sort"] = sort
        if attributes_to_retrieve:
            payload["attributesToRetrieve"] = attributes_to_retrieve

        result = await self._request("POST", f"/indexes/{self.index_name}/search", payload)

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(f"Search '{query}' returned {result.get('estimatedTotalHits', 0)} hits in {elapsed_ms}ms")

        if result:
            result["response_time_ms"] = elapsed_ms
        return result or {"hits": [], "estimatedTotalHits": 0, "response_time_ms": elapsed_ms}

    async def update_coupon(self, coupon_data: Dict[str, Any]):
        """Update an existing coupon in the index."""
        await self._request("PUT", f"/indexes/{self.index_name}/documents", [coupon_data])

    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return await self._request("GET", f"/indexes/{self.index_name}/stats") or {}

    async def clear_index(self):
        """Delete all documents from the index."""
        await self._request("DELETE", f"/indexes/{self.index_name}/documents")

    async def health_check(self) -> bool:
        """Check if Meilisearch is healthy."""
        try:
            result = await self._request("GET", "/health")
            return result.get("status") == "available" if result else False
        except Exception:
            return False


# Global search service instance
search_service = MeiliSearchService()
