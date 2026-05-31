"""Search service with Meilisearch integration."""
from app.services.search.meilisearch_service import MeiliSearchService, search_service

__all__ = ["MeiliSearchService", "search_service"]
