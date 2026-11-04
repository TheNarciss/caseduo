"""The chained mock interviews.

- Sunday `full`: 1 fit, 1 market sizing, 1 cadrage, 2 follow-ups, oral only,
  no going back, 30 min, XP × 2. One Sunday in four in MBB style: 1 PEI
  (with its follow-up) and a 25-minute interviewer-led case in 4 parts, the
  last one the 30-second synthesis — in English one time in two.
- Saturday of even weeks `fit`: 6 fit questions in a row, 15 min.
The global score compares with the previous mocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import Attempt, Exercise, MockRun
from ..errors import ConflictError, NotFoundError
from ..generation.planner import mock_is_mbb, mock_kind, mock_language


@dataclass(frozen=True)
class StepPlan:
    slot: str
    seconds: int
    follow_up_after: bool


PLANS: dict[str, tuple[StepPlan, ...]] = {
    "full": (
        StepPlan("mock_fit", 300, False),
        StepPlan("mock_market_sizing", 480, True),
        StepPlan("mock_cadrage", 600, True),
    ),
    "full_mbb": (
        StepPlan("mock_pei", 300, True),
        StepPlan("mock_case_mbb", 1500, False),
    ),
    "fit": (StepPlan("mock_fit_set", 900, False),),
}
TIME_LIMITS = {"full": 1800, "full_mbb": 1800, "fit": 900}
PREVIOUS_SHOWN = 10


def plan_key(kind: str, day: date) -> str:
    return "full_mbb" if kind == "full" and mock_is_mbb(day) else kind


async def _exercises(session: AsyncSession, day: date, key: str) -> list[Exercise]:
    slots = [s.slot for s in PLANS[key]]
    rows = (
        await session.execute(
            select(Exercise).where(Exercise.date == day, Exercise.slot.in_(slots))
        )
    ).scalars()
    by_slot = {e.slot: e for e in rows}
    if len(by_slot) != len(slots):
        raise ConflictError("Le mock du jour n'est pas encore prêt. Réessaie dans un moment.")
    return [by_slot[s] for s in slots]


def run_view(run: MockRun, exercises: list[Exercise]) -> dict[str, Any]:
    key = "full_mbb" if run.mbb else run.kind
    steps = []
    for i, (plan, ex) in enumerate(zip(PLANS[key], exercises, strict=True)):
        steps.append(
            {
                "index": i,
                "exercise_id": str(ex.id),
                "type": ex.type,
                "title": ex.title,
                "prompt": ex.prompt,
                "parts": ex.parts,
                "context_data": ex.context_data if ex.style == "mbb" else None,
                "time_limit_seconds": plan.seconds,
                "follow_up_after": plan.follow_up_after,
            }
        )
    return {
        "id": str(run.id),
        "kind": run.kind,
        "mbb": run.mbb,
        "language": run.language,
        "status": run.status,
        "time_limit_seconds": TIME_LIMITS[key],
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "steps": steps,
    }


async def start(session: AsyncSession, user: User, kind: str, day: date) -> dict[str, Any]:
    if mock_kind(day) != kind:
        raise ConflictError("Pas de mock de ce type aujourd'hui.")
    key = plan_key(kind, day)
    exercises = await _exercises(session, day, key)
    run = (
        await session.execute(
            select(MockRun).where(
                MockRun.user_id == user.id, MockRun.date == day, MockRun.kind == kind
            )
        )
    ).scalar_one_or_none()
    if run is not None and run.status == "finished":
        raise ConflictError("Tu as déjà fait le mock du jour.")
    if run is None:
        run = MockRun(
            user_id=user.id,
            date=day,
            kind=kind,
            mbb=key == "full_mbb",
            language=mock_language(day) if kind == "full" else "fr",
            exercise_ids=[str(e.id) for e in exercises],
            attempt_ids=[],
        )
        session.add(run)
        await session.commit()
    return run_view(run, exercises)


async def get(session: AsyncSession, user: User, run_id) -> tuple[MockRun, list[Exercise]]:
    run = await session.get(MockRun, run_id)
    if run is None or run.user_id != user.id:
        raise NotFoundError("Mock introuvable.")
    ids = list(run.exercise_ids)
    rows = (await session.execute(select(Exercise).where(Exercise.id.in_(ids)))).scalars()
    by_id = {str(e.id): e for e in rows}
    return run, [by_id[i] for i in ids if i in by_id]


def global_score(main_scores: list[int], follow_up_scores: list[int], n_steps: int) -> int:
    """Average of the steps (an unanswered step counts 0), follow-ups weigh 20 %."""
    mains = main_scores + [0] * max(0, n_steps - len(main_scores))
    base = sum(mains) / len(mains) if mains else 0
    if follow_up_scores:
        base = base * 0.8 + sum(follow_up_scores) / len(follow_up_scores) * 0.2
    return round(base)


async def finish(session: AsyncSession, user: User, run_id) -> dict[str, Any]:
    run, exercises = await get(session, user, run_id)
    if run.status == "finished":
        raise ConflictError("Ce mock est déjà terminé.")
    attempts = list(
        (
            await session.execute(
                select(Attempt).where(Attempt.mock_run_id == run.id).order_by(Attempt.created_at)
            )
        ).scalars()
    )
    by_ex = {e.id: e for e in exercises}
    mains = [a for a in attempts if a.kind == "main"]
    follow_ups = [a for a in attempts if a.kind == "follow_up"]
    run.score = global_score(
        [a.score for a in mains], [a.score for a in follow_ups], len(exercises)
    )
    run.xp_earned = sum(a.xp_earned for a in attempts)
    run.attempt_ids = [str(a.id) for a in attempts]
    run.status = "finished"
    run.finished_at = datetime.now(UTC)
    blocks = []
    for a in mains:
        ex = by_ex.get(a.exercise_id)
        blocks.append(f"### {ex.title if ex else 'Question'} — {a.score}/100\n\n{a.feedback}")
    for a in follow_ups:
        blocks.append(f"### Relance — {a.score}/100\n\n{a.feedback}")
    run.feedback = "\n\n".join(blocks) or "Aucune réponse enregistrée."
    previous = (
        await session.execute(
            select(MockRun)
            .where(
                MockRun.user_id == user.id,
                MockRun.kind == run.kind,
                MockRun.status == "finished",
                MockRun.id != run.id,
            )
            .order_by(MockRun.date.desc())
            .limit(PREVIOUS_SHOWN)
        )
    ).scalars()
    from ..routers.serializers import attempt_summary

    result = {
        "id": str(run.id),
        "score": run.score,
        "xp_earned": run.xp_earned,
        "attempts": [
            attempt_summary(a, by_ex[a.exercise_id]) for a in attempts if a.exercise_id in by_ex
        ],
        "previous": [
            {"date": m.date.isoformat(), "kind": m.kind, "score": m.score} for m in previous
        ],
        "feedback": run.feedback,
    }
    from ..grading import badges_hook

    await badges_hook.after_mock(session, user, run)
    await session.commit()
    return result
