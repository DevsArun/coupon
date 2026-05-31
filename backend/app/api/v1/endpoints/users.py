"""User endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.user import User
from app.models.search import SearchLog
from app.models.coupon import CouponFeedback
from app.schemas.auth import UserResponse

router = APIRouter()


@router.put("/profile")
async def update_profile(
    full_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile."""
    user_id = int(current_user["sub"])
    updates = {}
    if full_name is not None:
        updates["full_name"] = full_name
    if avatar_url is not None:
        updates["avatar_url"] = avatar_url

    if updates:
        await db.execute(update(User).where(User.id == user_id).values(**updates))

    return {"message": "Profile updated"}


@router.put("/password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password."""
    from app.core.security import verify_password
    user_id = int(current_user["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    user.password_hash = hash_password(new_password)
    return {"message": "Password changed"}


@router.get("/search-history")
async def get_search_history(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's search history."""
    user_id = int(current_user["sub"])
    result = await db.execute(
        select(SearchLog)
        .where(SearchLog.user_id == user_id)
        .order_by(SearchLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "query": log.query,
            "results_count": log.results_count,
            "merchant_detected": log.merchant_detected,
            "created_at": log.created_at.isoformat() if log.created_at else "",
        }
        for log in logs
    ]


@router.get("/saved-coupons")
async def get_saved_coupons(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's saved coupons."""
    user_id = int(current_user["sub"])
    result = await db.execute(
        select(CouponFeedback)
        .where(CouponFeedback.user_id == user_id, CouponFeedback.feedback_type == "saved")
        .order_by(CouponFeedback.created_at.desc())
    )
    saved = result.scalars().all()
    return [
        {
            "id": s.id,
            "coupon_id": s.coupon_id,
            "saved_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in saved
    ]
