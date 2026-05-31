"""Merchant models."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Float,
    ForeignKey, Index, Enum
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class MerchantStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    BLOCKED = "blocked"


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(Enum(MerchantStatus), default=MerchantStatus.ACTIVE)
    trust_score = Column(Float, default=0.5)
    total_coupons = Column(Integer, default=0)
    active_coupons = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    affiliate_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    coupons = relationship("Coupon", back_populates="merchant")
    aliases = relationship("MerchantAlias", back_populates="merchant")
    sources = relationship("MerchantSource", back_populates="merchant")

    __table_args__ = (
        Index("idx_merchant_status", "status"),
        Index("idx_merchant_category", "category"),
        Index("idx_merchant_featured", "is_featured"),
    )


class MerchantAlias(Base):
    __tablename__ = "merchant_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String(255), nullable=False, index=True)
    is_typo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    merchant = relationship("Merchant", back_populates="aliases")

    __table_args__ = (
        Index("idx_alias_merchant", "merchant_id"),
    )


class SourceType(str, enum.Enum):
    OFFICIAL_PAGE = "official_page"
    PROMOTION_PAGE = "promotion_page"
    RSS_FEED = "rss_feed"
    SITEMAP = "sitemap"
    DEAL_PAGE = "deal_page"
    EMAIL = "email"
    USER_SUBMITTED = "user_submitted"


class MerchantSource(Base):
    __tablename__ = "merchant_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    trust_score = Column(Float, default=0.5)
    last_crawled = Column(DateTime, nullable=True)
    crawl_frequency_hours = Column(Integer, default=24)
    success_rate = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    merchant = relationship("Merchant", back_populates="sources")

    __table_args__ = (
        Index("idx_source_merchant", "merchant_id"),
        Index("idx_source_type", "source_type"),
        Index("idx_source_active", "is_active"),
    )
