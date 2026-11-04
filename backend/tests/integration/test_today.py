"""GET /today and /me."""

from datetime import timedelta

import pytest

from app.generation import service as gen_service
from app.services.clock import today_for

pytestmark = pytest.mark.integration


async def test_today_orders_cards_and_counts_remaining(user_client, db):
    client, user = user_client
    day = today_for(user)
    await gen_service.insert_starter_pack(db, day)
    body = (await client.get("/api/today")).json()
    types = [c["type"] for c in body["cards"]]
    assert types[0] == "brainteaser" and types[1] == "fit"
    case_diffs = [c["difficulty"] for c in body["cards"] if c["type"] not in ("brainteaser", "fit")]
    assert case_diffs == sorted(case_diffs)
    assert body["remaining"] == len(body["cards"])
    assert body["goal"] == {"target_xp": 30, "xp_today": 0, "met": False}  # first week
    assert body["easy_mode"] is True
    assert body["streak"]["status"] == "safe"
    assert body["league"]["tier"] == "bronze"


async def test_today_without_exercises_is_empty_not_an_error(user_client):
    client, _ = user_client
    body = (await client.get("/api/today")).json()
    assert body["cards"] == [] and body["remaining"] == 0


async def test_cadrage_home_pinned_until_sunday(user_client, db):
    from app.db.models import Exercise
    from app.generation.planner import SlotSpec
    from app.generation.schema import validate
    from tests.fake_llm import exercise_json

    client, user = user_client
    day = today_for(user)
    friday = day - timedelta(days=(day.weekday() - 4) % 7)
    spec = SlotSpec("cadrage_home", "cadrage_home", 4, "fr", "wavestone", "banque", True)
    fields = validate(exercise_json("cadrage_home"), spec)
    db.add(Exercise(date=friday, slot="cadrage_home", **fields))
    await db.commit()
    body = (await client.get("/api/today")).json()
    pinned = [c for c in body["cards"] if c["pinned"]]
    if day.weekday() in (4, 5, 6):
        assert pinned and pinned[0]["due_label"] == "À rendre dimanche soir"
    else:
        assert not pinned


async def test_me_patch_and_delete(user_client):
    client, _user = user_client
    me = (await client.get("/api/me")).json()
    assert me["daily_goal_xp"] == 50 and me["timezone"] == "Asia/Singapore"
    patched = await client.patch(
        "/api/me", json={"daily_goal_xp": 80, "timezone": "Europe/Paris", "sounds_enabled": False}
    )
    assert patched.status_code == 200
    assert patched.json()["daily_goal_xp"] == 80 and patched.json()["sounds_enabled"] is False
    assert (await client.patch("/api/me", json={"daily_goal_xp": 45})).status_code == 422
    assert (await client.patch("/api/me", json={"timezone": "Mars/Base"})).status_code == 422
    assert (await client.delete("/api/me")).status_code == 204
    assert (await client.get("/api/users/me")).status_code == 401
