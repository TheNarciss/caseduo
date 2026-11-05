from datetime import date

from app.game.revenge import needs_revenge, schedule


def test_revenge_after_a_score_under_60_on_a_main_answer():
    assert needs_revenge(59, kind="main", flagged=False)
    assert not needs_revenge(60, kind="main", flagged=False)
    assert not needs_revenge(30, kind="follow_up", flagged=False)
    assert not needs_revenge(30, kind="retry_2min", flagged=False)
    assert not needs_revenge(30, kind="main", flagged=True)  # a flagged correction never comes back


def test_revenge_dates_three_then_ten_days_later():
    assert schedule(date(2026, 11, 28)) == [(1, date(2026, 12, 1)), (2, date(2026, 12, 8))]
