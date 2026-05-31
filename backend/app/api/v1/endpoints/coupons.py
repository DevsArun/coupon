"""Coupon management endpoints."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.coupon import Coupon, CouponFeedback, FeedbackType, CouponStatus
from app.models.merchant import Merchant
from app.schemas.coupon import CouponCreate, CouponUpdate, CouponResponse

router = APIRouter()


@router.get("", response_model=List[CouponResponse])
async def list_coupons(
    merchant_id: Optional[int] = None,
    status: Optional[str] = None,
    coupon_type: Optional[str] = None,
    is_verified: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List coupons with filters."""
    query = select(Coupon).order_by(Coupon.final_confidence.desc(), Coupon.created_at.desc())

    if merchant_id:
        query = query.where(Coupon.merchant_id == merchant_id)
    if status:
        query = query.where(Coupon.status == status)
    if coupon_type:
        query = query.where(Coupon.coupon_type == coupon_type)
    if is_verified is not None:
        query = query.where(Coupon.is_verified == is_verified)
    if is_featured is not None:
        query = query.where(Coupon.is_featured == is_featured)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    coupons = result.scalars().all()

    responses = []
    for coupon in coupons:
        # Get merchant name
        merchant_result = await db.execute(select(Merchant.name).where(Merchant.id == coupon.merchant_id))
        merchant_name = merchant_result.scalar_one_or_none()

        responses.append(CouponResponse(
            id=coupon.id,
            merchant_id=coupon.merchant_id,
            merchant_name=merchant_name,
            title=coupon.title,
            description=coupon.description,
            code=coupon.code,
            coupon_type=coupon.coupon_type.value if coupon.coupon_type else "deal",
            status=coupon.status.value if coupon.status else "active",
            discount_value=coupon.discount_value,
            discount_unit=coupon.discount_unit,
            minimum_purchase=coupon.minimum_purchase,
            maximum_discount=coupon.maximum_discount,
            url=coupon.url,
            terms=coupon.terms,
            is_verified=coupon.is_verified,
            is_exclusive=coupon.is_exclusive,
            is_featured=coupon.is_featured,
            final_confidence=coupon.final_confidence,
            total_uses=coupon.total_uses,
            success_count=coupon.success_count,
            views=coupon.views,
            starts_at=coupon.starts_at.isoformat() if coupon.starts_at else None,
            expires_at=coupon.expires_at.isoformat() if coupon.expires_at else None,
            created_at=coupon.created_at.isoformat() if coupon.created_at else "",
        ))

    return responses


@router.get("/{coupon_id}", response_model=CouponResponse)
async def get_coupon(coupon_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single coupon by ID."""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    # Increment views
    coupon.views += 1

    merchant_result = await db.execute(select(Merchant.name).where(Merchant.id == coupon.merchant_id))
    merchant_name = merchant_result.scalar_one_or_none()

    return CouponResponse(
        id=coupon.id,
        merchant_id=coupon.merchant_id,
        merchant_name=merchant_name,
        title=coupon.title,
        description=coupon.description,
        code=coupon.code,
        coupon_type=coupon.coupon_type.value if coupon.coupon_type else "deal",
        status=coupon.status.value if coupon.status else "active",
        discount_value=coupon.discount_value,
        discount_unit=coupon.discount_unit,
        minimum_purchase=coupon.minimum_purchase,
        maximum_discount=coupon.maximum_discount,
        url=coupon.url,
        terms=coupon.terms,
        is_verified=coupon.is_verified,
        is_exclusive=coupon.is_exclusive,
        is_featured=coupon.is_featured,
        final_confidence=coupon.final_confidence,
        total_uses=coupon.total_uses,
        success_count=coupon.success_count,
        views=coupon.views,
        starts_at=coupon.starts_at.isoformat() if coupon.starts_at else None,
        expires_at=coupon.expires_at.isoformat() if coupon.expires_at else None,
        created_at=coupon.created_at.isoformat() if coupon.created_at else "",
    )


@router.post("/{coupon_id}/feedback")
async def submit_feedback(
    coupon_id: int,
    feedback_type: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit coupon feedback (worked/failed/saved/reported)."""
    user_id = int(current_user["sub"])

    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    # Create feedback
    feedback = CouponFeedback(
        coupon_id=coupon_id,
        user_id=user_id,
        feedback_type=feedback_type,
    )
    db.add(feedback)

    # Update coupon metrics
    if feedback_type == "worked":
        coupon.success_count += 1
        coupon.total_uses += 1
    elif feedback_type == "failed":
        coupon.fail_count += 1
        coupon.total_uses += 1
    elif feedback_type == "saved":
        coupon.saves += 1

    await db.flush()
    return {"message": "Feedback submitted", "type": feedback_type}
