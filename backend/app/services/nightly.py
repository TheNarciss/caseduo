"""The night's generation by a Claude Code scheduled task, through GitHub (DEVIATIONS D13).

Nothing reaches the VM except GitHub Actions on its self-hosted runner, as
for Tangent and SingaSmoke:

1. `nightly-plan.yml` (00:40 Singapore, on the VM) runs `python -m app.nightly plan`
   and commits tomorrow's plan to the `nightly` branch: the system prompt and,
   per missing slot, the exact user message an API generation would send.
2. The Claude Code scheduled task (01:32, claude.ai) reads it, writes each
   exercise, checks it with `python -m app.nightly check` (generation/offline.py,
   no database), and pushes the files to `nightly`.
3. `nightly-import.yml` (every 10 minutes in the night, on the VM) runs
   `python -m app.nightly import`: validated again, inserted, logged in cron_runs.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import CronRun
from ..generation import request, schema, service
from ..generation.offline import check_item, spec_dict
from ..generation.planner import WEEKDAY_FR
from ..llm import prompts

JOB = "claude_code"


async def plan_payload(session: AsyncSession, day: date) -> dict[str, Any]:
    day_plan, ctx = await service.plan_for(session, day)
    missing = await service.missing_slots(session, day_plan)
    return {
        "date": day.isoformat(),
        "weekday": WEEKDAY_FR[day.weekday()],
        "sector": day_plan.sector,
        "system_prompt": prompts.load("generate"),
        "weaknesses": ctx.weakness_keys,
        "recent_titles": {t: [list(x) for x in v] for t, v in ctx.recent_titles.items()},
        "done": sorted(await service.existing_slots(session, day)),
        "slots": [
            {**spec_dict(s), "user_message": request.user_message(day_plan, s, ctx)}
            for s in missing
        ],
    }


async def _run(session: AsyncSession, day: date) -> CronRun:
    """One cron_runs row per night (job = claude_code), reused by every import of that night."""
    stmt = (
        select(CronRun)
        .where(CronRun.job == JOB, CronRun.target_date == day)
        .order_by(CronRun.started_at.desc())
        .limit(1)
    )
    run = (await session.execute(stmt)).scalar_one_or_none()
    if run is None:
        run = CronRun(job=JOB, target_date=day, status="running", model="claude-code", errors=[])
        session.add(run)
        await session.flush()
    return run


async def import_items(
    session: AsyncSession, day: date, items: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Validate and insert generated exercises. Idempotent: an existing slot is skipped."""
    day_plan, ctx = await service.plan_for(session, day)
    existing = await service.existing_slots(session, day)
    run = await _run(session, day)
    results: dict[str, str] = {}
    for slot, item in sorted(items.items()):
        spec = day_plan.slot(slot)
        if spec is None:
            results[slot] = "refusé : slot absent du plan du jour"
            continue
        if slot in existing:
            results[slot] = "déjà présent"
            continue
        try:
            fields = check_item(
                item,
                spec,
                weaknesses=ctx.weakness_keys,
                recent_titles=ctx.recent_titles.get(spec.type),
            )
        except schema.GenerationInvalid as exc:
            results[slot] = f"refusé : {exc}"
            run.errors = [*run.errors, {"slot": slot, "attempt": JOB, "error": str(exc)[:500]}]
            continue
        inserted = await service.insert_exercise(
            session, day, slot, fields, mode=JOB, run_id=run.id, model="claude-code"
        )
        run.n_succeeded += int(inserted)
        results[slot] = "inséré" if inserted else "déjà présent"
    missing = [s.slot for s in await service.missing_slots(session, day_plan)]
    run.n_requests = len(day_plan.slots)
    run.n_failed = len(missing)
    run.status = "ended" if not missing else ("partial" if run.n_succeeded else "failed")
    run.finished_at = datetime.now(UTC)
    await session.commit()
    return {"date": day.isoformat(), "results": results, "missing": missing, "status": run.status}
