"""Grading end to end with a fake streaming Claude."""

import json
from datetime import date

import pytest
from sqlalchemy import select

from app.content.starter_pack import exercises as starter
from app.db.models import Attempt, DailyActivity, Exercise
from app.generation import service as gen_service
from app.llm import anthropic_client
from tests.fake_llm import FakeClient, attach_grader, grade_text

pytestmark = pytest.mark.integration


@pytest.fixture
def grader():
    client = FakeClient()
    state = {"marks": None}

    def text_for(params):
        user_text = params["messages"][0]["content"][0]["text"]
        keys = [line.split("`")[1] for line in user_text.splitlines() if line.startswith("- `")]
        return grade_text(keys, state["marks"] or [2] * len(keys))

    attach_grader(client, text_for)
    anthropic_client.set_client_for_testing(client)
    yield client, state
    anthropic_client.set_client_for_testing(None)


async def seed_today(db, user):
    from app.services.clock import today_for

    day = today_for(user)
    await gen_service.insert_starter_pack(db, day)
    rows = (await db.execute(select(Exercise).where(Exercise.date == day))).scalars().all()
    return {r.slot: r for r in rows}


async def test_grade_json_scores_server_side_and_gives_xp(user_client, db, grader):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_cadrage"]
    _, state = grader
    state["marks"] = [2, 1, 1, 2, 0]  # weights 15/25/25/20/15
    resp = await client.post(
        "/api/grade",
        json={
            "exercise_id": str(ex.id),
            "answer_text": "Je reformule puis j'annonce trois axes.",
            "duration_seconds": 300,
            "input_mode": "voice",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    expected = round(15 + 12.5 + 12.5 + 20 + 0)
    assert body["attempt"]["score"] == expected  # not the model's 99
    assert body["xp"]["earned"] == 30  # 10 × difficulty 3, score < 80
    assert body["attempt"]["follow_up"].startswith("Et si")
    assert "Ce qui était bien" in body["attempt"]["feedback"]
    assert body["attempt"]["exercise"]["model_answer"]
    assert body["progress"]["xp_today"] == 30
    assert body["progress"]["remaining"] == 6
    stored = (await db.execute(select(Attempt))).scalar_one()
    assert stored.cost_usd > 0 and stored.input_tokens == 1000
    daily = (await db.execute(select(DailyActivity))).scalar_one()
    assert daily.xp_earned == 30 and daily.exercises_done == 1


async def test_grade_stream_emits_scores_feedback_follow_up_done(user_client, db, grader):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_fit"]
    async with client.stream(
        "POST",
        "/api/grade/stream",
        json={
            "exercise_id": str(ex.id),
            "answer_text": "Mon parcours en deux minutes : Thales, puis Singapour.",
        },
    ) as resp:
        assert resp.status_code == 200
        text = "".join([chunk async for chunk in resp.aiter_text()])
    events = [block.split("\n")[0].removeprefix("event: ") for block in text.strip().split("\n\n")]
    assert events[0] == "scores" and events[-1] == "done"
    assert "feedback" in events and "follow_up" in events
    done = json.loads(text.strip().split("\n\n")[-1].split("data: ", 1)[1])
    assert done["attempt"]["score"] == 100 and done["xp"]["earned"] == 12  # 8 × 1.5


async def test_follow_up_and_retry(user_client, db, grader):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_business_case"]
    first = (
        await client.post(
            "/api/grade",
            json={"exercise_id": str(ex.id), "answer_text": "Une première réponse assez longue."},
        )
    ).json()
    parent = first["attempt"]["id"]
    fu = await client.post(
        "/api/grade",
        json={
            "exercise_id": str(ex.id),
            "kind": "follow_up",
            "parent_attempt_id": parent,
            "answer_text": "Je divise le périmètre par deux.",
        },
    )
    assert fu.status_code == 200 and fu.json()["xp"]["earned"] == 5
    again = await client.post(
        "/api/grade",
        json={
            "exercise_id": str(ex.id),
            "kind": "follow_up",
            "parent_attempt_id": parent,
            "answer_text": "Encore une réponse.",
        },
    )
    assert again.status_code == 409
    retry = await client.post(
        "/api/grade",
        json={
            "exercise_id": str(ex.id),
            "kind": "retry_2min",
            "parent_attempt_id": parent,
            "answer_text": "Version en deux minutes.",
        },
    )
    assert retry.json()["xp"]["earned"] == 10
    last_call = grader[0].calls[-1]
    assert "Première tentative" in last_call["messages"][0]["content"][1]["text"]
    assert last_call["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}


async def test_reveal_before_answering_costs_five_xp(user_client, db, grader):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_market_sizing"]
    detail = (await client.get(f"/api/exercises/{ex.id}")).json()
    assert detail["context_data"] is None and detail["context_data_available"]
    rev = (await client.post(f"/api/exercises/{ex.id}/reveal")).json()
    assert rev["xp_penalty"] == 5 and rev["context_data"]["facts"]
    resp = (
        await client.post(
            "/api/grade", json={"exercise_id": str(ex.id), "answer_text": "Bottom-up par les vols."}
        )
    ).json()
    assert resp["attempt"]["revealed_data"] is True
    assert resp["xp"]["earned"] == 25  # 20 × 1.5 − 5
    assert (await client.get(f"/api/exercises/{ex.id}")).json()["context_data"] is not None


async def test_errors_before_streaming(user_client, db):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_fit"]
    anthropic_client.set_client_for_testing(None)
    resp = await client.post(
        "/api/grade", json={"exercise_id": str(ex.id), "answer_text": "Une réponse correcte."}
    )
    assert resp.status_code == 503
    short = await client.post("/api/grade", json={"exercise_id": str(ex.id), "answer_text": "ok"})
    assert short.status_code == 422
    missing = await client.post(
        "/api/grade",
        json={
            "exercise_id": "00000000-0000-0000-0000-000000000000",
            "answer_text": "Une réponse correcte.",
        },
    )
    assert missing.status_code == 404


async def test_attempts_listing(user_client, db, grader):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_brainteaser"]
    await client.post(
        "/api/grade",
        json={"exercise_id": str(ex.id), "answer_text": "22 fois, par la vitesse relative."},
    )
    listing = (await client.get("/api/attempts")).json()
    assert len(listing) == 1 and listing[0]["type"] == "brainteaser"
    full = (await client.get(f"/api/attempts/{listing[0]['id']}")).json()
    assert full["exercise"]["rubric"]


def test_starter_pack_slots_unique():
    slots = [s for s, _ in starter()]
    assert len(slots) == len(set(slots))
    assert date.today()  # keep import used
