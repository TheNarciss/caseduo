"""The day plan follows the spec, rule by rule."""

from datetime import date, timedelta

from app.generation.planner import (
    is_english,
    mock_is_mbb,
    mock_kind,
    mock_language,
    plan_day,
)

MON = date(2026, 11, 2)  # a Monday (ISO week 45)


def days_of_week(start: date = MON):
    return [start + timedelta(days=i) for i in range(7)]


def test_every_day_has_five_cases_one_fit_and_brainteasers():
    for day in days_of_week():
        plan = plan_day(day)
        cases = [s for s in plan.slots if s.slot.startswith("case_")]
        assert len(cases) == 5
        assert {s.type for s in cases[:4]} == {
            "market_sizing",
            "cadrage",
            "business_case",
            "diagnostic",
        }
        assert len([s for s in plan.slots if s.slot == "fit"]) == 1
        n_bt = len([s for s in plan.slots if s.type == "brainteaser"])
        assert n_bt == (3 if day.weekday() >= 5 else 2)


def test_difficulty_bands():
    expected = {0: (2, 3), 1: (2, 3), 2: (3, 4), 3: (3, 4), 4: (4, 5), 5: (1, 2), 6: (1, 2)}
    for day in days_of_week():
        lo, hi = expected[day.weekday()]
        for s in plan_day(day).slots:
            if s.is_mock or s.slot == "case_extra":
                continue
            assert lo <= s.difficulty <= hi, (day, s.slot, s.difficulty)
        extra = plan_day(day).slot("case_extra")
        assert extra.difficulty == min(5, hi + 1)


def test_easy_mode_caps_difficulty_at_two():
    for day in days_of_week():
        assert max(s.difficulty for s in plan_day(day, easy_mode=True).slots) <= 2


def test_tuesday_has_an_industry_defence_case():
    tuesday = MON + timedelta(days=1)
    plan = plan_day(tuesday)
    assert plan.sector == "industrie/défense"
    assert plan.slot("case_cadrage").sector == "industrie/défense"


def test_friday_adds_cadrage_home_and_thursday_tech_screen():
    assert plan_day(MON + timedelta(days=4)).slot("cadrage_home").type == "cadrage_home"
    assert plan_day(MON + timedelta(days=3)).slot("case_extra").type == "tech_screen"
    for i in (0, 1, 2, 5, 6):
        assert plan_day(MON + timedelta(days=i)).slot("cadrage_home") is None
    techs = [s for d in days_of_week() for s in plan_day(d).slots if s.type == "tech_screen"]
    assert len(techs) == 1  # once a week


def test_one_mbb_case_wednesday_to_friday_only():
    for day in days_of_week():
        mbb = [s for s in plan_day(day).slots if s.style == "mbb" and not s.is_mock]
        assert len(mbb) == (1 if day.weekday() in (2, 3, 4) else 0)


def test_sunday_mock_and_saturday_fit_mock():
    sunday = MON + timedelta(days=6)
    slots = {s.slot for s in plan_day(sunday).slots}
    if mock_is_mbb(sunday):
        assert {"mock_pei", "mock_case_mbb"} <= slots
    else:
        assert {"mock_fit", "mock_market_sizing", "mock_cadrage"} <= slots
    assert mock_kind(sunday) == "full"
    saturday = MON + timedelta(days=5)
    assert mock_kind(saturday) == ("fit" if saturday.isocalendar()[1] % 2 == 0 else None)


def test_mbb_mock_one_sunday_in_four_with_four_parts():
    sundays = [date(2026, 1, 4) + timedelta(weeks=i) for i in range(16)]
    mbb = [d for d in sundays if mock_is_mbb(d)]
    assert len(mbb) == 4
    for d in mbb:
        case = plan_day(d).slot("mock_case_mbb")
        assert case.parts == 4 and case.style == "mbb"
    assert {mock_language(d) for d in mbb} == {"fr", "en"}


def test_about_thirty_percent_english():
    year = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]
    flags = [is_english(d, s.slot) for d in year for s in plan_day(d).slots if not s.is_mock]
    share = sum(flags) / len(flags)
    assert 0.25 < share < 0.35


def test_two_cases_target_weaknesses_when_known():
    for day in days_of_week():
        assert not any(s.target_weakness for s in plan_day(day).slots)
        targeted = [s for s in plan_day(day, has_weaknesses=True).slots if s.target_weakness]
        assert len(targeted) == 2


def test_web_search_only_for_cases():
    for s in plan_day(MON + timedelta(days=4)).slots:
        assert s.web_search == (
            s.type in {"market_sizing", "cadrage", "business_case", "diagnostic", "cadrage_home"}
        )
