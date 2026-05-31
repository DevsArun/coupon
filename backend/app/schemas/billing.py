"""Billing schemas."""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    price: float
    interval: str
    searches_per_day: Optional[int]
    searches_per_month: Optional[int]
    features: Optional[Dict[str, Any]]
    is_free: bool
    sort_order: int

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    plan_id: int
    plan_name: Optional[str] = None
    status: str
    payment_provider: Optional[str]
    starts_at: str
    ends_at: Optional[str]
    is_lifetime: bool
    searches_used_today: int
    searches_used_month: int

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    plan_id: int
    payment_provider: str  # stripe, razorpay
    currency: str = "usd"


class PaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    status: str
    payment_provider: str
    created_at: str

    class Config:
        from_attributes = True
