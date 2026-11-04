"""Shared test fixtures (same approach as Tangent).

Env vars are set BEFORE the app is imported. Integration tests run against a
real Postgres with the Alembic migrations applied, through httpx's ASGI
transport. No test reaches Anthropic or Apple: the LLM client is replaced by
a fake in each test that needs one.
"""

import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production-use-only-xxxxxxxx")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://caseduo:caseduo_dev@localhost:5433/caseduo_test"
)
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("APPLE_BUNDLE_ID", "uk.test.caseduo")
os.environ.setdefault("JOBS_TIMEZONE", "Asia/Singapore")
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ.setdefault("APNS_TEAM_ID", "")

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_TABLES = (
    "league_weeks, reveals, revenges, llm_daily_cost, user_badges, user_story, "
    "daily_activity, attempts, mock_runs, exercises, cron_runs, oauth_account, users"
)


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def migrated():
    """Apply Alembic migrations once (same mechanism as production)."""
    from app.db.init_db import init_db

    await init_db()
    yield


@pytest_asyncio.fixture(loop_scope="session")
async def db(migrated):
    """A session on the test DB; every business table is emptied afterwards."""
    from app.db import async_session_factory, engine

    async with async_session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {_TABLES} CASCADE"))


@pytest_asyncio.fixture(loop_scope="session")
async def client(db):
    """A fresh client (fresh cookie jar) per test."""
    from app.main import _attempts, app

    _attempts.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_user(email: str, password: str, *, admin: bool = False, **fields):
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

    from app.auth import User, UserCreate
    from app.auth.manager import UserManager, password_helper
    from app.auth.oauth_models import OAuthAccount
    from app.db import async_session_factory

    async with async_session_factory() as session:
        manager = UserManager(
            SQLAlchemyUserDatabase(session, User, OAuthAccount), password_helper=password_helper
        )
        user = await manager.create(
            UserCreate(email=email, password=password, is_superuser=admin, is_verified=True),
            safe=False,
        )
        if fields:
            row = await session.get(User, user.id)
            for k, v in fields.items():
                setattr(row, k, v)
            await session.commit()
        return user


@pytest.fixture
def create_user():
    return _create_user


@pytest_asyncio.fixture(loop_scope="session")
async def user_client(client):
    """A logged-in client and its user (fresh e-mail each time)."""
    email = f"u-{uuid.uuid4().hex[:8]}@example.com"
    user = await _create_user(email, "correct-horse-battery")
    resp = await client.post(
        "/api/auth/login", data={"username": email, "password": "correct-horse-battery"}
    )
    assert resp.status_code == 204, resp.text
    return client, user


@pytest_asyncio.fixture(loop_scope="session")
async def admin_client(client):
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    user = await _create_user(email, "correct-horse-battery", admin=True)
    resp = await client.post(
        "/api/auth/login", data={"username": email, "password": "correct-horse-battery"}
    )
    assert resp.status_code == 204, resp.text
    return client, user
