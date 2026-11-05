"""JSON shapes of docs/API.md, in one place."""

from __future__ import annotations

from typing import Any

from ..catalog import TYPE_LABELS
from ..db.models import Attempt, Exercise


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def attempt_summary(a: Attempt, ex: Exercise) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "exercise_id": str(a.exercise_id),
        "kind": a.kind,
        "score": a.score,
        "xp_earned": a.xp_earned,
        "created_at": _iso(a.created_at),
        "title": ex.title,
        "type": ex.type,
        "type_label": TYPE_LABELS.get(ex.type, ex.type),
    }


def attempt_full(a: Attempt, ex: Exercise) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "exercise_id": str(a.exercise_id),
        "kind": a.kind,
        "parent_attempt_id": str(a.parent_attempt_id) if a.parent_attempt_id else None,
        "answer_text": a.answer_text,
        "duration_seconds": a.duration_seconds,
        "input_mode": a.input_mode,
        "score": a.score,
        "rubric_scores": a.rubric_scores,
        "feedback": a.feedback,
        "follow_up": a.follow_up,
        "xp_earned": a.xp_earned,
        "is_revenge": a.is_revenge,
        "revealed_data": a.revealed_data,
        "mock_run_id": str(a.mock_run_id) if a.mock_run_id else None,
        "created_at": _iso(a.created_at),
        "exercise": {
            "id": str(ex.id),
            "title": ex.title,
            "type": ex.type,
            "type_label": TYPE_LABELS.get(ex.type, ex.type),
            "language": ex.language,
            "model_answer": ex.model_answer,
            "sources": ex.sources,
            "rubric": ex.rubric,
            "flagged": ex.flagged,
        },
    }


def exercise_detail(
    ex: Exercise,
    attempts: list[Attempt],
    *,
    revealed: bool,
    is_revenge: bool = False,
) -> dict[str, Any]:
    has_main = any(a.kind == "main" for a in attempts)
    show_data = revealed or ex.style == "mbb" or has_main
    ctx = ex.context_data or {}
    available = bool(ctx.get("facts") or ctx.get("constraints") or ctx.get("documents"))
    return {
        "id": str(ex.id),
        "date": ex.date.isoformat(),
        "type": ex.type,
        "type_label": TYPE_LABELS.get(ex.type, ex.type),
        "style": ex.style,
        "language": ex.language,
        "difficulty": ex.difficulty,
        "sector": ex.sector,
        "title": ex.title,
        "prompt": ex.prompt,
        "estimated_minutes": ex.estimated_minutes,
        "parts": ex.parts,
        "context_data_available": available,
        "revealed": revealed,
        "context_data": ctx if show_data and available else None,
        "is_revenge": is_revenge,
        "flagged": ex.flagged,
        "attempts": [attempt_summary(a, ex) for a in attempts],
    }
