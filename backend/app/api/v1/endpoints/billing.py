"""Billing and subscription endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.billing import Plan, Subscription, Payment
from app.services.billing import billing_service
from app.schemas.billing import PlanResponse, SubscriptionResponse, PaymentCreate, PaymentResponse

router = APIRouter()


@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all available plans."""
    plans = await billing_service.get_plans(db)
    return [
        PlanResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            price=p.price,
            interval=p.interval.value if p.interval else "monthly",
            searches_per_day=p.searches_per_day,
            searches_per_month=p.searches_per_month,
            features=p.features,
            is_free=p.is_free,
            sort_order=p.sort_order,
        )
        for p in plans
    ]


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscription."""
    user_id = int(current_user["sub"])
    sub = await billing_service.get_user_subscription(db, user_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found")

    # Get plan name
    result = await db.execute(select(Plan.name).where(Plan.id == sub.plan_id))
    plan_name = result.scalar_one_or_none()

    return SubscriptionResponse(
        id=sub.id,
        plan_id=sub.plan_id,
        plan_name=plan_name,
        status=sub.status.value if sub.status else "active",
        payment_provider=sub.payment_provider,
        starts_at=sub.starts_at.isoformat() if sub.starts_at else "",
        ends_at=sub.ends_at.isoformat() if sub.ends_at else None,
        is_lifetime=sub.is_lifetime,
        searches_used_today=sub.searches_used_today,
        searches_used_month=sub.searches_used_month,
    )


@router.get("/quota")
async def check_quota(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check remaining search quota."""
    user_id = int(current_user["sub"])
    return await billing_service.check_search_quota(db, user_id)


@router.post("/subscribe")
async def create_subscription(
    payment_data: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate subscription payment."""
    user_id = int(current_user["sub"])

    # Get plan
    result = await db.execute(select(Plan).where(Plan.id == payment_data.plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Create payment record
    payment = await billing_service.create_payment(
        db, user_id, plan.id,
        payment_data.payment_provider,
        plan.price,
        payment_data.currency,
    )

    # Return payment intent info
    return {
        "payment_id": payment.id,
        "amount": plan.price,
        "currency": payment_data.currency,
        "provider": payment_data.payment_provider,
        "plan_name": plan.name,
        "message": "Complete payment via client-side SDK",
    }


@router.post("/webhook/stripe")
async def stripe_webhook(db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events."""
    # In production, verify webhook signature
    return {"received": True}


@router.post("/webhook/razorpay")
async def razorpay_webhook(db: AsyncSession = Depends(get_db)):
    """Handle Razorpay webhook events."""
    return {"received": True}


@router.post("/cancel")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel current subscription."""
    user_id = int(current_user["sub"])
    await billing_service.cancel_subscription(db, user_id)
    return {"message": "Subscription cancelled"}
