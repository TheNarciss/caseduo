"""Sunday mock (regular and MBB), Saturday fit mock, cadrage_home slides."""

from datetime import date, timedelta

import pytest

from app.generation import service as gen_service
from app.generation.planner import mock_is_mbb
from app.llm import anthropic_client
from app.routers import mocks as mocks_router
from app.services.mocks import global_score
from tests.fake_llm import FakeClient, attach_grader, grade_text

pytestmark = pytest.mark.integration


def sunday(mbb: bool) -> date:
    d = date(2026, 11, 8)  # a Sunday
    while mock_is_mbb(d) != mbb:
        d += timedelta(days=7)
    return d


@pytest.fixture
def llm():
    client = FakeClient()

    def text_for(params):
        user_text = params["messages"][0]["content"][0]["text"]
        keys = [line.split("`")[1] for line in user_text.splitlines() if line.startswith("- `")]
        return grade_text(keys, [1] * len(keys))

    attach_grader(client, text_for)
    anthropic_client.set_client_for_testing(client)
    yield client
    anthropic_client.set_client_for_testing(None)


async def test_regular_sunday_mock_end_to_end(user_client, db, llm, monkeypatch):
    client, _user = user_client
    day = sunday(mbb=False)
    monkeypatch.setattr(mocks_router, "today_for", lambda u: day)
    await gen_service.generate_day_sync(db, day)

    run = (await client.post("/api/mocks", json={"kind": "full"})).json()
    assert [s["type"] for s in run["steps"]] == ["fit", "market_sizing", "cadrage"]
    assert [s["follow_up_after"] for s in run["steps"]] == [False, True, True]
    assert run["time_limit_seconds"] == 1800
    resumed = (await client.post("/api/mocks", json={"kind": "full"})).json()
    assert resumed["id"] == run["id"]

    for step in run["steps"]:
        res = (
            await client.post(
                "/api/grade",
                json={
                    "exercise_id": step["exercise_id"],
                    "answer_text": "Réponse orale structurée.",
                    "input_mode": "voice",
                    "mock_run_id": run["id"],
                },
            )
        ).json()
        assert res["xp"]["breakdown"][-1]["label"] == "Mock entretien : ×2"
        assert res["attempt"]["follow_up"]
        if step["follow_up_after"]:
            fu = await client.post(
                "/api/grade",
                json={
                    "exercise_id": step["exercise_id"],
                    "kind": "follow_up",
                    "parent_attempt_id": res["attempt"]["id"],
                    "answer_text": "Je réponds à la relance.",
                    "mock_run_id": run["id"],
                },
            )
            assert fu.status_code == 200
    done = (await client.post(f"/api/mocks/{run['id']}/finish")).json()
    assert done["score"] == 50 and len(done["attempts"]) == 5 and done["previous"] == []
    assert "Relance" in done["feedback"]
    assert (await client.post(f"/api/mocks/{run['id']}/finish")).status_code == 409
    again = await client.post(
        "/api/grade",
        json={
            "exercise_id": run["steps"][0]["exercise_id"],
            "answer_text": "Encore une réponse.",
            "mock_run_id": run["id"],
        },
    )
    assert again.status_code == 409


async def test_mbb_sunday_mock_has_pei_and_four_part_case(user_client, db, llm, monkeypatch):
    client, _ = user_client
    day = sunday(mbb=True)
    monkeypatch.setattr(mocks_router, "today_for", lambda u: day)
    await gen_service.generate_day_sync(db, day)
    run = (await client.post("/api/mocks", json={"kind": "full"})).json()
    assert run["mbb"] is True
    assert [s["type"] for s in run["steps"]] == ["fit", "business_case"]
    assert len(run["steps"][1]["parts"]) == 4 and run["steps"][1]["context_data"] is not None


async def test_no_mock_on_a_weekday(user_client, db, monkeypatch):
    client, _ = user_client
    monkeypatch.setattr(mocks_router, "today_for", lambda u: date(2026, 11, 4))
    assert (await client.post("/api/mocks", json={"kind": "full"})).status_code == 409


async def test_saturday_fit_mock_six_questions(user_client, db, llm, monkeypatch):
    client, _ = user_client
    day = date(2026, 11, 7)  # Saturday of ISO week 45 (odd) → none; week 46 → yes
    if day.isocalendar()[1] % 2:
        day += timedelta(days=7)
    monkeypatch.setattr(mocks_router, "today_for", lambda u: day)
    await gen_service.generate_day_sync(db, day)
    run = (await client.post("/api/mocks", json={"kind": "fit"})).json()
    assert len(run["steps"]) == 1 and len(run["steps"][0]["parts"]) == 6
    assert run["time_limit_seconds"] == 900
    res = await client.post(
        "/api/grade",
        json={
            "exercise_id": run["steps"][0]["exercise_id"],
            "part_answers": [f"Réponse {i}" for i in range(6)],
            "mock_run_id": run["id"],
        },
    )
    assert res.status_code == 200
    assert "Partie 6" in llm.calls[-1]["messages"][0]["content"][1]["text"]


async def test_cadrage_home_requires_five_slides(user_client, db, llm):
    from app.db.models import Exercise
    from app.generation.planner import SlotSpec
    from app.generation.schema import validate
    from app.services.clock import today_for
    from tests.fake_llm import exercise_json

    client, user = user_client
    spec = SlotSpec("cadrage_home", "cadrage_home", 4, "fr", "wavestone", "banque", True)
    ex = Exercise(
        date=today_for(user), slot="cadrage_home", **validate(exercise_json("cadrage_home"), spec)
    )
    db.add(ex)
    await db.commit()
    four = [{"title": f"Message {i}", "lines": ["a", "b", "c"]} for i in range(4)]
    assert (
        await client.post("/api/grade", json={"exercise_id": str(ex.id), "slides": four})
    ).status_code == 422
    five = [*four, {"title": "Recommandation : lancer un pilote", "lines": ["x", "y", "z"]}]
    res = (await client.post("/api/grade", json={"exercise_id": str(ex.id), "slides": five})).json()
    assert res["xp"]["earned"] == 40
    sent = llm.calls[-1]["messages"][0]["content"][1]["text"]
    assert "Slide 5 — Recommandation : lancer un pilote" in sent


def test_global_score():
    assert global_score([80, 60, 40], [], 3) == 60
    assert global_score([80, 60], [], 3) == 47  # one step unanswered counts 0
    assert global_score([80, 60, 40], [100, 0], 3) == 58  # 60 × 0.8 + 50 × 0.2
