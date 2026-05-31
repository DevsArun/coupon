"""Search and analytics models."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Float,
    ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    query = Column(String(500), nullable=False)
    processed_query = Column(String(500), nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    results_count = Column(Integer, default=0)
    response_time_ms = Column(Integer, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_typo_corrected = Column(Boolean, default=False)
    merchant_detected = Column(String(255), nullable=True)
    clicked_coupon_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="search_logs")

    __table_args__ = (
        Index("idx_search_user", "user_id"),
        Index("idx_search_query", "query"),
        Index("idx_search_created", "created_at"),
    )


class SearchAnalytics(Base):
    __tablename__ = "search_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    total_searches = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    avg_response_time_ms = Column(Float, default=0)
    top_queries = Column(JSON, nullable=True)
    top_merchants = Column(JSON, nullable=True)
    zero_result_queries = Column(JSON, nullable=True)
    conversion_rate = Column(Float, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_analytics_date", "date"),
    )
