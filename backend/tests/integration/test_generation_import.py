"""Generation by a Claude Code scheduled task: plan, import (validated), finish."""

from datetime import date

import pytest
from sqlalchemy import select

from app.db.models import CronRun, Exercise
from app.generation.planner import plan_day
from tests.fake_llm import SEARCH_URL, exercise_json

pytestmark = pytest.mark.integration

DAY = date(2026, 11, 13)  # a Friday
TOKEN = "import-token-for-tests-0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setenv("GENERATION_IMPORT_TOKEN", TOKEN)


async def test_routes_hidden_without_token_config(client, monkeypatch):
    monkeypatch.delenv("GENERATION_IMPORT_TOKEN", raising=False)
    assert (await client.get("/api/generation/plan", headers=AUTH)).status_code == 404


async def test_wrong_token_refused(client, token):
    resp = await client.get("/api/generation/plan", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


async def test_plan_import_finish(client, db, token):
    plan = (await client.get(f"/api/generation/plan?date={DAY.isoformat()}", headers=AUTH)).json()
    assert plan["date"] == DAY.isoformat() and plan["weekday"] == "vendredi"
    assert "senior manager de la practice Data & IA" in plan["system_prompt"]
    slots = {s["slot"]: s for s in plan["slots"]}
    assert set(slots) == {s.slot for s in plan_day(DAY).slots}
    assert "- slot : case_cadrage" in slots["case_cadrage"]["user_message"]

    # an invalid exercise comes back with the reason, nothing inserted
    bad = exercise_json("cadrage")
    bad["rubric"][0]["weight"] += 5
    resp = await client.post(
        "/api/generation/import",
        headers=AUTH,
        json={"date": DAY.isoformat(), "slot": "case_cadrage", "exercise": bad},
    )
    assert resp.status_code == 422 and "poids" in resp.json()["detail"]

    resp = await client.post(
        "/api/generation/import",
        headers=AUTH,
        json={
            "date": DAY.isoformat(),
            "slot": "case_cadrage",
            "exercise": exercise_json("cadrage"),
            "search_urls": [SEARCH_URL],
        },
    )
    body = resp.json()
    assert resp.status_code == 200 and body["inserted"] and "case_cadrage" not in body["remaining"]
    ex = (await db.execute(select(Exercise).where(Exercise.slot == "case_cadrage"))).scalar_one()
    assert ex.generation_mode == "claude_code" and ex.sources[0]["verified"] is True

    again = await client.post(
        "/api/generation/import",
        headers=AUTH,
        json={
            "date": DAY.isoformat(),
            "slot": "case_cadrage",
            "exercise": exercise_json("cadrage"),
        },
    )
    assert again.status_code == 409
    unknown = await client.post(
        "/api/generation/import",
        headers=AUTH,
        json={"date": DAY.isoformat(), "slot": "nope", "exercise": {}},
    )
    assert unknown.status_code == 404

    done = (
        await client.post(
            "/api/generation/finish",
            headers=AUTH,
            json={"date": DAY.isoformat(), "summary": "1/10"},
        )
    ).json()
    assert (
        done["status"] == "partial"
        and done["inserted"] == 1
        and len(done["missing"]) == len(slots) - 1
    )
    run = (await db.execute(select(CronRun).where(CronRun.job == "claude_code"))).scalar_one()
    assert run.status == "partial" and run.n_succeeded == 1 and run.cost_usd == 0
    assert any("poids" in str(e.get("error", "")) for e in run.errors)


async def test_default_date_is_tomorrow(client, token):
    from datetime import timedelta

    from app.llm.cost_tracker import today_jobs_tz

    plan = (await client.get("/api/generation/plan", headers=AUTH)).json()
    assert plan["date"] == (today_jobs_tz() + timedelta(days=1)).isoformat()
