"""System models - audit logs, feature flags, settings."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Float,
    ForeignKey, Index, JSON, Enum
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource_type"),
        Index("idx_audit_created", "created_at"),
    )


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=False)
    conditions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CrawlerJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlerJob(Base):
    __tablename__ = "crawler_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True)
    source_id = Column(Integer, ForeignKey("merchant_sources.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(CrawlerJobStatus), default=CrawlerJobStatus.PENDING)
    job_type = Column(String(50), nullable=False)
    url = Column(String(500), nullable=True)
    results_count = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_job_status", "status"),
        Index("idx_job_merchant", "merchant_id"),
        Index("idx_job_created", "created_at"),
    )


class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(String(50), unique=True, nullable=False)
    is_enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    model_name = Column(String(100), nullable=False)
    api_key_env = Column(String(100), nullable=True)
    max_tokens = Column(Integer, default=1000)
    temperature = Column(Float, default=0.1)
    timeout_seconds = Column(Integer, default=10)
    total_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    avg_response_time_ms = Column(Float, default=0)
    last_used = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
