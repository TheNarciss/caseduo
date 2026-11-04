"""FastAPI entry point — mount routers + middlewares + lifespan (same shape as Tangent).

Endpoint business logic lives in app/routers/. main.py is intentionally thin.
"""

import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from time import time as _now

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import logging_config
from .auth import UserRead, UserUpdate, auth_backend, fastapi_users
from .auth import apple as apple_auth
from .auth import session as app_session
from .auth.backend import COOKIE_NAME, cookie_transport
from .db import ping as db_ping
from .db.init_db import init_db
from .errors import AppError
from .routers import ROUTERS, admin_pages

logging_config.configure()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Apply migrations, then start the scheduler (generation, push, leagues)."""
    try:
        await init_db()
    except Exception:
        logger.exception("Failed to initialize DB schema at startup")

    scheduler = None
    if os.getenv("SCHEDULER_ENABLED", "true").lower() == "true":
        from .scheduler import setup_scheduler

        scheduler = setup_scheduler()
        scheduler.start()
        logger.info("APScheduler started")
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info("APScheduler stopped")


app = FastAPI(title="CaseDuo", version="0.1.0", lifespan=lifespan)


# ─── Rate limiter (sliding window, same as Tangent) ───────────────────────
_AUTH_RATE_LIMITS = {
    "/api/auth/login": (5, 60),
    "/api/auth/apple/native": (10, 60),
}
_attempts: dict[tuple[str, str], list[float]] = defaultdict(list)


@app.middleware("http")
async def apply_auth_rate_limits(request: Request, call_next):
    if request.method == "POST" and request.url.path in _AUTH_RATE_LIMITS:
        max_count, window_seconds = _AUTH_RATE_LIMITS[request.url.path]
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, request.url.path)
        now = _now()
        _attempts[key] = [t for t in _attempts[key] if now - t < window_seconds]
        if len(_attempts[key]) >= max_count:
            retry_after = int(window_seconds - (now - _attempts[key][0]))
            logger.warning("Rate limit hit: ip=%s path=%s", client_ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Trop de tentatives. Réessaie dans {retry_after} s.",
                    "type": "RateLimitExceeded",
                },
                headers={"Retry-After": str(retry_after)},
            )
        _attempts[key].append(now)
    return await call_next(request)


@app.middleware("http")
async def renew_session_while_in_use(request: Request, call_next):
    """A session that is used stays open (Tangent ADR-035), on `/api/users/me` only."""
    response = await call_next(request)
    if request.url.path != "/api/users/me" or response.status_code != 200:
        return response
    token = request.cookies.get(COOKIE_NAME)
    fresh = app_session.renewed_token(token) if token else None
    if fresh:
        cookie_transport._set_login_cookie(response, fresh)
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if os.getenv("ENV", "dev") == "prod":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled exception in %s %s", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d (%.0f ms)", request.method, request.url.path, response.status_code, duration_ms
    )
    return response


# ─── Health ───────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health():
    db_ok = await db_ping()
    return {"status": "ok" if db_ok else "degraded", "db": "up" if db_ok else "down"}


# ─── Auth (fastapi-users) ─────────────────────────────────────────────────
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/api/auth", tags=["auth"])
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/api/users", tags=["users"]
)


@app.get("/api/auth/providers", tags=["auth"])
async def auth_providers() -> dict[str, bool]:
    """Which sign-in buttons the app may show: only what the backend can honour."""
    return {"apple": apple_auth.is_configured()}


if apple_auth.is_configured():
    app.include_router(apple_auth.build_router(), prefix="/api/auth/apple", tags=["auth"])
else:
    logger.warning("Sign in with Apple not configured — set APPLE_BUNDLE_ID in backend/.env.")

# ─── Business routers (all require auth) ──────────────────────────────────
for router in ROUTERS:
    app.include_router(router, prefix="/api")
app.include_router(admin_pages.router)


# ─── Exception handlers ───────────────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("%s on %s: %s", type(exc).__name__, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": type(exc).__name__},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled %s on %s", type(exc).__name__, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne.", "type": type(exc).__name__},
    )
