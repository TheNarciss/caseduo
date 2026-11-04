"""Turning the grader's per-criterion marks into the final score — server side.

The model's own total is ignored (DEVIATIONS D12): score = Σ(mark / 2 ×
weight), rounded. A criterion the model skipped counts 0 and says so.
"""

from __future__ import annotations

import json
from typing import Any

from ..catalog import criterion_label


class ScoresInvalid(ValueError):
    pass


def parse_scores(raw: str, rubric: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """(rubric_scores, score) from the `<scores>` JSON, aligned on the exercise rubric."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScoresInvalid(f"JSON des notes invalide : {exc}") from exc
    items = data.get("rubric_scores") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ScoresInvalid("rubric_scores absent")
    by_key = {str(i.get("key")): i for i in items if isinstance(i, dict)}
    if not by_key:
        raise ScoresInvalid("aucune note")

    scores: list[dict[str, Any]] = []
    for criterion in rubric:
        key = criterion["key"]
        item = by_key.get(key, {})
        try:
            mark = int(item.get("score", 0))
        except (TypeError, ValueError):
            mark = 0
        mark = min(2, max(0, mark))
        scores.append(
            {
                "key": key,
                "label": criterion.get("label") or criterion_label(key),
                "weight": int(criterion["weight"]),
                "score": mark,
                "justification": str(item.get("justification") or "Critère non évalué.")[:500],
                "quote": str(item.get("quote") or "")[:200],
            }
        )
    return scores, weighted_score(scores)


def weighted_score(scores: list[dict[str, Any]]) -> int:
    total_weight = sum(s["weight"] for s in scores) or 100
    raw = sum(s["score"] / 2 * s["weight"] for s in scores) * 100 / total_weight
    return round(raw)
