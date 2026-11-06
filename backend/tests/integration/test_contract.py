"""Real backend responses, one per screen, decoded by the iPhone app's models.

Run with UPDATE_CONTRACT_FIXTURES=1 to (re)write them into
ios/Packages/CaseDuoCore/Tests/CaseDuoCoreTests/Fixtures/backend/, where
`BackendContractTests.swift` decodes each file with the app's Codable types
(`swift test`, on macOS in CI or on Linux). A backend change that breaks the
app's decoding then fails on the Swift side.
"""

import json
import os
from datetime import date
from pathlib import Path

import pytest

from app.content import bonus
from app.generation import service as gen_service
from app.llm import anthropic_client
from app.routers import mocks as mocks_router
from app.services.clock import today_for
from tests.fake_llm import FakeClient, attach_grader, grade_text

pytestmark = pytest.mark.integration

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "ios/Packages/CaseDuoCore/Tests/CaseDuoCoreTests/Fixtures/backend"
)


@pytest.fixture
def llm():
    client = FakeClient()

    def text_for(params):
        user_text = params["messages"][0]["content"][0]["text"]
        keys = [line.split("`")[1] for line in user_text.splitlines() if line.startswith("- `")]
        return grade_text(keys, [(i % 3) for i in range(len(keys))])

    attach_grader(client, text_for)
    anthropic_client.set_client_for_testing(client)
    yield client
    anthropic_client.set_client_for_testing(None)


async def test_every_screen_response(admin_client, db, llm, monkeypatch):
    client, user = admin_client
    out: dict[str, object] = {}
    await gen_service.insert_starter_pack(db, today_for(user))

    async def get(name, path):
        resp = await client.get(path)
        assert resp.status_code == 200, (path, resp.text)
        out[name] = resp.json()
        return out[name]

    await get("providers", "/api/auth/providers")
    await client.put(
        "/api/me/story", json={"story_text": "ESILV, Thales Rungis, Thales Singapour."}
    )
    resp = await client.post("/api/me/commitment", json={"daily_xp": 50, "days": 14})
    assert resp.status_code == 200, resp.text
    await get("me", "/api/me")
    await bonus.import_packs(db, today_for(user))
    await get("training", "/api/training")
    today = await get("today", "/api/today")
    card = next(c for c in today["cards"] if c["type"] == "market_sizing")
    await get("exercise", f"/api/exercises/{card['exercise_id']}")
    resp = await client.post(f"/api/exercises/{card['exercise_id']}/reveal")
    out["reveal"] = resp.json()
    resp = await client.post(
        "/api/grade",
        json={
            "exercise_id": card["exercise_id"],
            "answer_text": "Bottom-up par les vols, trois étapes.",
            "input_mode": "voice",
            "duration_seconds": 240,
        },
    )
    out["grade_result"] = grade = resp.json()
    resp = await client.post(
        "/api/grade",
        json={
            "exercise_id": card["exercise_id"],
            "kind": "follow_up",
            "parent_attempt_id": grade["attempt"]["id"],
            "answer_text": "Je pose 80 % de remplissage.",
        },
    )
    out["grade_result_follow_up"] = resp.json()
    async with client.stream(
        "POST",
        "/api/grade/stream",
        json={
            "exercise_id": today["cards"][0]["exercise_id"],
            "answer_text": "22 fois, vitesse relative.",
        },
    ) as stream:
        text = "".join([c async for c in stream.aiter_text()])
    events = {
        b.split("\n")[0].removeprefix("event: "): json.loads(b.split("data: ", 1)[1])
        for b in text.strip().split("\n\n")
    }
    out["sse_scores"] = events["scores"]
    out["sse_follow_up"] = events["follow_up"]
    await get("attempts", "/api/attempts")
    await get("attempt", f"/api/attempts/{grade['attempt']['id']}")
    await get("history", "/api/history")
    await get("league", "/api/league")
    await get("badges", "/api/badges")
    await get("widget", "/api/widget")
    await get("day_summary", "/api/day/summary")

    sunday = date(2026, 11, 8)
    monkeypatch.setattr(mocks_router, "today_for", lambda u: sunday)
    await gen_service.generate_day_sync(db, sunday)
    run = (await client.post("/api/mocks", json={"kind": "full"})).json()
    out["mock_run"] = run
    step = run["steps"][1]
    res = (
        await client.post(
            "/api/grade",
            json={
                "exercise_id": step["exercise_id"],
                "answer_text": "Réponse orale.",
                "mock_run_id": run["id"],
            },
        )
    ).json()
    await client.post(
        "/api/grade",
        json={
            "exercise_id": step["exercise_id"],
            "kind": "follow_up",
            "parent_attempt_id": res["attempt"]["id"],
            "answer_text": "Je réponds à la relance.",
            "mock_run_id": run["id"],
        },
    )
    out["mock_finish"] = (await client.post(f"/api/mocks/{run['id']}/finish")).json()

    resp = await client.post(
        "/api/grade",
        json={"exercise_id": "00000000-0000-0000-0000-000000000000", "answer_text": "Une réponse."},
    )
    out["error_404"] = resp.json()
    resp = await client.patch("/api/me", json={"daily_goal_xp": 45})
    out["error_422"] = resp.json()

    assert len(out) == 21
    if os.getenv("UPDATE_CONTRACT_FIXTURES") == "1":
        FIXTURES.mkdir(parents=True, exist_ok=True)
        for name, body in out.items():
            (FIXTURES / f"{name}.json").write_text(
                json.dumps(body, ensure_ascii=False, indent=2) + "\n"
            )
