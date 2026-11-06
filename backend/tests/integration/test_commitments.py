"""« Je m'engage » holds for a period (DEVIATIONS D16): locked goal, day-by-day tracking,
the badge of a kept commitment, the Entraîner tab apart."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.content.starter_pack import exercises as starter
from app.db.models import DailyActivity, GoalCommitment, UserBadge
from app.generation import service as gen_service
from app.services import commitments
from app.services.clock import today_for
from tests.integration.test_grading import grader, seed_today  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration


async def test_commitment_locks_the_goal_and_tracks_days(user_client, db, grader):  # noqa: F811
    client, user = user_client
    day = today_for(user)
    assert (await client.get("/api/me")).json()["commitment"] is None

    resp = await client.post("/api/me/commitment", json={"daily_xp": 30, "days": 7})
    assert resp.status_code == 200, resp.text
    me = resp.json()
    assert me["daily_goal_xp"] == 30
    c = me["commitment"]
    assert c["status"] == "active" and c["day_index"] == 1 and c["days"] == 7
    assert c["end_date"] == (day + timedelta(days=6)).isoformat()
    assert [d["state"] for d in c["calendar"]] == ["today"] + ["future"] * 6
    assert c["on_track"] and c["kept"] is None

    assert (
        await client.post("/api/me/commitment", json={"daily_xp": 50, "days": 7})
    ).status_code == 409
    resp = await client.patch("/api/me", json={"daily_goal_xp": 80})
    assert resp.status_code == 409 and "engagement" in resp.json()["detail"].lower()
    assert (await client.patch("/api/me", json={"sounds_enabled": False})).status_code == 200

    # The goal met today: the first day is kept, on the day screen too.
    ex = (await seed_today(db, user))["starter_cadrage"]
    resp = await client.post(
        "/api/grade",
        json={"exercise_id": str(ex.id), "answer_text": "Je reformule puis trois axes."},
    )
    assert resp.status_code == 200 and resp.json()["progress"]["goal_met"]
    today = (await client.get("/api/today")).json()
    assert today["commitment"]["days_met"] == 1
    assert today["commitment"]["calendar"][0]["state"] == "met"
    assert (await client.patch("/api/me", json={"daily_goal_xp": 45})).status_code == 422
    assert (
        await client.post("/api/me/commitment", json={"daily_xp": 50, "days": 5})
    ).status_code == 422


async def _ended(db, user, day, *, states):
    """A 7-day commitment that ended yesterday, with one DailyActivity row per state."""
    start = day - timedelta(days=7)
    db.add(
        GoalCommitment(
            id=uuid.uuid4(),
            user_id=user.id,
            daily_xp=30,
            days=7,
            start_date=start,
            end_date=start + timedelta(days=6),
        )
    )
    for i, state in enumerate(states):
        if state == "none":
            continue
        db.add(
            DailyActivity(
                user_id=user.id,
                date=start + timedelta(days=i),
                xp_earned=30,
                goal_met=state == "met",
                freeze_used=state == "frozen",
            )
        )
    await db.commit()


async def test_kept_commitment_earns_the_badge_once(user_client, db):
    client, user = user_client
    day = today_for(user)
    await _ended(db, user, day, states=["met"] * 5 + ["frozen", "met"])
    today = (await client.get("/api/today")).json()
    c = today["commitment"]
    assert c["status"] == "ended" and c["kept"] is True and c["badge_awarded"] is True
    assert (c["days_met"], c["days_frozen"], c["days_missed"], c["day_index"]) == (6, 1, 0, 7)
    badges = {b["code"]: b for b in (await client.get("/api/badges")).json()}
    assert badges["commitment_kept"]["earned_at"]
    await client.get("/api/today")
    rows = (
        await db.execute(select(UserBadge).where(UserBadge.badge_code == "commitment_kept"))
    ).all()
    assert len(rows) == 1

    # A new commitment can start right away; the summary of the old one is gone from the day.
    resp = await client.post("/api/me/commitment", json={"daily_xp": 80, "days": 30})
    assert resp.status_code == 200 and resp.json()["commitment"]["status"] == "active"


async def test_broken_commitment_has_no_badge_and_fades_after_a_week(user_client, db):
    client, user = user_client
    day = today_for(user)
    await _ended(db, user, day, states=["met", "none", "met", "met", "met", "met", "met"])
    c = (await client.get("/api/today")).json()["commitment"]
    assert c["status"] == "ended" and c["kept"] is False and c["days_missed"] == 1
    assert c["calendar"][1]["state"] == "missed" and not c["badge_awarded"]
    assert (await client.get("/api/badges")).json()
    assert not any(
        b["code"] == "commitment_kept" and b["earned_at"]
        for b in (await client.get("/api/badges")).json()
    )
    assert await commitments.for_screen(db, user, day + timedelta(days=6)) is not None
    assert await commitments.for_screen(db, user, day + timedelta(days=7)) is None


async def test_first_week_cap_still_applies_to_a_committed_goal(user_client, db):
    client, _user = user_client
    await client.post("/api/me/commitment", json={"daily_xp": 80, "days": 7})
    today = (await client.get("/api/today")).json()
    assert today["goal"]["target_xp"] == 30 and today["easy_mode"]  # first week: capped
    assert today["commitment"]["daily_xp"] == 80
    assert len(list(starter())) >= 7 and gen_service.BONUS_MODE == "bonus"
