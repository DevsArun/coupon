"""Search schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    merchant: Optional[str] = None
    coupon_type: Optional[str] = None
    sort_by: Optional[str] = None  # relevance, discount, expiry, confidence
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class SearchResponse(BaseModel):
    query: str
    corrected_query: Optional[str] = None
    merchant_detected: Optional[str] = None
    total_hits: int
    response_time_ms: int
    results: list
    ai_analysis: Optional[dict] = None
    quota_remaining: Optional[int] = None
