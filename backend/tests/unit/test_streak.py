"""Streak and freezes: consecutive days, missed days with/without freeze,
freeze earning, timezones and midnight, perfect week."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from app.game.streak import StreakState, close_missed_days, is_perfect_week, on_goal_met
from app.services.clock import today_for

D = date(2026, 11, 2)  # Monday


def day(n: int) -> date:
    return D + timedelta(days=n)


def test_consecutive_days_extend():
    s = StreakState()
    for i in range(3):
        s = close_missed_days(s, day(i)).state
        s = on_goal_met(s, day(i)).state
    assert (s.current, s.longest, s.last_date) == (3, 3, day(2))


def test_goal_met_twice_same_day_counts_once():
    s = on_goal_met(StreakState(), day(0)).state
    r = on_goal_met(s, day(0))
    assert r.state.current == 1 and not r.extended


def test_missed_day_without_freeze_resets():
    s = StreakState(current=5, longest=5, freezes=0, last_date=day(0))
    r = close_missed_days(s, day(2))  # day(1) missed
    assert r.broken and r.state.current == 0 and r.frozen_days == ()
    assert on_goal_met(r.state, day(2)).state.current == 1
    assert r.state.longest == 5


def test_missed_day_with_freeze_keeps_streak_without_adding():
    s = StreakState(current=5, longest=5, freezes=2, last_date=day(0))
    r = close_missed_days(s, day(2))
    assert not r.broken and r.frozen_days == (day(1),)
    assert r.state.current == 5 and r.state.freezes == 1 and r.state.last_date == day(1)
    assert on_goal_met(r.state, day(2)).state.current == 6


def test_two_missed_days_one_freeze_breaks():
    s = StreakState(current=4, freezes=1, last_date=day(0))
    r = close_missed_days(s, day(3))
    assert r.broken and r.frozen_days == (day(1),) and r.state.current == 0 and r.state.freezes == 0


def test_rollover_is_idempotent_and_ignores_today_and_yesterday():
    s = StreakState(current=2, freezes=2, last_date=day(0))
    assert close_missed_days(s, day(1)).state == s  # yesterday covered, today still open
    once = close_missed_days(s, day(3)).state
    assert close_missed_days(once, day(3)).state == once


def test_freeze_earned_every_seven_days_capped_at_three():
    s = StreakState(current=6, longest=6, freezes=2, last_date=day(0))
    r = on_goal_met(s, day(1))
    assert r.state.current == 7 and r.state.freezes == 3 and r.freeze_earned
    s = StreakState(current=13, longest=13, freezes=3, last_date=day(0))
    r = on_goal_met(s, day(1))
    assert r.state.freezes == 3 and not r.freeze_earned


def test_local_date_around_midnight_and_timezones():
    user_sg = SimpleNamespace(timezone="Asia/Singapore", created_at=None)
    user_paris = SimpleNamespace(timezone="Europe/Paris", created_at=None)
    just_before = datetime(2026, 11, 4, 15, 59, tzinfo=UTC)  # 23:59 in Singapore
    just_after = datetime(2026, 11, 4, 16, 1, tzinfo=UTC)  # 00:01 in Singapore
    assert today_for(user_sg, just_before) == date(2026, 11, 4)
    assert today_for(user_sg, just_after) == date(2026, 11, 5)
    assert today_for(user_paris, just_after) == date(2026, 11, 4)  # 17:01 in Paris
    bad = SimpleNamespace(timezone="Nowhere/Land", created_at=None)
    assert today_for(bad, just_after) == date(2026, 11, 5)  # falls back to Singapore


def test_answer_at_2359_then_0001_is_two_days():
    user = SimpleNamespace(timezone="Asia/Singapore", created_at=None)
    d1 = today_for(user, datetime(2026, 11, 4, 15, 59, tzinfo=UTC))
    d2 = today_for(user, datetime(2026, 11, 4, 16, 1, tzinfo=UTC))
    s = on_goal_met(StreakState(), d1).state
    s = close_missed_days(s, d2).state
    assert on_goal_met(s, d2).state.current == 2


def test_perfect_week():
    sunday = day(6)
    week = {day(i): (True, False) for i in range(7)}
    assert is_perfect_week(week, sunday)
    assert not is_perfect_week({**week, day(3): (True, True)}, sunday)  # a freeze
    assert not is_perfect_week({**week, day(2): (False, False)}, sunday)
    assert not is_perfect_week(week, day(5))  # only on Sunday
