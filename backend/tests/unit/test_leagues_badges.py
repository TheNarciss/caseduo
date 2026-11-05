from datetime import date

from app.game.badges import for_attempt, for_league
from app.game.leagues import (
    WEEKLY_RANGE,
    bot_xp,
    generate_bots,
    next_tier,
    outcome,
    standings,
)

WEEK = date(2026, 11, 2)


def test_bots_are_deterministic_named_and_realistic():
    a = generate_bots("user-1", WEEK, "bronze")
    assert a == generate_bots("user-1", WEEK, "bronze")
    assert a != generate_bots("user-1", date(2026, 11, 9), "bronze")
    assert len(a) == 5 and len({b["name"] for b in a}) == 5
    lo, hi = WEEKLY_RANGE["bronze"]
    for bot in a:
        assert len(bot["daily_xp"]) == 7 and all(x >= 0 and x % 5 == 0 for x in bot["daily_xp"])
        assert lo - 60 <= sum(bot["daily_xp"]) <= hi + 60
    gold = generate_bots("user-1", WEEK, "gold")
    assert sum(sum(b["daily_xp"]) for b in gold) > sum(sum(b["daily_xp"]) for b in a)


def test_bot_xp_grows_over_the_week():
    bot = {"name": "x", "daily_xp": [50, 50, 0, 100, 20, 0, 80]}
    assert bot_xp(bot, 0, 0.0) == 0
    assert bot_xp(bot, 0, 0.5) == 25
    assert bot_xp(bot, 3, 0.0) == 100
    assert bot_xp(bot, 7, 0.0) == 300


def test_standings_and_outcomes():
    bots = [
        {"name": n, "daily_xp": [x] * 7}
        for n, x in (("A", 50), ("B", 40), ("C", 30), ("D", 20), ("E", 10))
    ]
    ranking = standings("Moi", 210, bots, 7, 0.0)
    me = next(m for m in ranking if m.is_me)
    assert me.rank == 3 and [m.rank for m in ranking] == [1, 2, 3, 4, 5, 6]
    assert outcome(1, "bronze") == "promoted" and outcome(2, "silver") == "promoted"
    assert outcome(1, "gold") == "stayed"
    assert outcome(5, "silver") == "relegated" and outcome(6, "bronze") == "stayed"
    assert outcome(3, "silver") == "stayed"
    assert (
        next_tier("bronze", "promoted") == "silver" and next_tier("silver", "relegated") == "bronze"
    )


def test_badges_for_attempts():
    base = dict(
        exercise_type="cadrage",
        kind="main",
        score=70,
        is_revenge=False,
        streak=0,
        perfect_week=False,
        fit_answers=0,
    )
    assert for_attempt(**base) == {"first_case"}
    assert "score_90" in for_attempt(**{**base, "score": 92})
    assert "revenge_won" in for_attempt(**{**base, "is_revenge": True})
    assert for_attempt(**{**base, "streak": 10}) >= {"streak_3", "streak_7", "streak_10"}
    assert "follow_up_held" in for_attempt(**{**base, "kind": "follow_up", "score": 85})
    assert "cadrage_home_done" in for_attempt(**{**base, "exercise_type": "cadrage_home"})
    assert "fit_10" in for_attempt(**{**base, "exercise_type": "fit", "fit_answers": 10})
    assert for_league("gold") == {"league_silver", "league_gold"}
