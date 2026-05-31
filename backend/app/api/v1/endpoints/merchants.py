"""Merchant endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.merchant import Merchant
from app.schemas.merchant import MerchantCreate, MerchantUpdate, MerchantResponse

router = APIRouter()


@router.get("", response_model=List[MerchantResponse])
async def list_merchants(
    category: Optional[str] = None,
    is_featured: Optional[bool] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List merchants with optional filters."""
    query = select(Merchant).order_by(Merchant.active_coupons.desc())

    if category:
        query = query.where(Merchant.category == category)
    if is_featured is not None:
        query = query.where(Merchant.is_featured == is_featured)
    if status:
        query = query.where(Merchant.status == status)
    else:
        query = query.where(Merchant.status == "active")

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    merchants = result.scalars().all()

    return [
        MerchantResponse(
            id=m.id,
            name=m.name,
            slug=m.slug,
            domain=m.domain,
            logo_url=m.logo_url,
            description=m.description,
            category=m.category,
            status=m.status.value if m.status else "active",
            trust_score=m.trust_score,
            total_coupons=m.total_coupons,
            active_coupons=m.active_coupons,
            is_featured=m.is_featured,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in merchants
    ]


@router.get("/{slug}", response_model=MerchantResponse)
async def get_merchant(slug: str, db: AsyncSession = Depends(get_db)):
    """Get merchant by slug."""
    result = await db.execute(select(Merchant).where(Merchant.slug == slug))
    merchant = result.scalar_one_or_none()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return MerchantResponse(
        id=merchant.id,
        name=merchant.name,
        slug=merchant.slug,
        domain=merchant.domain,
        logo_url=merchant.logo_url,
        description=merchant.description,
        category=merchant.category,
        status=merchant.status.value if merchant.status else "active",
        trust_score=merchant.trust_score,
        total_coupons=merchant.total_coupons,
        active_coupons=merchant.active_coupons,
        is_featured=merchant.is_featured,
        created_at=merchant.created_at.isoformat() if merchant.created_at else "",
    )
