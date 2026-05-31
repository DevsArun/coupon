"""Coupon models."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Float,
    ForeignKey, Index, Enum, JSON
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CouponType(str, enum.Enum):
    CODE = "code"
    DEAL = "deal"
    CASHBACK = "cashback"
    FREE_SHIPPING = "free_shipping"
    BOGO = "bogo"
    PERCENTAGE = "percentage"
    FLAT = "flat"


class CouponStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    UNVERIFIED = "unverified"
    INVALID = "invalid"
    PENDING = "pending"


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    code = Column(String(100), nullable=True, index=True)
    coupon_type = Column(Enum(CouponType), nullable=False)
    status = Column(Enum(CouponStatus), default=CouponStatus.ACTIVE)
    discount_value = Column(Float, nullable=True)
    discount_unit = Column(String(20), nullable=True)  # percent, usd, etc.
    minimum_purchase = Column(Float, nullable=True)
    maximum_discount = Column(Float, nullable=True)
    url = Column(String(500), nullable=True)
    affiliate_url = Column(String(500), nullable=True)
    terms = Column(Text, nullable=True)
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)
    is_exclusive = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)

    # Scoring
    source_trust_score = Column(Float, default=0.5)
    freshness_score = Column(Float, default=1.0)
    success_score = Column(Float, default=0.5)
    duplicate_score = Column(Float, default=1.0)
    expiry_confidence = Column(Float, default=0.5)
    final_confidence = Column(Float, default=0.5)

    # Metrics
    total_uses = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    views = Column(Integer, default=0)
    saves = Column(Integer, default=0)

    # Source tracking
    source_url = Column(String(500), nullable=True)
    source_type = Column(String(50), nullable=True)
    crawled_at = Column(DateTime, nullable=True)

    # AI metadata
    ai_extracted = Column(Boolean, default=False)
    ai_confidence = Column(Float, nullable=True)
    ai_tags = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    merchant = relationship("Merchant", back_populates="coupons")
    tags = relationship("CouponTag", back_populates="coupon")
    feedback = relationship("CouponFeedback", back_populates="coupon")

    __table_args__ = (
        Index("idx_coupon_merchant", "merchant_id"),
        Index("idx_coupon_status", "status"),
        Index("idx_coupon_type", "coupon_type"),
        Index("idx_coupon_expires", "expires_at"),
        Index("idx_coupon_confidence", "final_confidence"),
        Index("idx_coupon_featured", "is_featured"),
        Index("idx_coupon_verified", "is_verified"),
        Index("idx_coupon_created", "created_at"),
    )


class CouponCategory(Base):
    __tablename__ = "coupon_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50), nullable=True)
    parent_id = Column(Integer, ForeignKey("coupon_categories.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CouponTag(Base):
    __tablename__ = "coupon_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(100), nullable=False, index=True)

    coupon = relationship("Coupon", back_populates="tags")

    __table_args__ = (
        Index("idx_tag_coupon", "coupon_id"),
    )


class FeedbackType(str, enum.Enum):
    WORKED = "worked"
    FAILED = "failed"
    SAVED = "saved"
    REPORTED = "reported"


class CouponFeedback(Base):
    __tablename__ = "coupon_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    feedback_type = Column(Enum(FeedbackType), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    coupon = relationship("Coupon", back_populates="feedback")
    user = relationship("User", back_populates="saved_coupons")

    __table_args__ = (
        Index("idx_feedback_coupon", "coupon_id"),
        Index("idx_feedback_user", "user_id"),
    )
