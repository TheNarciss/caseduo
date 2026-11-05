"""Seed: generate today + 2 days of backfill, synchronously (not in batch),
to try the app right away.

    python -m app.seed                 # today + the 2 previous days
    python -m app.seed --days 0        # today only
    python -m app.seed --date 2026-11-06
    python -m app.seed --starter       # the hand-written pack, no API call

Idempotent: a slot already generated is never redone. Each day is logged in
`cron_runs` (job = seed) with its tokens and cost.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, timedelta

from . import logging_config
from .db import async_session_factory
from .errors import LLMUnavailableError
from .generation import service
from .llm import cost_tracker

logger = logging.getLogger("app.seed")


async def run(days: list[date], *, starter: bool) -> None:
    async with async_session_factory() as session:
        for day in days:
            if starter:
                n = await service.insert_starter_pack(session, day)
                print(f"{day} : {n} exercices du pack de démarrage")
                continue
            try:
                result = await service.generate_day_sync(session, day, job="seed")
            except LLMUnavailableError as exc:
                print(f"{day} : génération impossible ({exc}). Relance avec --starter.")
                return
            if result is None:
                print(f"{day} : déjà complet")
            else:
                print(
                    f"{day} : {result.n_succeeded}/{result.n_requests} exercices, "
                    f"{result.input_tokens} tokens in / {result.output_tokens} out, "
                    f"${result.cost_usd:.4f}"
                    + (f", {len(result.errors)} erreur(s) dans cron_runs" if result.errors else "")
                )


def main() -> None:
    logging_config.configure()
    parser = argparse.ArgumentParser(prog="python -m app.seed")
    parser.add_argument("--days", type=int, default=2, help="jours de backfill avant aujourd'hui")
    parser.add_argument("--date", type=date.fromisoformat, help="une seule date (YYYY-MM-DD)")
    parser.add_argument("--starter", action="store_true", help="pack écrit à la main, sans API")
    args = parser.parse_args()
    if args.date:
        days = [args.date]
    else:
        today = cost_tracker.today_jobs_tz()
        days = [today - timedelta(days=i) for i in range(args.days, -1, -1)]
    asyncio.run(run(days, starter=args.starter))


if __name__ == "__main__":
    main()
