"""LLM cost: per-call computation from `usage`, global daily kill-switch (Tangent ADR-015).

- Prices per model (USD per million tokens), cache writes ×1.25 and reads
  ×0.1 of the input price, web searches $0.01 each.
- Message Batches halve token prices, not web searches.
- `llm_daily_cost` holds one row per day (jobs time zone), incremented by an
  atomic UPSERT; nothing new starts once `LLM_DAILY_CAP_USD` is reached.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import CronRun, LLMDailyCost

logger = logging.getLogger(__name__)

# USD per million tokens (input, output), snapshot 2026-10. Longest prefix wins.
PRICES_PER_MTOK_USD: dict[str, tuple[float, float]] = {
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.0, 5.0),
}
CACHE_WRITE_FACTOR = 1.25
CACHE_READ_FACTOR = 0.10
PRICE_WEB_SEARCH_USD = 0.01
BATCH_DISCOUNT = 0.5

DAILY_CAP_USD = float(os.getenv("LLM_DAILY_CAP_USD", "1.0"))
_TZ = ZoneInfo(os.getenv("JOBS_TIMEZONE", "Asia/Singapore"))


def prices_for(model: str | None) -> tuple[float, float]:
    """(input, output) for the model; the dearest known one if unknown (safe side)."""
    if model:
        for prefix in sorted(PRICES_PER_MTOK_USD, key=len, reverse=True):
            if model.startswith(prefix):
                return PRICES_PER_MTOK_USD[prefix]
    return max(PRICES_PER_MTOK_USD.values())


@dataclass
class Usage:
    """Token counts of one or several calls, and their cost."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    web_searches: int = 0
    cost_usd: float = 0.0
    calls: int = 0
    models: set[str] = field(default_factory=set)

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens
        self.web_searches += other.web_searches
        self.cost_usd += other.cost_usd
        self.calls += other.calls
        self.models |= other.models


def compute_cost_usd(
    model: str | None,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    web_searches: int = 0,
    batch: bool = False,
) -> float:
    """Pure: what one call cost. `input_tokens` excludes cached tokens, as the API reports."""
    price_in, price_out = prices_for(model)
    tokens = (
        input_tokens * price_in
        + cache_write_tokens * price_in * CACHE_WRITE_FACTOR
        + cache_read_tokens * price_in * CACHE_READ_FACTOR
        + output_tokens * price_out
    ) / 1_000_000
    if batch:
        tokens *= BATCH_DISCOUNT
    return tokens + web_searches * PRICE_WEB_SEARCH_USD


def usage_of(message: Any, *, batch: bool = False) -> Usage:
    """Usage and cost of one Anthropic message (sync or from a batch result)."""
    u = getattr(message, "usage", None)

    def n(name: str) -> int:
        return int(getattr(u, name, 0) or 0)

    server = getattr(u, "server_tool_use", None)
    searches = int(getattr(server, "web_search_requests", 0) or 0)
    model = getattr(message, "model", None)
    model = model if isinstance(model, str) else None
    usage = Usage(
        input_tokens=n("input_tokens"),
        output_tokens=n("output_tokens"),
        cache_read_tokens=n("cache_read_input_tokens"),
        cache_write_tokens=n("cache_creation_input_tokens"),
        web_searches=searches,
        calls=1,
        models={model} if model else set(),
    )
    usage.cost_usd = compute_cost_usd(
        model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=usage.cache_read_tokens,
        cache_write_tokens=usage.cache_write_tokens,
        web_searches=usage.web_searches,
        batch=batch,
    )
    return usage


def apply_to_run(run: CronRun, usage: Usage) -> None:
    """Accumulate a usage into a cron_runs row (not committed)."""
    run.input_tokens += usage.input_tokens
    run.output_tokens += usage.output_tokens
    run.cache_read_tokens += usage.cache_read_tokens
    run.cache_write_tokens += usage.cache_write_tokens
    run.web_searches += usage.web_searches
    run.cost_usd = round((run.cost_usd or 0.0) + usage.cost_usd, 6)


def today_jobs_tz() -> date:
    return datetime.now(_TZ).date()


async def get_today_cost_usd(session: AsyncSession, today: date | None = None) -> float:
    today = today or today_jobs_tz()
    stmt = select(LLMDailyCost.cumulative_cost_usd).where(LLMDailyCost.cost_date == today)
    return float((await session.execute(stmt)).scalar() or 0.0)


async def in_flight_estimate_usd(session: AsyncSession) -> float:
    """Batches still processing count against the cap (their real cost comes hours later)."""
    stmt = select(func.coalesce(func.sum(CronRun.estimated_cost_usd), 0.0)).where(
        CronRun.job == "batch", CronRun.status == "in_progress"
    )
    return float((await session.execute(stmt)).scalar() or 0.0)


async def budget_left_usd(session: AsyncSession) -> float:
    spent = await get_today_cost_usd(session)
    return DAILY_CAP_USD - spent - await in_flight_estimate_usd(session)


async def is_under_cap(session: AsyncSession) -> bool:
    return await budget_left_usd(session) > 0


async def record_cost(session: AsyncSession, cost_usd: float, *, commit: bool = True) -> None:
    """Atomically add a cost to today's total (PG UPSERT, race-safe)."""
    if cost_usd <= 0:
        return
    today = today_jobs_tz()
    stmt = pg_insert(LLMDailyCost).values(
        cost_date=today, cumulative_cost_usd=cost_usd, calls_count=1
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["cost_date"],
        set_={
            "cumulative_cost_usd": LLMDailyCost.cumulative_cost_usd
            + stmt.excluded.cumulative_cost_usd,
            "calls_count": LLMDailyCost.calls_count + 1,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    if commit:
        await session.commit()
    logger.info("LLM cost recorded: +$%.4f on %s (cap $%.2f)", cost_usd, today, DAILY_CAP_USD)
