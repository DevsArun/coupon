"""Admin endpoints - Mission Control Center API."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, RoleType
from app.models.coupon import Coupon, CouponStatus
from app.models.merchant import Merchant, MerchantSource
from app.models.billing import Plan, Subscription
from app.models.system import (
    AuditLog, FeatureFlag, AIProviderConfig,
    CrawlerJob, CrawlerJobStatus
)
from app.models.search import SearchAnalytics
from app.services.billing import billing_service
from app.services.search import search_service

router = APIRouter()



def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin or super_admin role."""
    role = current_user.get("role", "")
    if role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/dashboard")
async def admin_dashboard(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get admin dashboard stats."""
    total_users = await db.scalar(select(func.count(User.id)))
    total_coupons = await db.scalar(select(func.count(Coupon.id)))
    active_coupons = await db.scalar(
        select(func.count(Coupon.id)).where(Coupon.status == CouponStatus.ACTIVE)
    )
    total_merchants = await db.scalar(select(func.count(Merchant.id)))
    total_searches = await db.scalar(
        select(func.count()).select_from(SearchAnalytics)
    ) or 0

    return {
        "total_users": total_users or 0,
        "total_coupons": total_coupons or 0,
        "active_coupons": active_coupons or 0,
        "total_merchants": total_merchants or 0,
        "total_searches": total_searches,
    }



# --- User Management ---
@router.get("/users")
async def admin_list_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with filters."""
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    users = result.scalars().all()
    return [
        {
            "id": u.id, "email": u.email, "username": u.username,
            "role": u.role.value if u.role else "user",
            "is_active": u.is_active, "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
        for u in users
    ]


@router.put("/users/{user_id}/role")
async def admin_update_role(
    user_id: int, role: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user role."""
    await db.execute(update(User).where(User.id == user_id).values(role=role))
    return {"message": f"User role updated to {role}"}


@router.put("/users/{user_id}/status")
async def admin_toggle_user(
    user_id: int, is_active: bool,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate a user."""
    await db.execute(update(User).where(User.id == user_id).values(is_active=is_active))
    return {"message": f"User {'activated' if is_active else 'deactivated'}"}



# --- Plan Management ---
@router.post("/plans")
async def admin_create_plan(
    name: str, slug: str, price: float, interval: str,
    searches_per_day: Optional[int] = None,
    searches_per_month: Optional[int] = None,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new plan."""
    plan = await billing_service.create_plan(db, {
        "name": name, "slug": slug, "price": price,
        "interval": interval,
        "searches_per_day": searches_per_day,
        "searches_per_month": searches_per_month,
    })
    return {"message": "Plan created", "plan_id": plan.id}


@router.put("/plans/{plan_id}")
async def admin_update_plan(
    plan_id: int, name: Optional[str] = None,
    price: Optional[float] = None,
    searches_per_day: Optional[int] = None,
    searches_per_month: Optional[int] = None,
    status: Optional[str] = None,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing plan."""
    updates = {}
    if name: updates["name"] = name
    if price is not None: updates["price"] = price
    if searches_per_day is not None: updates["searches_per_day"] = searches_per_day
    if searches_per_month is not None: updates["searches_per_month"] = searches_per_month
    if status: updates["status"] = status
    await billing_service.update_plan(db, plan_id, updates)
    return {"message": "Plan updated"}


@router.delete("/plans/{plan_id}")
async def admin_delete_plan(
    plan_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a plan."""
    await db.execute(delete(Plan).where(Plan.id == plan_id))
    return {"message": "Plan deleted"}


@router.post("/users/{user_id}/assign-plan")
async def admin_assign_plan(
    user_id: int, plan_id: int, is_lifetime: bool = False,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Assign a plan to a user (including lifetime)."""
    await billing_service.assign_custom_plan(db, user_id, plan_id, is_lifetime)
    return {"message": "Plan assigned"}



# --- Coupon Management ---
@router.get("/coupons")
async def admin_list_coupons(
    status: Optional[str] = None,
    merchant_id: Optional[int] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all coupons with admin filters."""
    query = select(Coupon).order_by(Coupon.created_at.desc())
    if status:
        query = query.where(Coupon.status == status)
    if merchant_id:
        query = query.where(Coupon.merchant_id == merchant_id)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    coupons = result.scalars().all()
    return [
        {
            "id": c.id, "title": c.title, "code": c.code,
            "merchant_id": c.merchant_id,
            "status": c.status.value if c.status else "active",
            "final_confidence": c.final_confidence,
            "is_verified": c.is_verified,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in coupons
    ]


@router.put("/coupons/{coupon_id}/verify")
async def admin_verify_coupon(
    coupon_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Verify a coupon."""
    await db.execute(
        update(Coupon).where(Coupon.id == coupon_id).values(is_verified=True)
    )
    return {"message": "Coupon verified"}


@router.put("/coupons/{coupon_id}/status")
async def admin_update_coupon_status(
    coupon_id: int, status: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update coupon status."""
    await db.execute(
        update(Coupon).where(Coupon.id == coupon_id).values(status=status)
    )
    return {"message": f"Coupon status updated to {status}"}


# --- Merchant Management ---
@router.get("/merchants")
async def admin_list_merchants(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all merchants."""
    result = await db.execute(
        select(Merchant).order_by(Merchant.created_at.desc()).limit(limit).offset(offset)
    )
    merchants = result.scalars().all()
    return [
        {
            "id": m.id, "name": m.name, "slug": m.slug,
            "status": m.status.value if m.status else "active",
            "total_coupons": m.total_coupons,
            "active_coupons": m.active_coupons,
            "trust_score": m.trust_score,
        }
        for m in merchants
    ]



# --- AI Provider Management ---
@router.get("/ai-providers")
async def admin_list_ai_providers(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List AI provider configs."""
    result = await db.execute(
        select(AIProviderConfig).order_by(AIProviderConfig.priority)
    )
    providers = result.scalars().all()
    return [
        {
            "id": p.id, "provider_name": p.provider_name,
            "is_enabled": p.is_enabled, "priority": p.priority,
            "model_name": p.model_name,
            "total_requests": p.total_requests,
            "failed_requests": p.failed_requests,
            "avg_response_time_ms": p.avg_response_time_ms,
        }
        for p in providers
    ]


@router.put("/ai-providers/{provider_id}")
async def admin_update_ai_provider(
    provider_id: int,
    is_enabled: Optional[bool] = None,
    priority: Optional[int] = None,
    model_name: Optional[str] = None,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update AI provider config."""
    updates = {}
    if is_enabled is not None: updates["is_enabled"] = is_enabled
    if priority is not None: updates["priority"] = priority
    if model_name: updates["model_name"] = model_name
    if updates:
        await db.execute(
            update(AIProviderConfig).where(AIProviderConfig.id == provider_id).values(**updates)
        )
    return {"message": "AI provider updated"}


# --- Feature Flags ---
@router.get("/feature-flags")
async def admin_list_flags(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all feature flags."""
    result = await db.execute(select(FeatureFlag))
    flags = result.scalars().all()
    return [
        {"id": f.id, "name": f.name, "is_enabled": f.is_enabled, "description": f.description}
        for f in flags
    ]


@router.put("/feature-flags/{flag_id}")
async def admin_toggle_flag(
    flag_id: int, is_enabled: bool,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle a feature flag."""
    await db.execute(
        update(FeatureFlag).where(FeatureFlag.id == flag_id).values(is_enabled=is_enabled)
    )
    return {"message": f"Flag {'enabled' if is_enabled else 'disabled'}"}


# --- Search Reindexing ---
@router.post("/reindex")
async def admin_reindex(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger full search reindex."""
    await search_service.initialize_index()
    return {"message": "Reindex initiated"}


# --- Audit Logs ---
@router.get("/audit-logs")
async def admin_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get recent audit logs."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id, "user_id": l.user_id, "action": l.action,
            "resource_type": l.resource_type, "resource_id": l.resource_id,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }
        for l in logs
    ]
