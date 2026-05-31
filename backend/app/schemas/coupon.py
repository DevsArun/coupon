"""Coupon schemas."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class CouponCreate(BaseModel):
    merchant_id: int
    title: str
    description: Optional[str] = None
    code: Optional[str] = None
    coupon_type: str = "code"
    discount_value: Optional[float] = None
    discount_unit: Optional[str] = None
    minimum_purchase: Optional[float] = None
    maximum_discount: Optional[float] = None
    url: Optional[str] = None
    terms: Optional[str] = None
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None


class CouponUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    coupon_type: Optional[str] = None
    status: Optional[str] = None
    discount_value: Optional[float] = None
    discount_unit: Optional[str] = None
    url: Optional[str] = None
    terms: Optional[str] = None
    expires_at: Optional[str] = None
    is_verified: Optional[bool] = None
    is_featured: Optional[bool] = None


class CouponResponse(BaseModel):
    id: int
    merchant_id: int
    merchant_name: Optional[str] = None
    title: str
    description: Optional[str]
    code: Optional[str]
    coupon_type: str
    status: str
    discount_value: Optional[float]
    discount_unit: Optional[str]
    minimum_purchase: Optional[float]
    maximum_discount: Optional[float]
    url: Optional[str]
    terms: Optional[str]
    is_verified: bool
    is_exclusive: bool
    is_featured: bool
    final_confidence: float
    total_uses: int
    success_count: int
    views: int
    starts_at: Optional[str]
    expires_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class CouponSearchResponse(BaseModel):
    query: str
    corrected_query: Optional[str] = None
    merchant_detected: Optional[str] = None
    total_hits: int
    response_time_ms: int
    results: List[CouponResponse]
    ai_analysis: Optional[Dict[str, Any]] = None
