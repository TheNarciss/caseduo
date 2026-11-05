"""Recurring weaknesses, computed from `attempts.rubric_scores`.

Each graded attempt carries one score (0, 1 or 2) per rubric criterion, with
a canonical key (catalog.CRITERIA). A weakness is a criterion whose average
is low; ties go to the criterion seen most often (more evidence).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..catalog import CRITERIA, criterion_label


@dataclass(frozen=True)
class CriterionStat:
    key: str
    label: str
    average: float  # on the rubric scale, 0 to 2
    count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "average": round(self.average, 2),
            "count": self.count,
        }


def criteria_stats(rubric_score_lists: Iterable[list[dict[str, Any]]]) -> list[CriterionStat]:
    """Average score per criterion, weakest first."""
    totals: dict[str, list[int]] = {}
    for scores in rubric_score_lists:
        for item in scores or []:
            key = item.get("key")
            value = item.get("score")
            if key not in CRITERIA or not isinstance(value, int | float):
                continue
            totals.setdefault(key, []).append(int(value))
    stats = [
        CriterionStat(key=k, label=criterion_label(k), average=sum(v) / len(v), count=len(v))
        for k, v in totals.items()
        if v
    ]
    return sorted(stats, key=lambda s: (s.average, -s.count, s.key))


def weakest_criteria(
    rubric_score_lists: Iterable[list[dict[str, Any]]], n: int = 3
) -> list[CriterionStat]:
    """The n weakest criteria. Only criteria below the top mark count as weak."""
    return [s for s in criteria_stats(rubric_score_lists) if s.average < 2][:n]
