"""Which badges an event earns — pure. The catalogue lives in the badges table."""

from __future__ import annotations

from ..catalog import CASE_TYPES

STREAK_BADGES = ((3, "streak_3"), (7, "streak_7"), (10, "streak_10"), (30, "streak_30"))


def for_attempt(
    *,
    exercise_type: str,
    kind: str,
    score: int,
    is_revenge: bool,
    streak: int,
    perfect_week: bool,
    fit_answers: int,
) -> set[str]:
    codes = {code for n, code in STREAK_BADGES if streak >= n}
    is_case = exercise_type in (*CASE_TYPES, "tech_screen")
    if kind == "main" and is_case:
        codes.add("first_case")
        if score >= 90:
            codes.add("score_90")
    if kind == "main" and is_revenge and score >= 60:
        codes.add("revenge_won")
    if kind == "follow_up" and score >= 80:
        codes.add("follow_up_held")
    if kind == "main" and exercise_type == "cadrage_home":
        codes.add("cadrage_home_done")
    if fit_answers >= 10:
        codes.add("fit_10")
    if perfect_week:
        codes.add("perfect_week")
    return codes


def for_league(tier_after: str) -> set[str]:
    return {"silver": {"league_silver"}, "gold": {"league_silver", "league_gold"}}.get(
        tier_after, set()
    )
