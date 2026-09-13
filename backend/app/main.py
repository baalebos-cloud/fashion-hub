"""
Application entrypoint. Wires together middleware, exception handlers,
rate limiting, CORS, routers, and health endpoints.

Run locally with: uvicorn app.main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import check_database_health
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.redis import check_redis_health

configure_logging()

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])

app = FastAPI(
    title=settings.APP_NAME,
    description="Fashion Hub backend API -- connecting customers, tailors/designers, material vendors, and delivery partners.",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["Health"])
def health():
    """Liveness-adjacent basic check: process is up and serving requests."""
    return {"status": "ok"}


@app.get("/health/live", tags=["Health"])
def health_live():
    """Kubernetes/orchestrator liveness probe: process is running."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def health_ready():
    """Readiness probe: verifies the app can actually serve traffic by
    checking its critical dependencies (DB, Redis)."""
    db_ok = check_database_health()
    redis_ok = check_redis_health()
    ready = db_ok and redis_ok
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {"database": db_ok, "redis": redis_ok},
    }
