"""Streak through the API: goal met by grading, freeze applied on a missed day,
"freeze used" shown once, widget, day summary, push token."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.auth import User
from app.db.models import DailyActivity
from app.generation import service as gen_service
from app.llm import anthropic_client
from app.services.clock import today_for
from tests.fake_llm import FakeClient, attach_grader, grade_text

pytestmark = pytest.mark.integration


@pytest.fixture
def grader():
    client = FakeClient()

    def text_for(params):
        user_text = params["messages"][0]["content"][0]["text"]
        keys = [line.split("`")[1] for line in user_text.splitlines() if line.startswith("- `")]
        return grade_text(keys, [2] * len(keys))

    attach_grader(client, text_for)
    anthropic_client.set_client_for_testing(client)
    yield client
    anthropic_client.set_client_for_testing(None)


async def test_goal_met_extends_streak_then_freeze_bridges_a_missed_day(user_client, db, grader):
    client, user = user_client
    day = today_for(user)
    await gen_service.insert_starter_pack(db, day)
    cards = (await client.get("/api/today")).json()["cards"]
    case = next(c for c in cards if c["type"] == "cadrage")  # 30 × 1.5 = 45 ≥ 30 (first week)
    res = (
        await client.post(
            "/api/grade",
            json={
                "exercise_id": case["exercise_id"],
                "answer_text": "Réponse structurée en trois axes.",
            },
        )
    ).json()
    assert res["progress"]["goal_just_met"] and res["progress"]["streak_extended"]
    assert res["progress"]["streak"]["current"] == 1
    assert res["progress"]["streak"]["status"] == "extended_today"

    # Pretend the last covered day was 3 days ago with a streak of 5: one freeze per missed day.
    row = await db.get(User, user.id)
    row.streak_current, row.streak_last_date, row.streak_freezes = 5, day - timedelta(days=3), 2
    await db.commit()
    today = (await client.get("/api/today")).json()
    assert today["streak"]["current"] == 5 and today["streak"]["freezes"] == 0
    assert today["streak"]["freeze_just_used"] is True
    assert len(today["streak"]["freeze_used_on"]) == 2
    again = (await client.get("/api/today")).json()
    assert again["streak"]["freeze_just_used"] is False  # shown once
    frozen = (
        (await db.execute(select(DailyActivity).where(DailyActivity.freeze_used.is_(True))))
        .scalars()
        .all()
    )
    assert len(frozen) == 2


async def test_missed_days_without_freeze_reset(user_client, db):
    client, user = user_client
    row = await db.get(User, user.id)
    row.streak_current, row.streak_last_date, row.streak_freezes = (
        9,
        today_for(user) - timedelta(days=3),
        0,
    )
    await db.commit()
    body = (await client.get("/api/today")).json()
    assert (body["streak"]["current"] == 0 and body["streak"]["longest"] == 0) or body["streak"][
        "current"
    ] == 0


async def test_widget_summary_and_push_token(user_client, db, grader):
    client, user = user_client
    await gen_service.insert_starter_pack(db, today_for(user))
    widget = (await client.get("/api/widget")).json()
    assert widget["remaining"] == 7 and widget["streak"] == 0 and widget["goal_xp"] == 30
    cards = (await client.get("/api/today")).json()["cards"]
    await client.post(
        "/api/grade",
        json={
            "exercise_id": cards[2]["exercise_id"],
            "answer_text": "Réponse structurée en trois axes.",
        },
    )
    summary = (await client.get("/api/day/summary")).json()
    assert summary["exercises_done"] == 1 and summary["line"]
    assert (await client.get("/api/widget")).json()["remaining"] == 6
    token = "a" * 64
    assert (
        await client.post("/api/me/push-token", json={"token": token, "environment": "sandbox"})
    ).status_code == 204
    stored = await db.get(User, user.id, populate_existing=True)
    assert stored.apns_token == token and stored.apns_environment == "sandbox"
    assert (await client.post("/api/me/push-token", json={"token": "nothex!"})).status_code == 422
