"""Grading through Claude Code on the subscription (DEVIATIONS D14), with a fake CLI."""

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models import Attempt
from tests.integration.test_grading import seed_today

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def sse_events(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        head, data = block.split("\n", 1)
        out.append((head.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return out


async def test_claude_code_streams_the_grading_like_the_api(user_client, db, fake_cli):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_cadrage"]
    async with client.stream(
        "POST",
        "/api/grade/stream",
        json={"exercise_id": str(ex.id), "answer_text": "Je reformule puis j'annonce trois axes."},
    ) as resp:
        assert resp.status_code == 200
        events = sse_events("".join([chunk async for chunk in resp.aiter_text()]))
    names = [name for name, _ in events]
    assert names[0] == "scores" and names[-1] == "done"
    assert "feedback" in names and "follow_up" in names
    done = events[-1][1]
    assert done["attempt"]["score"] == 100  # recomputed by the server, not the model's 99

    stored = (await db.execute(select(Attempt))).scalar_one()
    assert stored.cost_usd == 0  # the subscription pays
    assert stored.model_used == "claude-sonnet-5-5"
    assert stored.output_tokens == 900 and stored.cache_write_tokens == 4200

    seen = json.loads((fake_cli / "cli.jsonl").read_text().splitlines()[-1])
    argv = seen["argv"]
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert "Tu es l'interviewer" in argv[argv.index("--system-prompt") + 1]
    assert "ANTHROPIC_API_KEY" not in seen["env"]  # the CLI would bill the API with it
    assert "### Réponse du candidat" in seen["stdin"] and "### Rubric" in seen["stdin"]


async def test_usage_limit_is_said_and_nothing_is_stored(user_client, db, fake_cli):
    client, user = user_client
    ex = (await seed_today(db, user))["starter_fit"]
    (fake_cli / "mode").write_text("limit")
    resp = await client.post(
        "/api/grade", json={"exercise_id": str(ex.id), "answer_text": "Mon parcours en bref."}
    )
    assert resp.status_code == 503
    assert "limite d'usage" in resp.json()["detail"]
    assert (await db.execute(select(Attempt))).first() is None

    (fake_cli / "mode").write_text("auth")
    resp = await client.post(
        "/api/grade", json={"exercise_id": str(ex.id), "answer_text": "Mon parcours en bref."}
    )
    assert "setup-token" in resp.json()["detail"]


async def test_provider_choice(user_client, db, fake_cli, monkeypatch):
    from app.grading.service import provider

    assert provider() == "claude_code"  # auto: the subscription first
    monkeypatch.setenv("GRADING_PROVIDER", "api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert provider() is None
    monkeypatch.setenv("GRADING_PROVIDER", "auto")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "")
    assert provider() is None
    client, user = user_client
    ex = (await seed_today(db, user))["starter_fit"]
    resp = await client.post(
        "/api/grade", json={"exercise_id": str(ex.id), "answer_text": "Mon parcours en bref."}
    )
    assert resp.status_code == 503 and "pas configurée" in resp.json()["detail"]
