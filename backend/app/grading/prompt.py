"""The grader's user message: a cached block with the exercise, then the attempt.

Block 1 (exercise: statement, data, model answer, rubric) is identical for
the main answer, the follow-up and the 2-minute redo of the same exercise:
it carries a cache breakpoint, so the second and third gradings of an
exercise read it from the cache.
"""

from __future__ import annotations

from typing import Any

from ..catalog import TYPE_LABELS
from ..db.models import Attempt, Exercise

KIND_LABELS = {
    "main": "main (première réponse)",
    "retry_2min": "retry_2min (refait en 2 minutes à l'oral après la correction)",
    "follow_up": "follow_up (réponse à la relance)",
}


def exercise_block(ex: Exercise) -> str:
    lines = [
        "## Exercice",
        f"Type : {ex.type} ({TYPE_LABELS.get(ex.type, ex.type)}) · style {ex.style} · "
        f"langue {ex.language} · difficulté {ex.difficulty}/5 · secteur {ex.sector}",
        f"Titre : {ex.title}",
        "",
        "### Énoncé",
        ex.prompt,
    ]
    if ex.parts:
        lines += ["", "### Parties (posées une à une)"]
        for i, part in enumerate(ex.parts, 1):
            data = f" — données : {part.get('data')}" if part.get("data") else ""
            lines.append(f"{i}. {part.get('question')}{data}")
    ctx = ex.context_data or {}
    facts = ctx.get("facts") or []
    if facts or ctx.get("constraints") or ctx.get("documents"):
        lines += ["", "### context_data"]
        for f in facts:
            origin = f.get("source_url") or "hypothèse"
            lines.append(f"- {f.get('label')} : {f.get('value')} ({origin})")
        for c in ctx.get("constraints") or []:
            lines.append(f"- Contrainte : {c}")
        for d in ctx.get("documents") or []:
            lines += [f"#### Document : {d.get('title')}", str(d.get("body"))]
    lines += ["", "### model_answer", ex.model_answer, "", "### Rubric"]
    for c in ex.rubric:
        levels = c.get("levels") or {}
        lines.append(
            f"- `{c['key']}` ({c.get('label')}), poids {c['weight']} : "
            f"0 = {levels.get('0')} ; 1 = {levels.get('1')} ; 2 = {levels.get('2')}"
        )
    return "\n".join(lines)


def attempt_block(
    *,
    kind: str,
    answer_text: str,
    duration_seconds: int,
    input_mode: str,
    revealed_before: bool,
    parent: Attempt | None,
    fit_context: str | None = None,
    in_mock: bool = False,
) -> str:
    mode = "oral (transcription automatique)" if input_mode == "voice" else "texte"
    lines = [
        "## Tentative",
        f"kind : {KIND_LABELS.get(kind, kind)}",
        f"Durée : {duration_seconds} s · Mode : {mode} · "
        f"Données demandées avant de répondre : {'oui' if revealed_before else 'non'}",
    ]
    if in_mock:
        lines.append("Contexte : mock entretien (feedback montré à la fin du mock).")
    if parent is not None and kind == "retry_2min":
        lines += ["", f"### Première tentative (score {parent.score}/100)", parent.answer_text]
    if parent is not None and kind == "follow_up":
        lines += [
            "",
            "### Première réponse du candidat",
            parent.answer_text,
            "",
            "### Relance posée par l'interviewer",
            parent.follow_up or "",
        ]
    if fit_context:
        lines += ["", fit_context]
    lines += ["", "### Réponse du candidat", answer_text.strip() or "(vide)"]
    return "\n".join(lines)


def messages(ex: Exercise, attempt_text: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": exercise_block(ex),
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": attempt_text},
            ],
        }
    ]


def as_text(ex: Exercise, attempt_text: str) -> str:
    """The same message as one text, for Claude Code (which caches on its own)."""
    return exercise_block(ex) + "\n\n" + attempt_text
