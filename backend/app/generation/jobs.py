"""The generation jobs the scheduler runs (Asia/Singapore), with their own sessions.

- 03:00  tomorrow's exercises: written by Claude Code on the subscription (DEVIATIONS D15),
         or submitted as an API batch when only an API key is set
- :00/:30 poll in-flight batches, insert as soon as results land
- 05:30  fallback: whatever tomorrow still lacks is generated synchronously
         (the batch is cancelled first); today is checked too — there must
         never be an empty day
- boot   catch-up: a restart at night (deploy, security updates) must not
         skip any of the above (same idea as Tangent's `missed_tonight`); the bonus
         pack is imported once
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ..content import bonus
from ..db import async_session_factory
from ..db.models import CronRun
from ..errors import LLMUnavailableError
from . import batch, provider, service

logger = logging.getLogger(__name__)

TZ = ZoneInfo(os.getenv("JOBS_TIMEZONE", "Asia/Singapore"))
SUBMIT_AT = time(3, 0)
FALLBACK_AT = time(5, 30)


def now_local() -> datetime:
    return datetime.now(TZ)


async def job_submit_batch() -> None:
    tomorrow = now_local().date() + timedelta(days=1)
    async with async_session_factory() as session:
        try:
            run = await batch.submit_batch(session, tomorrow)
            if run is None:
                logger.info(
                    "Batch for %s not submitted (complete, in flight or over budget)", tomorrow
                )
        except RuntimeError as exc:  # no API key
            logger.warning("Batch for %s skipped: %s", tomorrow, exc)
        except Exception:
            logger.exception("Batch submit for %s failed", tomorrow)


async def job_nightly() -> None:
    """03:00: tomorrow's exercises, by Claude Code (D15) or, with only an API key, by batch."""
    chosen = provider.provider()
    if chosen == "api":
        await job_submit_batch()
        return
    tomorrow = now_local().date() + timedelta(days=1)
    if chosen is None:
        logger.warning("03:00: neither a Claude Code token nor an API key, nothing generated")
        return
    async with async_session_factory() as session:
        try:
            await service.ensure_day(session, tomorrow, job="claude_code")
        except Exception:
            logger.exception("Claude Code generation for %s failed", tomorrow)


async def job_poll_batches() -> None:
    async with async_session_factory() as session:
        try:
            n = await batch.poll_batches(session)
            if n:
                logger.info("%d generation batch(es) finalized", n)
        except RuntimeError as exc:
            logger.warning("Batch polling skipped: %s", exc)
        except Exception:
            logger.exception("Batch polling failed")


async def job_fallback() -> None:
    today = now_local().date()
    tomorrow = today + timedelta(days=1)
    async with async_session_factory() as session:
        try:
            plan, _ = await service.plan_for(session, tomorrow)
            if await service.missing_slots(session, plan):
                cancelled = await batch.cancel_in_flight(session, tomorrow)
                if cancelled:
                    logger.warning(
                        "Batch for %s not back at 05:30: cancelled, going sync", tomorrow
                    )
                await service.ensure_day(session, tomorrow, job="fallback")
            await service.ensure_day(session, today, job="fallback")
        except LLMUnavailableError as exc:
            logger.warning("Fallback: %s", exc)
        except Exception:
            logger.exception("Generation fallback failed")


def missed(now: datetime, at: time, last: datetime | None) -> bool:
    """Whether a daily job due at `at` today has not run since (pure, tested)."""
    due = datetime.combine(now.date(), at, tzinfo=TZ)
    return now >= due and (last is None or last < due)


async def job_catch_up_at_boot() -> None:
    """After a restart: today must have content, tonight's jobs must not be skipped."""
    now = now_local()
    tomorrow = now.date() + timedelta(days=1)
    async with async_session_factory() as session:
        try:
            await bonus.import_packs(session, now.date())
        except Exception:
            logger.exception("Boot catch-up: bonus pack import failed")
            await session.rollback()
        try:
            await service.ensure_day(session, now.date(), job="fallback")
            stmt = (
                select(CronRun.started_at)
                .where(CronRun.target_date == tomorrow)
                .order_by(CronRun.started_at.desc())
                .limit(1)
            )
            last = (await session.execute(stmt)).scalar()
        except Exception:
            logger.exception("Boot catch-up: today's check failed")
            return
    if missed(now, FALLBACK_AT, last):
        logger.warning("Boot catch-up: 05:30 fallback was missed, running it")
        await job_fallback()
    elif missed(now, SUBMIT_AT, last):
        logger.warning("Boot catch-up: 03:00 generation was missed, running it")
        await job_nightly()
