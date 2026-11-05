"""XP rules, as specified — pure.

- 10 × difficulty per case (market sizing, cadrage, business case,
  diagnostic, tech screen), 5 × difficulty per brainteaser, 8 per fit
  question, 40 for a cadrage_home handed in
- × 1.5 if score ≥ 80, × 1.2 on a revenge, × 2 in the Sunday mock
- − 5 if context_data was revealed before answering
- + 10 for "redo in 2 minutes" if score ≥ 70, + 5 for a follow-up ≥ 60
  (× 2 as well inside a mock)
- + 20 once the whole day is done
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..catalog import CASE_TYPES

DAY_COMPLETE_BONUS = 20
REVEAL_PENALTY = 5
EASY_GOAL_XP = 30  # first week: 1 case + 1 brainteaser at difficulty 2


@dataclass
class XPResult:
    earned: int
    breakdown: list[dict] = field(default_factory=list)


def base_xp(exercise_type: str, difficulty: int) -> int:
    if exercise_type in CASE_TYPES or exercise_type == "tech_screen":
        return 10 * difficulty
    if exercise_type == "brainteaser":
        return 5 * difficulty
    if exercise_type == "fit":
        return 8
    if exercise_type == "cadrage_home":
        return 40
    return 0


def _fmt(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def attempt_xp(
    exercise_type: str,
    difficulty: int,
    kind: str,
    score: int,
    *,
    is_revenge: bool = False,
    is_mock: bool = False,
    revealed_before: bool = False,
) -> XPResult:
    lines: list[dict] = []
    if kind == "retry_2min":
        xp = 10.0 if score >= 70 else 0.0
        lines.append(
            {"label": "Refait en 2 min, score ≥ 70", "xp": int(xp)}
            if xp
            else {"label": "Refait en 2 min : score < 70", "xp": 0}
        )
    elif kind == "follow_up":
        xp = 5.0 if score >= 60 else 0.0
        lines.append(
            {"label": "Relance tenue, score ≥ 60", "xp": int(xp)}
            if xp
            else {"label": "Relance : score < 60", "xp": 0}
        )
    else:
        base = base_xp(exercise_type, difficulty)
        xp = float(base)
        label = {
            "brainteaser": f"5 × difficulté {difficulty}",
            "fit": "Question de fit",
            "cadrage_home": "Cadrage à domicile rendu",
        }.get(exercise_type, f"10 × difficulté {difficulty}")
        lines.append({"label": label, "xp": base})
        if score >= 80:
            lines.append({"label": "Score ≥ 80 : ×1,5", "xp": round(xp * 0.5)})
            xp *= 1.5
    if xp and is_revenge and kind == "main":
        lines.append({"label": "Revanche : ×1,2", "xp": round(xp * 0.2)})
        xp *= 1.2
    if xp and is_mock:
        lines.append({"label": "Mock entretien : ×2", "xp": round(xp)})
        xp *= 2
    total = round(xp)
    if revealed_before and kind == "main":
        penalty = min(REVEAL_PENALTY, total)
        if penalty:
            lines.append({"label": "Données demandées avant de répondre", "xp": -penalty})
        total -= penalty
    # keep the breakdown summing exactly to the total despite rounding
    drift = total - sum(line["xp"] for line in lines)
    if drift and lines:
        lines[-1]["xp"] += drift
    return XPResult(earned=max(0, total), breakdown=lines)


def effective_goal(daily_goal_xp: int, *, first_week: bool) -> int:
    """First week: the goal is reachable with 1 case + 1 brainteaser (easy wins)."""
    return min(daily_goal_xp, EASY_GOAL_XP) if first_week else daily_goal_xp


def multiplier_label(value: float) -> str:
    return f"×{_fmt(value)}"
