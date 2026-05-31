"""Seed script to populate database with sample merchants and coupons."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import AsyncSessionLocal, init_db
from app.models.merchant import Merchant, MerchantAlias, MerchantSource, SourceType
from app.models.coupon import Coupon, CouponType, CouponStatus, CouponTag
from datetime import datetime, timezone, timedelta


SAMPLE_MERCHANTS = [
    {"name": "Amazon", "slug": "amazon", "domain": "amazon.com", "category": "ecommerce", "trust_score": 0.95},
    {"name": "Nike", "slug": "nike", "domain": "nike.com", "category": "fashion", "trust_score": 0.90},
    {"name": "Hostinger", "slug": "hostinger", "domain": "hostinger.com", "category": "hosting", "trust_score": 0.85},
    {"name": "NordVPN", "slug": "nordvpn", "domain": "nordvpn.com", "category": "vpn", "trust_score": 0.88},
    {"name": "Walmart", "slug": "walmart", "domain": "walmart.com", "category": "ecommerce", "trust_score": 0.92},
    {"name": "Best Buy", "slug": "best-buy", "domain": "bestbuy.com", "category": "electronics", "trust_score": 0.90},
    {"name": "Adidas", "slug": "adidas", "domain": "adidas.com", "category": "fashion", "trust_score": 0.88},
    {"name": "ExpressVPN", "slug": "expressvpn", "domain": "expressvpn.com", "category": "vpn", "trust_score": 0.87},
    {"name": "Target", "slug": "target", "domain": "target.com", "category": "ecommerce", "trust_score": 0.90},
    {"name": "DoorDash", "slug": "doordash", "domain": "doordash.com", "category": "food", "trust_score": 0.85},
]

SAMPLE_COUPONS = [
    {"merchant": "amazon", "title": "20% Off Electronics", "code": "TECH20", "type": CouponType.PERCENTAGE, "discount_value": 20, "discount_unit": "percent"},
    {"merchant": "amazon", "title": "Free Shipping on Orders $25+", "code": None, "type": CouponType.FREE_SHIPPING, "discount_value": None, "discount_unit": None},
    {"merchant": "amazon", "title": "$10 Off First Order", "code": "FIRST10", "type": CouponType.FLAT, "discount_value": 10, "discount_unit": "usd"},
    {"merchant": "nike", "title": "30% Off Clearance", "code": "CLEAR30", "type": CouponType.PERCENTAGE, "discount_value": 30, "discount_unit": "percent"},
    {"merchant": "nike", "title": "Buy One Get One 50% Off", "code": "BOGO50", "type": CouponType.BOGO, "discount_value": 50, "discount_unit": "percent"},
    {"merchant": "hostinger", "title": "75% Off Web Hosting", "code": "HOST75", "type": CouponType.PERCENTAGE, "discount_value": 75, "discount_unit": "percent"},
    {"merchant": "hostinger", "title": "Free Domain with Annual Plan", "code": None, "type": CouponType.DEAL, "discount_value": None, "discount_unit": None},
    {"merchant": "nordvpn", "title": "68% Off 2-Year Plan", "code": "NORD68", "type": CouponType.PERCENTAGE, "discount_value": 68, "discount_unit": "percent"},
    {"merchant": "nordvpn", "title": "3 Months Free with Annual", "code": None, "type": CouponType.DEAL, "discount_value": None, "discount_unit": None},
    {"merchant": "walmart", "title": "$15 Off $75 Grocery Order", "code": "GROC15", "type": CouponType.FLAT, "discount_value": 15, "discount_unit": "usd"},
    {"merchant": "best-buy", "title": "10% Off Laptops", "code": "LAP10", "type": CouponType.PERCENTAGE, "discount_value": 10, "discount_unit": "percent"},
    {"merchant": "adidas", "title": "25% Off Full Price", "code": "ADIDAS25", "type": CouponType.PERCENTAGE, "discount_value": 25, "discount_unit": "percent"},
    {"merchant": "expressvpn", "title": "49% Off + 3 Months Free", "code": "EXPRESS49", "type": CouponType.PERCENTAGE, "discount_value": 49, "discount_unit": "percent"},
    {"merchant": "target", "title": "$5 Off $50 Purchase", "code": "SAVE5", "type": CouponType.FLAT, "discount_value": 5, "discount_unit": "usd"},
    {"merchant": "doordash", "title": "40% Off First Order", "code": "DASH40", "type": CouponType.PERCENTAGE, "discount_value": 40, "discount_unit": "percent"},
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Create merchants
        merchant_map = {}
        for m_data in SAMPLE_MERCHANTS:
            merchant = Merchant(
                name=m_data["name"], slug=m_data["slug"], domain=m_data["domain"],
                category=m_data["category"], trust_score=m_data["trust_score"],
                status="active", total_coupons=0, active_coupons=0, is_featured=True,
            )
            db.add(merchant)
            await db.flush()
            merchant_map[m_data["slug"]] = merchant.id

            # Add alias
            alias = MerchantAlias(merchant_id=merchant.id, alias=m_data["name"].lower())
            db.add(alias)

        # Create coupons
        for c_data in SAMPLE_COUPONS:
            mid = merchant_map.get(c_data["merchant"])
            if not mid:
                continue
            coupon = Coupon(
                merchant_id=mid,
                title=c_data["title"],
                code=c_data["code"],
                coupon_type=c_data["type"],
                status=CouponStatus.ACTIVE,
                discount_value=c_data["discount_value"],
                discount_unit=c_data["discount_unit"],
                is_verified=True,
                source_trust_score=0.85,
                freshness_score=0.90,
                success_score=0.75,
                duplicate_score=1.0,
                expiry_confidence=0.80,
                final_confidence=0.82,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                source_type="official_page",
                ai_extracted=True,
                ai_confidence=0.9,
            )
            db.add(coupon)

        await db.commit()
        print(f"Seeded {len(SAMPLE_MERCHANTS)} merchants and {len(SAMPLE_COUPONS)} coupons")


if __name__ == "__main__":
    asyncio.run(seed())
