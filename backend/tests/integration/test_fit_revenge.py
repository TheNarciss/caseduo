"""Fit context sent to the grader, revenges scheduled and played, history."""

from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.db.models import Exercise, Revenge
from app.generation import service as gen_service
from app.llm import anthropic_client
from app.services.clock import today_for
from tests.fake_llm import FakeClient, attach_grader, grade_text

pytestmark = pytest.mark.integration


@pytest.fixture
def grader():
    client = FakeClient()
    state = {"mark": 2}

    def text_for(params):
        user_text = params["messages"][0]["content"][0]["text"]
        keys = [line.split("`")[1] for line in user_text.splitlines() if line.startswith("- `")]
        return grade_text(keys, [state["mark"]] * len(keys))

    attach_grader(client, text_for)
    anthropic_client.set_client_for_testing(client)
    yield client, state
    anthropic_client.set_client_for_testing(None)


async def slots(db, user):
    day = today_for(user)
    await gen_service.insert_starter_pack(db, day)
    rows = (await db.execute(select(Exercise).where(Exercise.date == day))).scalars().all()
    return {r.slot: r for r in rows}


async def test_fit_grading_gets_story_and_previous_fit_answers(user_client, db, grader):
    client, user = user_client
    ex = await slots(db, user)
    await client.put(
        "/api/me/story", json={"story_text": "ESILV, Thales Rungis, Thales Singapour."}
    )
    me = (await client.get("/api/me")).json()
    assert me["story_text"].startswith("ESILV")
    # an earlier fit answer, on another fit exercise
    other = Exercise(
        **{
            **{c.name: getattr(ex["starter_fit"], c.name) for c in Exercise.__table__.columns},
            "id": None,
            "slot": "fit_old",
            "date": ex["starter_fit"].date - timedelta(days=2),
            "title": "Pourquoi nous ?",
        }
    )
    other.id = None
    db.add(other)
    await db.commit()
    await client.post(
        "/api/grade",
        json={"exercise_id": str(other.id), "answer_text": "Parce que la practice Data & IA."},
    )
    await client.post(
        "/api/grade",
        json={
            "exercise_id": str(ex["starter_fit"].id),
            "answer_text": "J'ai quitté Thales pour le conseil.",
        },
    )
    attempt_block = grader[0].calls[-1]["messages"][0]["content"][1]["text"]
    assert "Récit de parcours" in attempt_block and "Thales Singapour" in attempt_block
    assert "Pourquoi nous ?" in attempt_block and "la practice Data & IA" in attempt_block


async def test_low_score_schedules_revenges_then_plays_them(user_client, db, grader):
    client, user = user_client
    ex = (await slots(db, user))["starter_cadrage"]
    _, state = grader
    state["mark"] = 0
    first = (
        await client.post(
            "/api/grade",
            json={"exercise_id": str(ex.id), "answer_text": "Une réponse faible mais longue."},
        )
    ).json()
    assert first["attempt"]["score"] == 0
    revenges = (await db.execute(select(Revenge).order_by(Revenge.step))).scalars().all()
    day = today_for(user)
    assert [(r.step, r.due_date) for r in revenges] == [
        (1, day + timedelta(days=3)),
        (2, day + timedelta(days=10)),
    ]

    # three days later: bring step 1 due today
    await db.execute(update(Revenge).where(Revenge.step == 1).values(due_date=day))
    await db.commit()
    cards = (await client.get("/api/today")).json()["cards"]
    revenge_card = cards[-1]
    assert revenge_card["is_revenge"] and revenge_card["exercise_id"] == str(ex.id)
    assert revenge_card["xp_potential"] == 36  # 30 × 1.2
    detail = (await client.get(f"/api/exercises/{ex.id}")).json()
    assert detail["is_revenge"] is True

    state["mark"] = 1
    second = (
        await client.post(
            "/api/grade",
            json={"exercise_id": str(ex.id), "answer_text": "Une réponse meilleure cette fois."},
        )
    ).json()
    assert second["attempt"]["is_revenge"] is True
    assert second["xp"]["earned"] == 36
    step1 = (await db.execute(select(Revenge).where(Revenge.step == 1))).scalar_one()
    await db.refresh(step1)
    assert step1.done_attempt_id is not None
    assert not any(c["is_revenge"] for c in (await client.get("/api/today")).json()["cards"])


async def test_flagged_exercise_leaves_revenges(user_client, db, grader):
    client, user = user_client
    ex = (await slots(db, user))["starter_diagnostic"]
    grader[1]["mark"] = 0
    await client.post(
        "/api/grade",
        json={"exercise_id": str(ex.id), "answer_text": "Une réponse faible mais longue."},
    )
    await db.execute(update(Revenge).values(due_date=today_for(user)))
    await db.execute(update(Exercise).where(Exercise.id == ex.id).values(flagged=True))
    await db.commit()
    cards = (await client.get("/api/today")).json()["cards"]
    assert not any(c["is_revenge"] for c in cards)


async def test_history_series_weaknesses_calendar(user_client, db, grader):
    client, user = user_client
    ex = await slots(db, user)
    grader[1]["mark"] = 1
    for slot in ("starter_cadrage", "starter_market_sizing"):
        await client.post(
            "/api/grade",
            json={"exercise_id": str(ex[slot].id), "answer_text": "Réponse moyenne, structurée."},
        )
    body = (await client.get("/api/history")).json()
    types = {s["type"] for s in body["series"]}
    assert types == {"cadrage", "market_sizing"}
    assert len(body["weaknesses"]) == 3 and body["weaknesses"][0]["average"] == 1.0
    assert body["calendar"][-1]["xp"] > 0
    assert len(body["recent_attempts"]) == 2
