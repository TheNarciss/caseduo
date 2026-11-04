"""Grading one answer: checks before anything is spent, the streamed Claude call,
the server-side score, the attempt row, XP and progress.

`stream_grade` yields `(event, data)` pairs — `scores`, `feedback`,
`follow_up`, then `done` with the full result — consumed by the SSE route
as they come, or collected by `POST /grade`.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from anthropic import APIConnectionError, APIStatusError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import Attempt, Exercise, MockRun, Reveal
from ..errors import (
    BudgetExceededError,
    ConflictError,
    InvalidRequestError,
    LLMUnavailableError,
    NotFoundError,
)
from ..game.xp import attempt_xp
from ..llm import anthropic_client, cost_tracker, prompts
from ..llm.cost_tracker import usage_of
from ..services import progress
from ..services.clock import today_for
from . import hooks, prompt
from .parser import TaggedStreamParser
from .scoring import ScoresInvalid, parse_scores

logger = logging.getLogger(__name__)

MIN_ANSWER_CHARS = 10


class Slide(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    lines: list[str] = Field(default_factory=list, max_length=8)


class GradeRequest(BaseModel):
    exercise_id: uuid.UUID
    kind: Literal["main", "retry_2min", "follow_up"] = "main"
    answer_text: str = Field(default="", max_length=30_000)
    duration_seconds: int = Field(default=0, ge=0, le=6 * 3600)
    input_mode: Literal["text", "voice"] = "text"
    parent_attempt_id: uuid.UUID | None = None
    mock_run_id: uuid.UUID | None = None
    part_answers: list[str] | None = Field(default=None, max_length=10)
    slides: list[Slide] | None = Field(default=None, max_length=8)


@dataclass
class Prepared:
    user: User
    exercise: Exercise
    body: GradeRequest
    answer_text: str
    parent: Attempt | None = None
    revealed_before: bool = False
    is_revenge: bool = False
    mock_run: MockRun | None = None
    fit_context: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def compose_answer(ex: Exercise, body: GradeRequest) -> str:
    """The text the grader reads: slides and parts are laid out explicitly."""
    if body.slides:
        blocks = []
        for i, slide in enumerate(body.slides, 1):
            lines = "\n".join(f"- {line}" for line in slide.lines if line.strip())
            blocks.append(f"Slide {i} — {slide.title.strip()}\n{lines}")
        return "\n\n".join(blocks)
    if body.part_answers:
        parts = ex.parts or []
        blocks = []
        for i, answer in enumerate(body.part_answers):
            question = parts[i]["question"] if i < len(parts) else f"Partie {i + 1}"
            blocks.append(f"Partie {i + 1} — {question}\n{answer.strip()}")
        return "\n\n".join(blocks)
    return body.answer_text.strip()


async def prepare(session: AsyncSession, user: User, body: GradeRequest) -> Prepared:
    """Every check that can fail before any token is spent (proper HTTP errors)."""
    exercise = await session.get(Exercise, body.exercise_id)
    if exercise is None:
        raise NotFoundError("Exercice introuvable.")
    answer = compose_answer(exercise, body)
    if len(answer) < MIN_ANSWER_CHARS:
        raise InvalidRequestError("Réponse trop courte pour être notée.")

    parent = None
    if body.kind in ("retry_2min", "follow_up"):
        if body.parent_attempt_id is None:
            raise InvalidRequestError("parent_attempt_id manquant.")
        parent = await session.get(Attempt, body.parent_attempt_id)
        if parent is None or parent.user_id != user.id or parent.exercise_id != exercise.id:
            raise NotFoundError("Tentative d'origine introuvable.")
        if body.kind == "follow_up" and not (parent.follow_up or "").strip():
            raise ConflictError("Cette tentative n'a pas de relance.")
        if body.kind == "follow_up":
            stmt = select(Attempt.id).where(
                Attempt.parent_attempt_id == parent.id, Attempt.kind == "follow_up"
            )
            if (await session.execute(stmt)).first():
                raise ConflictError("Tu as déjà répondu à cette relance.")

    prepared = Prepared(user=user, exercise=exercise, body=body, answer_text=answer, parent=parent)

    if body.kind == "main" and exercise.style != "mbb":
        reveal = await session.get(Reveal, (user.id, exercise.id))
        if reveal is not None:
            stmt = select(Attempt.id).where(
                Attempt.user_id == user.id,
                Attempt.exercise_id == exercise.id,
                Attempt.kind == "main",
                Attempt.created_at < reveal.revealed_at,
            )
            prepared.revealed_before = (await session.execute(stmt)).first() is None

    await hooks.before_grading(session, prepared)

    if not await cost_tracker.is_under_cap(session):
        raise BudgetExceededError(
            "Le budget IA du jour est atteint : la notation reprend demain. Ta réponse n'est pas perdue."
        )
    try:
        anthropic_client.get_client()
    except RuntimeError as exc:
        raise LLMUnavailableError("La notation n'est pas configurée sur le serveur.") from exc
    return prepared


def _params(p: Prepared) -> dict[str, Any]:
    attempt_text = prompt.attempt_block(
        kind=p.body.kind,
        answer_text=p.answer_text,
        duration_seconds=p.body.duration_seconds,
        input_mode=p.body.input_mode,
        revealed_before=p.revealed_before,
        parent=p.parent,
        fit_context=p.fit_context,
        in_mock=p.mock_run is not None,
    )
    model = anthropic_client.MODEL
    return {
        "model": model,
        "max_tokens": anthropic_client.GRADING_MAX_TOKENS,
        "system": anthropic_client.cached_system(prompts.load("grade")),
        "messages": prompt.messages(p.exercise, attempt_text),
        **anthropic_client.reasoning_params(model, effort=anthropic_client.GRADING_EFFORT),
    }


async def stream_grade(
    session: AsyncSession, p: Prepared
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    client = anthropic_client.get_client()
    parser = TaggedStreamParser()
    rubric = p.exercise.rubric
    rubric_scores: list[dict[str, Any]] | None = None
    score = 0
    feedback_parts: list[str] = []
    follow_up = ""

    def handle(events) -> list[tuple[str, dict[str, Any]]]:
        nonlocal rubric_scores, score, follow_up
        out: list[tuple[str, dict[str, Any]]] = []
        for ev in events:
            if ev.kind == "scores" and rubric_scores is None:
                try:
                    rubric_scores, score = parse_scores(ev.text, rubric)
                except ScoresInvalid as exc:
                    logger.warning("Grader scores unreadable: %s", exc)
                    continue
                out.append(("scores", {"rubric_scores": rubric_scores, "score": score}))
            elif ev.kind == "feedback":
                feedback_parts.append(ev.text)
                out.append(("feedback", {"delta": ev.text}))
            elif ev.kind == "follow_up":
                follow_up = ev.text.strip()
                if follow_up:
                    out.append(("follow_up", {"text": follow_up}))
        return out

    try:
        async with client.messages.stream(**_params(p)) as stream:
            async for chunk in stream.text_stream:
                for item in handle(parser.feed(chunk)):
                    yield item
            final = await stream.get_final_message()
    except (APIStatusError, APIConnectionError) as exc:
        logger.warning("Grading API error: %s", exc)
        raise LLMUnavailableError("Claude est surchargé, réessaie dans une minute.") from exc
    for item in handle(parser.close()):
        yield item

    usage = usage_of(final)
    await cost_tracker.record_cost(session, usage.cost_usd, commit=False)
    if rubric_scores is None:
        await session.commit()
        raise LLMUnavailableError("La notation a échoué (réponse illisible). Réessaie.")

    body = p.body
    xp = attempt_xp(
        p.exercise.type,
        p.exercise.difficulty,
        body.kind,
        score,
        is_revenge=p.is_revenge,
        is_mock=p.mock_run is not None,
        revealed_before=p.revealed_before,
    )
    attempt = Attempt(
        id=uuid.uuid4(),
        user_id=p.user.id,
        exercise_id=p.exercise.id,
        kind=body.kind,
        parent_attempt_id=p.parent.id if p.parent else None,
        mock_run_id=p.mock_run.id if p.mock_run else None,
        answer_text=p.answer_text,
        duration_seconds=body.duration_seconds,
        input_mode=body.input_mode,
        revealed_data=p.revealed_before,
        is_revenge=p.is_revenge,
        score=score,
        rubric_scores=rubric_scores,
        feedback="".join(feedback_parts).strip(),
        follow_up=follow_up or None,
        xp_earned=xp.earned,
        local_date=today_for(p.user),
        model_used=next(iter(usage.models), anthropic_client.MODEL),
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=usage.cache_read_tokens,
        cache_write_tokens=usage.cache_write_tokens,
        cost_usd=round(usage.cost_usd, 6),
    )
    session.add(attempt)
    await session.flush()
    result = await progress.apply_attempt(session, p.user, attempt, p.exercise)
    await hooks.after_grading(session, p, attempt, result)
    await session.commit()
    logger.info(
        "Graded %s %s: score=%d xp=%d tokens=%d/%d cost=$%.4f",
        p.exercise.type,
        body.kind,
        score,
        xp.earned,
        usage.input_tokens + usage.cache_read_tokens,
        usage.output_tokens,
        usage.cost_usd,
    )
    from ..routers.serializers import attempt_full  # avoid an import cycle

    yield (
        "done",
        {
            "attempt": attempt_full(attempt, p.exercise),
            "xp": {"earned": xp.earned, "breakdown": xp.breakdown},
            "progress": result.as_dict(),
        },
    )


async def grade(session: AsyncSession, p: Prepared) -> dict[str, Any]:
    done: dict[str, Any] | None = None
    async for kind, data in stream_grade(session, p):
        if kind == "done":
            done = data
    assert done is not None
    return done
