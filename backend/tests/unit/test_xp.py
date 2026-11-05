"""XP rules from the spec."""

from app.game.xp import attempt_xp, base_xp, effective_goal


def test_base_xp_per_type():
    assert base_xp("market_sizing", 3) == 30
    assert base_xp("tech_screen", 4) == 40
    assert base_xp("brainteaser", 3) == 15
    assert base_xp("fit", 5) == 8
    assert base_xp("cadrage_home", 5) == 40


def test_high_score_multiplier():
    assert attempt_xp("cadrage", 3, "main", 79).earned == 30
    assert attempt_xp("cadrage", 3, "main", 80).earned == 45


def test_revenge_mock_and_reveal():
    assert attempt_xp("cadrage", 3, "main", 50, is_revenge=True).earned == 36
    assert attempt_xp("cadrage", 3, "main", 85, is_revenge=True).earned == 54  # 30 × 1.5 × 1.2
    assert attempt_xp("market_sizing", 3, "main", 50, is_mock=True).earned == 60
    assert attempt_xp("cadrage", 3, "main", 50, revealed_before=True).earned == 25
    assert attempt_xp("fit", 1, "main", 10, revealed_before=True).earned == 3


def test_retry_and_follow_up_bonuses():
    assert attempt_xp("cadrage", 3, "retry_2min", 70).earned == 10
    assert attempt_xp("cadrage", 3, "retry_2min", 69).earned == 0
    assert attempt_xp("cadrage", 3, "follow_up", 60).earned == 5
    assert attempt_xp("cadrage", 3, "follow_up", 59).earned == 0
    assert attempt_xp("cadrage", 3, "follow_up", 60, is_mock=True).earned == 10
    # revenge multiplier only applies to the main answer
    assert attempt_xp("cadrage", 3, "follow_up", 60, is_revenge=True).earned == 5


def test_breakdown_sums_to_total():
    for kw in ({}, {"is_revenge": True}, {"is_mock": True}, {"revealed_before": True}):
        r = attempt_xp("business_case", 4, "main", 83, **kw)
        assert sum(line["xp"] for line in r.breakdown) == r.earned


def test_first_week_goal_is_one_case_plus_one_brainteaser():
    assert effective_goal(50, first_week=True) == 30
    assert effective_goal(80, first_week=False) == 80
    assert base_xp("cadrage", 2) + base_xp("brainteaser", 2) >= effective_goal(50, first_week=True)
