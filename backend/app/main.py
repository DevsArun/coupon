"""CouponAI - Main FastAPI Application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import init_redis, close_redis
from app.api.v1.router import api_router
from app.middleware.rate_limiter import RateLimitMiddleware

# Import all models so Base.metadata knows about them before create_all
import app.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")

    # Initialize Meilisearch
    try:
        from app.services.search import search_service
        await search_service.initialize_index()
        logger.info("Meilisearch index configured")
    except Exception as e:
        logger.warning(f"Meilisearch not available: {e}")

    # Seed initial data
    await seed_initial_data()

    yield

    # Shutdown
    await close_db()
    await close_redis()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Coupon Intelligence Platform",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.add_middleware(RateLimitMiddleware)

# API Routes
app.include_router(api_router)

# Static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")



@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", response_class=HTMLResponse)
async def serve_landing():
    """Serve the landing page."""
    try:
        with open("frontend/templates/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>CouponAI</h1><p>Platform loading...</p>")


@app.get("/app", response_class=HTMLResponse)
@app.get("/app/{path:path}", response_class=HTMLResponse)
async def serve_app(path: str = ""):
    """Serve the main application."""
    try:
        with open("frontend/templates/user/dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>CouponAI Dashboard</h1>")


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/{path:path}", response_class=HTMLResponse)
async def serve_admin(path: str = ""):
    """Serve the admin panel."""
    try:
        with open("frontend/templates/admin/dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin Panel</h1>")


@app.get("/login", response_class=HTMLResponse)
async def serve_login():
    """Serve login page."""
    try:
        with open("frontend/templates/auth/login.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Login</h1>")


@app.get("/register", response_class=HTMLResponse)
async def serve_register():
    """Serve register page."""
    try:
        with open("frontend/templates/auth/register.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Register</h1>")



async def seed_initial_data():
    """Seed initial data - plans, super admin, etc."""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, RoleType
    from app.models.billing import Plan, PlanInterval, PlanStatus
    from app.core.security import hash_password
    from sqlalchemy import select
    import secrets

    async with AsyncSessionLocal() as db:
        try:
            # Check if super admin exists
            result = await db.execute(
                select(User).where(User.email == settings.SUPER_ADMIN_EMAIL)
            )
            if not result.scalar_one_or_none():
                admin = User(
                    email=settings.SUPER_ADMIN_EMAIL,
                    username="superadmin",
                    password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
                    full_name="Super Admin",
                    role=RoleType.SUPER_ADMIN,
                    is_active=True,
                    is_verified=True,
                    referral_code=secrets.token_urlsafe(8),
                )
                db.add(admin)
                logger.info("Super admin created")

            # Seed plans
            result = await db.execute(select(Plan).where(Plan.slug == "free"))
            if not result.scalar_one_or_none():
                plans = [
                    Plan(name="Free", slug="free", price=0, interval=PlanInterval.MONTHLY,
                         searches_per_day=10, is_free=True, sort_order=0,
                         status=PlanStatus.ACTIVE,
                         description="10 searches per day"),
                    Plan(name="Starter", slug="starter", price=5, interval=PlanInterval.MONTHLY,
                         searches_per_month=100, sort_order=1,
                         status=PlanStatus.ACTIVE,
                         description="100 searches per month"),
                    Plan(name="Pro", slug="pro", price=10, interval=PlanInterval.MONTHLY,
                         searches_per_month=200, sort_order=2,
                         status=PlanStatus.ACTIVE,
                         description="200 searches per month"),
                    Plan(name="Yearly Pro", slug="yearly-pro", price=49, interval=PlanInterval.YEARLY,
                         searches_per_day=100, sort_order=3,
                         status=PlanStatus.ACTIVE,
                         description="100 searches per day"),
                    Plan(name="Yearly Elite", slug="yearly-elite", price=99, interval=PlanInterval.YEARLY,
                         searches_per_day=200, sort_order=4,
                         status=PlanStatus.ACTIVE,
                         description="200 searches per day"),
                ]
                for plan in plans:
                    db.add(plan)
                logger.info("Plans seeded")

            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Seed error: {e}")
