"""APScheduler setup (same design as Tangent): jobs run inside the backend process.

Single-instance design: one backend container, no leader election. All
crons are in JOBS_TIMEZONE (Asia/Singapore). Each job opens its own session
and catches its exceptions so the scheduler keeps ticking.

Jobs:
- generation_submit     03:00 daily   → batch of tomorrow's exercises
- generation_poll       every 30 min  → insert batch results as they land
- generation_fallback   05:30 daily   → sync for whatever is still missing
- generation_catch_up   at boot +60 s → today never empty, missed nights redone
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .generation import jobs as generation_jobs

logger = logging.getLogger(__name__)

JOBS_TZ = ZoneInfo(os.getenv("JOBS_TIMEZONE", "Asia/Singapore"))
_DAILY = {"replace_existing": True, "max_instances": 1, "coalesce": True}


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=JOBS_TZ)
    sub, fb = generation_jobs.SUBMIT_AT, generation_jobs.FALLBACK_AT

    scheduler.add_job(
        generation_jobs.job_submit_batch,
        CronTrigger(hour=sub.hour, minute=sub.minute, timezone=JOBS_TZ),
        id="generation_submit",
        **_DAILY,
    )
    scheduler.add_job(
        generation_jobs.job_poll_batches,
        CronTrigger(minute="0,30", timezone=JOBS_TZ),
        id="generation_poll",
        **_DAILY,
    )
    scheduler.add_job(
        generation_jobs.job_fallback,
        CronTrigger(hour=fb.hour, minute=fb.minute, timezone=JOBS_TZ),
        id="generation_fallback",
        **_DAILY,
    )
    scheduler.add_job(
        generation_jobs.job_catch_up_at_boot,
        DateTrigger(run_date=datetime.now(JOBS_TZ) + timedelta(seconds=60)),
        id="generation_catch_up",
        replace_existing=True,
    )
    logger.info("Scheduler configured: %d jobs (%s)", len(scheduler.get_jobs()), JOBS_TZ)
    return scheduler
