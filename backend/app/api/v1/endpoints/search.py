"""Search endpoints - the core of the platform."""
import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.redis import cache
from app.services.ai import ai_engine
from app.services.search import search_service
from app.services.billing import billing_service
from app.schemas.search import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search_coupons(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-powered coupon search with natural language understanding."""
    start_time = time.time()
    user_id = int(current_user["sub"])

    # Check search quota
    quota = await billing_service.check_search_quota(db, user_id)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Search limit reached: {quota['reason']}. Upgrade your plan for more searches."
        )

    # Try cache first
    cache_key = f"search:{request.query}:{request.merchant}:{request.sort_by}:{request.limit}:{request.offset}"
    cached = await cache.get(cache_key)
    if cached:
        # Still count the search
        await billing_service.record_search_usage(db, user_id)
        cached["quota_remaining"] = quota.get("remaining")
        return SearchResponse(**cached)

    # AI analysis of query
    ai_analysis = await ai_engine.analyze_query(request.query)
    search_query = ai_analysis.get("corrected_query", request.query)
    merchant_detected = ai_analysis.get("merchant")

    # Build Meilisearch filters
    filters = []
    if request.merchant:
        filters.append(f'merchant_name = "{request.merchant}"')
    elif merchant_detected:
        filters.append(f'merchant_name = "{merchant_detected}"')

    if request.coupon_type:
        filters.append(f'coupon_type = "{request.coupon_type}"')

    filters.append('status = "active"')
    filter_str = " AND ".join(filters) if filters else None

    # Build sort
    sort = None
    if request.sort_by == "discount":
        sort = ["discount_value:desc"]
    elif request.sort_by == "expiry":
        sort = ["expires_at_ts:asc"]
    elif request.sort_by == "confidence":
        sort = ["final_confidence:desc"]
    elif request.sort_by == "newest":
        sort = ["created_at_ts:desc"]

    # Execute search
    results = await search_service.search(
        query=search_query,
        filters=filter_str,
        sort=sort,
        limit=request.limit,
        offset=request.offset,
    )

    # Record usage
    await billing_service.record_search_usage(db, user_id)

    elapsed_ms = int((time.time() - start_time) * 1000)

    response_data = {
        "query": request.query,
        "corrected_query": search_query if search_query != request.query else None,
        "merchant_detected": merchant_detected,
        "total_hits": results.get("estimatedTotalHits", 0),
        "response_time_ms": elapsed_ms,
        "results": results.get("hits", []),
        "ai_analysis": ai_analysis,
        "quota_remaining": quota.get("remaining"),
    }

    # Cache results for 60 seconds
    await cache.set(cache_key, response_data, ttl=60)

    return SearchResponse(**response_data)


@router.get("/quick")
async def quick_search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=20),
):
    """Quick search for autocomplete - no auth required, limited results."""
    results = await search_service.search(
        query=q,
        filters='status = "active"',
        limit=limit,
        attributes_to_retrieve=["id", "title", "code", "merchant_name", "discount_value", "discount_unit"],
    )
    return {
        "query": q,
        "hits": results.get("hits", []),
        "total": results.get("estimatedTotalHits", 0),
    }


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=1, max_length=100),
):
    """Get search suggestions/autocomplete."""
    results = await search_service.search(
        query=q,
        limit=5,
        attributes_to_retrieve=["title", "merchant_name"],
    )
    suggestions = []
    for hit in results.get("hits", []):
        suggestions.append(hit.get("title", ""))
    return {"suggestions": suggestions[:5]}
