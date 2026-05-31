"""Script to index all coupons to Meilisearch."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import AsyncSessionLocal, init_db
from app.models.coupon import Coupon
from app.models.merchant import Merchant, MerchantAlias
from app.services.search import search_service
from sqlalchemy import select
from datetime import timezone


async def index_all():
    """Index all active coupons to Meilisearch."""
    await init_db()
    await search_service.initialize_index()

    async with AsyncSessionLocal() as db:
        # Get all coupons with merchants
        result = await db.execute(
            select(Coupon, Merchant)
            .join(Merchant, Coupon.merchant_id == Merchant.id)
            .where(Coupon.status == "active")
        )
        rows = result.all()

        documents = []
        for coupon, merchant in rows:
            # Get merchant aliases
            alias_result = await db.execute(
                select(MerchantAlias.alias).where(MerchantAlias.merchant_id == merchant.id)
            )
            aliases = [a for (a,) in alias_result.all()]

            doc = {
                "id": coupon.id,
                "title": coupon.title,
                "description": coupon.description or "",
                "code": coupon.code or "",
                "merchant_id": merchant.id,
                "merchant_name": merchant.name,
                "merchant_aliases": aliases,
                "coupon_type": coupon.coupon_type.value if coupon.coupon_type else "deal",
                "status": coupon.status.value if coupon.status else "active",
                "discount_value": coupon.discount_value or 0,
                "discount_unit": coupon.discount_unit or "",
                "is_verified": coupon.is_verified,
                "is_featured": coupon.is_featured,
                "is_exclusive": coupon.is_exclusive,
                "category": merchant.category or "",
                "tags": [],
                "final_confidence": coupon.final_confidence or 0.5,
                "success_score": coupon.success_score or 0.5,
                "views": coupon.views or 0,
                "url": coupon.url or "",
                "terms": coupon.terms or "",
                "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else "",
                "expires_at_ts": int(coupon.expires_at.replace(tzinfo=timezone.utc).timestamp()) if coupon.expires_at else 0,
                "created_at_ts": int(coupon.created_at.replace(tzinfo=timezone.utc).timestamp()) if coupon.created_at else 0,
            }
            documents.append(doc)

        if documents:
            await search_service.index_coupons_batch(documents)
            print(f"Indexed {len(documents)} coupons to Meilisearch")
        else:
            print("No coupons to index")


if __name__ == "__main__":
    asyncio.run(index_all())
