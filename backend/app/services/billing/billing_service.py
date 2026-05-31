"""Unified billing service for Stripe and Razorpay."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.models.billing import Plan, Subscription, Payment, Invoice, SubscriptionStatus, PaymentStatus

logger = logging.getLogger(__name__)


class BillingService:
    """Unified billing management service."""

    async def get_plans(self, db: AsyncSession) -> list:
        """Get all active plans."""
        result = await db.execute(
            select(Plan).where(Plan.status == "active").order_by(Plan.sort_order)
        )
        return result.scalars().all()

    async def get_user_subscription(self, db: AsyncSession, user_id: int) -> Optional[Subscription]:
        """Get user's active subscription."""
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_free_subscription(self, db: AsyncSession, user_id: int) -> Subscription:
        """Create a free plan subscription for new user."""
        # Get free plan
        result = await db.execute(select(Plan).where(Plan.is_free == True))
        free_plan = result.scalar_one_or_none()

        if not free_plan:
            # Create free plan if not exists
            free_plan = Plan(
                name="Free",
                slug="free",
                description="Basic free plan with limited searches",
                price=0,
                interval="monthly",
                status="active",
                searches_per_day=10,
                searches_per_month=None,
                is_free=True,
                sort_order=0,
            )
            db.add(free_plan)
            await db.flush()

        subscription = Subscription(
            user_id=user_id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
            starts_at=datetime.now(timezone.utc),
        )
        db.add(subscription)
        await db.flush()
        return subscription

    async def check_search_quota(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Check if user has remaining search quota."""
        sub = await self.get_user_subscription(db, user_id)
        if not sub:
            return {"allowed": False, "reason": "No subscription", "remaining": 0}

        # Reset daily/monthly counters if needed
        now = datetime.now(timezone.utc)
        if sub.last_reset_date:
            if sub.last_reset_date.date() < now.date():
                sub.searches_used_today = 0
            if sub.last_reset_date.month < now.month or sub.last_reset_date.year < now.year:
                sub.searches_used_month = 0
        sub.last_reset_date = now

        # Load plan
        result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
        plan = result.scalar_one_or_none()

        if not plan:
            return {"allowed": False, "reason": "Plan not found", "remaining": 0}

        # Check daily limit
        if plan.searches_per_day:
            remaining_day = plan.searches_per_day - sub.searches_used_today
            if remaining_day <= 0:
                return {"allowed": False, "reason": "Daily limit reached", "remaining": 0, "limit": plan.searches_per_day}
            return {"allowed": True, "remaining": remaining_day, "limit": plan.searches_per_day, "type": "daily"}

        # Check monthly limit
        if plan.searches_per_month:
            remaining_month = plan.searches_per_month - sub.searches_used_month
            if remaining_month <= 0:
                return {"allowed": False, "reason": "Monthly limit reached", "remaining": 0, "limit": plan.searches_per_month}
            return {"allowed": True, "remaining": remaining_month, "limit": plan.searches_per_month, "type": "monthly"}

        # Lifetime/unlimited
        return {"allowed": True, "remaining": -1, "limit": -1, "type": "unlimited"}

    async def record_search_usage(self, db: AsyncSession, user_id: int):
        """Record a search usage for the user."""
        await db.execute(
            update(Subscription)
            .where(Subscription.user_id == user_id)
            .values(
                searches_used_today=Subscription.searches_used_today + 1,
                searches_used_month=Subscription.searches_used_month + 1,
            )
        )

    async def create_payment(
        self, db: AsyncSession, user_id: int, plan_id: int,
        provider: str, amount: float, currency: str = "usd"
    ) -> Payment:
        """Create a payment record."""
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            amount=amount,
            currency=currency,
            payment_provider=provider,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        await db.flush()
        return payment

    async def complete_payment(
        self, db: AsyncSession, payment_id: int, provider_payment_id: str
    ) -> Payment:
        """Mark payment as completed and activate subscription."""
        result = await db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise ValueError("Payment not found")

        payment.status = PaymentStatus.COMPLETED
        payment.provider_payment_id = provider_payment_id

        # Update subscription
        result = await db.execute(select(Plan).where(Plan.id == payment.plan_id))
        plan = result.scalar_one_or_none()

        if plan:
            now = datetime.now(timezone.utc)
            ends_at = None
            if plan.interval == "monthly":
                ends_at = now + timedelta(days=30)
            elif plan.interval == "yearly":
                ends_at = now + timedelta(days=365)

            await db.execute(
                update(Subscription)
                .where(Subscription.user_id == payment.user_id)
                .values(
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE,
                    payment_provider=payment.payment_provider,
                    starts_at=now,
                    ends_at=ends_at,
                    is_lifetime=(plan.interval == "lifetime"),
                    searches_used_today=0,
                    searches_used_month=0,
                )
            )

        await db.flush()
        return payment

    async def cancel_subscription(self, db: AsyncSession, user_id: int):
        """Cancel user subscription."""
        await db.execute(
            update(Subscription)
            .where(Subscription.user_id == user_id)
            .values(
                status=SubscriptionStatus.CANCELLED,
                cancelled_at=datetime.now(timezone.utc),
            )
        )

    async def create_plan(self, db: AsyncSession, plan_data: Dict[str, Any]) -> Plan:
        """Admin: Create a new plan."""
        plan = Plan(**plan_data)
        db.add(plan)
        await db.flush()
        return plan

    async def update_plan(self, db: AsyncSession, plan_id: int, plan_data: Dict[str, Any]) -> Optional[Plan]:
        """Admin: Update a plan."""
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        if plan:
            for key, value in plan_data.items():
                setattr(plan, key, value)
            await db.flush()
        return plan

    async def assign_custom_plan(self, db: AsyncSession, user_id: int, plan_id: int, is_lifetime: bool = False):
        """Admin: Assign a custom plan to a user."""
        now = datetime.now(timezone.utc)
        await db.execute(
            update(Subscription)
            .where(Subscription.user_id == user_id)
            .values(
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                starts_at=now,
                ends_at=None if is_lifetime else now + timedelta(days=365),
                is_lifetime=is_lifetime,
                searches_used_today=0,
                searches_used_month=0,
            )
        )


billing_service = BillingService()
