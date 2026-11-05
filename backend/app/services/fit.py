"""What the grader needs for a fit answer: the career story and the fit answers
of the last 30 days, to catch contradictions between days."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Attempt, Exercise, UserStory

FIT_HISTORY_DAYS = 30
FIT_HISTORY_MAX = 12
ANSWER_CHARS = 700


async def fit_context(
    session: AsyncSession, user_id: uuid.UUID, today: date, *, exclude_exercise: uuid.UUID
) -> str:
    story = await session.get(UserStory, user_id)
    lines = ["### Récit de parcours du candidat"]
    lines.append(
        story.story_text.strip() if story and story.story_text.strip() else "(non renseigné)"
    )
    rows = (
        await session.execute(
            select(Attempt, Exercise)
            .join(Exercise, Exercise.id == Attempt.exercise_id)
            .where(
                Attempt.user_id == user_id,
                Attempt.kind == "main",
                Exercise.type == "fit",
                Exercise.id != exclude_exercise,
                Attempt.local_date >= today - timedelta(days=FIT_HISTORY_DAYS),
            )
            .order_by(Attempt.created_at.desc())
            .limit(FIT_HISTORY_MAX)
        )
    ).all()
    lines += ["", f"### Réponses de fit des {FIT_HISTORY_DAYS} derniers jours"]
    if not rows:
        lines.append("(aucune)")
    for attempt, ex in reversed(rows):
        answer = attempt.answer_text.strip().replace("\n", " ")
        if len(answer) > ANSWER_CHARS:
            answer = answer[:ANSWER_CHARS] + "…"
        lines.append(f"- {attempt.local_date.isoformat()} — « {ex.title} » : {answer}")
    return "\n".join(lines)
