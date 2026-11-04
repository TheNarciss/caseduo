"""APScheduler setup (same design as Tangent). Jobs arrive with their features."""

from __future__ import annotations

import logging
import os
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

JOBS_TZ = ZoneInfo(os.getenv("JOBS_TIMEZONE", "Asia/Singapore"))


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=JOBS_TZ)
    logger.info("Scheduler configured: %d jobs", len(scheduler.get_jobs()))
    return scheduler
