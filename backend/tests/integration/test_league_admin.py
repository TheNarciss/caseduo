"""League view and weekly close, badges, admin review + flag + regenerate."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.auth import User
from app.db.models import DailyActivity, Exercise, LeagueWeek
from app.generation import service as gen_service
from app.llm import anthropic_client
from app.services import leagues
from app.services.clock import today_for
from tests.fake_llm import FakeClient, attach_grader, grade_text

pytestmark = pytest.mark.integration


@pytest.fixture
def llm():
    client = FakeClient()

    def text_for(params):
        user_text = params["messages"][0]["content"][0]["text"]
        keys = [line.split("`")[1] for line in user_text.splitlines() if line.startswith("- `")]
        return grade_text(keys, [2] * len(keys))

    attach_grader(client, text_for)
    anthropic_client.set_client_for_testing(client)
    yield client
    anthropic_client.set_client_for_testing(None)


async def test_league_view_and_today_rank(user_client, db):
    client, _ = user_client
    league = (await client.get("/api/league")).json()
    assert league["tier"] == "bronze" and len(league["members"]) == 6
    assert sum(m["is_me"] for m in league["members"]) == 1
    assert league["promote_top"] == 2 and league["last_outcome"] is None
    today = (await client.get("/api/today")).json()
    assert today["league"]["size"] == 6 and 1 <= today["league"]["rank"] <= 6


async def test_week_close_promotes_a_top_player(user_client, db):
    client, user = user_client
    row_user = await db.get(User, user.id)
    start = leagues.week_start(today_for(row_user)) - timedelta(days=7)
    db.add(
        LeagueWeek(
            user_id=user.id,
            week_start=start,
            tier="bronze",
            bots=[{"name": f"B{i}", "daily_xp": [0] * 7} for i in range(5)],
        )
    )
    db.add(DailyActivity(user_id=user.id, date=start + timedelta(days=2), xp_earned=200))
    await db.commit()
    league = (await client.get("/api/league")).json()
    assert league["last_outcome"] == "promoted" and league["tier"] == "silver"
    badges = (await client.get("/api/badges")).json()
    assert next(b for b in badges if b["code"] == "league_silver")["earned_at"]


async def test_badges_after_grading(user_client, db, llm):
    client, user = user_client
    await gen_service.insert_starter_pack(db, today_for(user))
    cards = (await client.get("/api/today")).json()["cards"]
    case = next(c for c in cards if c["type"] == "cadrage")
    res = (
        await client.post(
            "/api/grade",
            json={
                "exercise_id": case["exercise_id"],
                "answer_text": "Une réponse parfaite, structurée.",
            },
        )
    ).json()
    codes = {b["code"] for b in res["progress"]["new_badges"]}
    assert {"first_case", "score_90"} <= codes
    res2 = (
        await client.post(
            "/api/grade",
            json={
                "exercise_id": case["exercise_id"],
                "answer_text": "Encore une réponse parfaite.",
            },
        )
    ).json()
    assert res2["progress"]["new_badges"] == []


async def test_admin_review_flag_and_html(admin_client, db, llm):
    client, admin = admin_client
    day = today_for(admin)
    await gen_service.insert_starter_pack(db, day)
    data = (await client.get(f"/api/admin/review/{day.isoformat()}")).json()
    assert len(data["exercises"]) == 7
    ex_id = data["exercises"][0]["id"]
    flagged = (
        await client.post(
            f"/api/admin/exercises/{ex_id}/flag", json={"flagged": True, "note": "chiffrage faux"}
        )
    ).json()
    assert flagged["flagged"] and flagged["flag_note"] == "chiffrage faux"
    page = await client.get(f"/admin/review/{day.isoformat()}")
    assert (
        page.status_code == 200
        and "Marquer « mauvais »" in page.text
        and "chiffrage faux" in page.text
    )


async def test_admin_is_protected(user_client, client):
    c, _user = user_client
    assert (await c.get("/api/admin/review/2026-11-04")).status_code == 403
    page = await c.get("/admin/review/2026-11-04")
    assert "Connexion administrateur" in page.text


async def test_admin_force_regenerate_keeps_answered(admin_client, db, llm):
    client, admin = admin_client
    day = today_for(admin) + timedelta(days=30)
    await gen_service.generate_day_sync(db, day)
    n = len((await db.execute(select(Exercise).where(Exercise.date == day))).scalars().all())
    resp = (
        await client.post("/api/admin/generate", json={"date": day.isoformat(), "force": True})
    ).json()
    assert resp["deleted"] == n and resp["run"]["n_succeeded"] == n
    runs = (await client.get("/api/admin/cron-runs")).json()
    assert runs and runs[0]["target_date"] == day.isoformat()
    _ = datetime.now(UTC)
