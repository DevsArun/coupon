# CouponAI - AI-Powered Coupon Intelligence Platform

An enterprise-grade SaaS platform for AI-powered coupon discovery and search.

## Architecture

```
Frontend (HTML5 + TailwindCSS + Vanilla JS)
    ↓
FastAPI Backend (Python)
    ├── MySQL (Primary Database)
    ├── Meilisearch (Search Engine)
    ├── Redis (Cache & Rate Limiting)
    └── AI Providers (Groq → Gemini → OpenAI)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, TailwindCSS, Vanilla JavaScript |
| Backend | Python FastAPI |
| Database | MySQL 8.0 |
| Search | Meilisearch |
| Cache | Redis |
| AI | Groq, Gemini, OpenAI (with fallback chain) |
| Auth | JWT + Refresh Tokens |
| Deployment | Docker, HuggingFace Spaces, VPS-ready |

## Quick Start

### Using Docker Compose

```bash
# Clone and start all services
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d

# Seed sample data
docker-compose exec app python scripts/seed_data.py

# Index to Meilisearch
docker-compose exec app python scripts/index_to_meilisearch.py
```

### Local Development

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start services (MySQL, Redis, Meilisearch must be running)
uvicorn app.main:app --reload --port 7860

# Access
# Landing: http://localhost:7860
# API Docs: http://localhost:7860/docs
# Admin: http://localhost:7860/admin
# App: http://localhost:7860/app
```

## Default Credentials

- **Super Admin**: admin@couponai.com / SuperAdmin@123

## Business Model

| Plan | Price | Limits |
|------|-------|--------|
| Free | $0 | 10 searches/day |
| Starter | $5/mo | 100 searches/month |
| Pro | $10/mo | 200 searches/month |
| Yearly Pro | $49/yr | 100 searches/day |
| Yearly Elite | $99/yr | 200 searches/day |

## Features

- **AI Search**: Natural language understanding, typo correction, merchant detection
- **Multi-Source Ingestion**: Official pages, RSS, sitemaps, deal sites, email, user submissions
- **Confidence Scoring**: Source trust, freshness, success rate, duplicate detection, expiry confidence
- **SaaS Billing**: Stripe + Razorpay, subscription management, quota enforcement
- **Admin Panel**: Full mission control center with user/coupon/merchant/AI/plan management
- **Security**: JWT auth, RBAC, rate limiting, audit logs, CSRF protection

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| POST /api/v1/auth/register | Register new user |
| POST /api/v1/auth/login | Login |
| POST /api/v1/search | AI-powered search |
| GET /api/v1/search/quick | Quick search (no auth) |
| GET /api/v1/coupons | List coupons |
| GET /api/v1/merchants | List merchants |
| GET /api/v1/billing/plans | List plans |
| GET /api/v1/admin/dashboard | Admin stats |

## Deployment

### Hugging Face Spaces

1. Create a new Space with Docker SDK
2. Set environment variables in Space settings
3. Push this repo to the Space

### VPS (Future)

Use the included `config/nginx.conf` and `docker-compose.yml`.
