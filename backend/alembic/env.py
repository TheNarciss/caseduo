"""Alembic env.py — async, wired to app.* metadata (same as Tangent).

Run: `alembic upgrade head`. New revisions are written by hand (the
convention: autogenerate misses server defaults on NOT NULL columns).
DATABASE_URL must be set (else the local dev fallback).
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import app.auth.oauth_models  # noqa: E402,F401 — registers oauth_account
import app.db.models  # noqa: E402,F401 — registers business tables
from app.auth.models import Base  # noqa: E402

target_metadata = Base.metadata

config = context.config
db_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://caseduo:caseduo_dev@localhost:5433/caseduo",
)
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def render_item(type_, obj, autogen_context):
    """fastapi-users GUID type rendered as an importable expression."""
    if type_ == "type" and obj.__class__.__module__.startswith("fastapi_users_db_sqlalchemy"):
        autogen_context.imports.add("import fastapi_users_db_sqlalchemy")
        return "fastapi_users_db_sqlalchemy.generics.GUID()"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
