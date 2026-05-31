"""Billing and subscription models."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Float,
    ForeignKey, Index, Enum, JSON
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class PlanInterval(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class PlanStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    interval = Column(Enum(PlanInterval), nullable=False)
    status = Column(Enum(PlanStatus), default=PlanStatus.ACTIVE)
    searches_per_day = Column(Integer, nullable=True)
    searches_per_month = Column(Integer, nullable=True)
    features = Column(JSON, nullable=True)
    stripe_price_id = Column(String(255), nullable=True)
    razorpay_plan_id = Column(String(255), nullable=True)
    is_custom = Column(Boolean, default=False)
    is_free = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("Subscription", back_populates="plan")


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    PAUSED = "paused"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    payment_provider = Column(String(50), nullable=True)  # stripe, razorpay
    provider_subscription_id = Column(String(255), nullable=True)
    provider_customer_id = Column(String(255), nullable=True)
    starts_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ends_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    is_lifetime = Column(Boolean, default=False)
    searches_used_today = Column(Integer, default=0)
    searches_used_month = Column(Integer, default=0)
    last_reset_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")

    __table_args__ = (
        Index("idx_sub_user", "user_id"),
        Index("idx_sub_status", "status"),
        Index("idx_sub_provider", "payment_provider"),
    )


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="usd")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_provider = Column(String(50), nullable=False)
    provider_payment_id = Column(String(255), nullable=True)
    provider_invoice_id = Column(String(255), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="payments")

    __table_args__ = (
        Index("idx_payment_user", "user_id"),
        Index("idx_payment_status", "status"),
        Index("idx_payment_provider", "payment_provider"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    invoice_number = Column(String(100), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="usd")
    description = Column(Text, nullable=True)
    status = Column(String(50), default="issued")
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    due_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    pdf_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_invoice_user", "user_id"),
    )
