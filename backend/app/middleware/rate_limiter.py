"""Rate limiting middleware."""
import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis import cache


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting per IP address."""

    async def dispatch(self, request: Request, call_next):
        # Skip health check
        if request.url.path in ("/health", "/api/v1/search/quick"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}:{int(time.time() // 60)}"

        try:
            count = await cache.increment(key, ttl=60)
            if count > 120:  # 120 requests per minute per IP
                raise HTTPException(status_code=429, detail="Too many requests")
        except (RuntimeError, Exception):
            pass  # Redis not available, skip rate limiting

        response = await call_next(request)
        return response
