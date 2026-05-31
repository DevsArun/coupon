"""API v1 router combining all endpoint routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, search, coupons, merchants, billing, admin, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(coupons.router, prefix="/coupons", tags=["Coupons"])
api_router.include_router(merchants.router, prefix="/merchants", tags=["Merchants"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
