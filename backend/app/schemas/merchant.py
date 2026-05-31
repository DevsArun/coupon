"""Merchant schemas."""
from typing import Optional, List
from pydantic import BaseModel


class MerchantCreate(BaseModel):
    name: str
    slug: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    affiliate_url: Optional[str] = None


class MerchantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    affiliate_url: Optional[str] = None


class MerchantResponse(BaseModel):
    id: int
    name: str
    slug: str
    domain: Optional[str]
    logo_url: Optional[str]
    description: Optional[str]
    category: Optional[str]
    status: str
    trust_score: float
    total_coupons: int
    active_coupons: int
    is_featured: bool
    created_at: str

    class Config:
        from_attributes = True
