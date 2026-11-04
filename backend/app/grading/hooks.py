"""Extension points around a grading: revenges, fit context, mocks, badges,
keeping grading/service.py stable."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Attempt, MockRun, Revenge
from ..errors import ConflictError, InvalidRequestError, NotFoundError
from ..game import revenge as revenge_rules
from ..services.clock import today_for
from ..services.fit import fit_context

if TYPE_CHECKING:
    from ..services.progress import ProgressResult
    from .service import Prepared


async def due_revenges(session: AsyncSession, p: Prepared) -> list[Revenge]:
    stmt = select(Revenge).where(
        Revenge.user_id == p.user.id,
        Revenge.exercise_id == p.exercise.id,
        Revenge.due_date <= today_for(p.user),
        Revenge.done_attempt_id.is_(None),
    )
    return list((await session.execute(stmt)).scalars().all())


async def before_grading(session: AsyncSession, p: Prepared) -> None:
    if p.body.mock_run_id is not None:
        run = await session.get(MockRun, p.body.mock_run_id)
        if run is None or run.user_id != p.user.id:
            raise NotFoundError("Mock introuvable.")
        if run.status != "in_progress":
            raise ConflictError("Ce mock est terminé.")
        if str(p.exercise.id) not in run.exercise_ids:
            raise InvalidRequestError("Cet exercice ne fait pas partie du mock.")
        p.mock_run = run
    if p.exercise.type == "cadrage_home" and p.body.kind == "main":
        slides = p.body.slides or []
        if len(slides) != 5 or any(not s.title.strip() for s in slides):
            raise InvalidRequestError(
                "Un cadrage à domicile se rend en 5 slides, chacune avec un titre-message."
            )
    if p.body.kind == "main" and not p.exercise.flagged:
        p.is_revenge = bool(await due_revenges(session, p))
    if p.exercise.type == "fit":
        p.fit_context = await fit_context(
            session, p.user.id, today_for(p.user), exclude_exercise=p.exercise.id
        )


async def after_grading(
    session: AsyncSession, p: Prepared, attempt: Attempt, result: ProgressResult
) -> None:
    if p.mock_run is not None:
        p.mock_run.attempt_ids = [*p.mock_run.attempt_ids, str(attempt.id)]
    if p.is_revenge:
        for revenge in await due_revenges(session, p):
            revenge.done_attempt_id = attempt.id
    if revenge_rules.needs_revenge(attempt.score, kind=attempt.kind, flagged=p.exercise.flagged):
        for step, due in revenge_rules.schedule(attempt.local_date):
            await session.execute(
                pg_insert(Revenge)
                .values(
                    user_id=p.user.id,
                    exercise_id=p.exercise.id,
                    source_attempt_id=attempt.id,
                    step=step,
                    due_date=due,
                )
                .on_conflict_do_nothing(constraint="uq_revenges_user_ex_step")
            )
