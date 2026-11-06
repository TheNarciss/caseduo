"""The day's exercises written by Claude Code on the subscription (DEVIATIONS D15), and the
bonus pack, with a fake CLI."""

import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.content import bonus
from app.db.models import CronRun, Exercise
from app.generation import provider, service
from app.services import today as today_service
from app.services.clock import today_for
from tests.fake_llm import SEARCH_URL, exercise_json

pytestmark = pytest.mark.integration


def calls(folder) -> list[dict]:
    return [json.loads(line) for line in (folder / "cli.jsonl").read_text().splitlines()]


def arg(call: dict, name: str) -> str:
    argv = call["argv"]
    return argv[argv.index(name) + 1]


async def test_claude_code_writes_the_day_and_replaces_the_unused_starter_pack(
    user_client, db, fake_cli, monkeypatch
):
    monkeypatch.setenv("GENERATION_PROVIDER", "claude_code")
    assert provider.provider() == "claude_code"
    client, user = user_client
    day = today_for(user)
    await service.insert_starter_pack(db, day)
    starter = {e.slot: e for e in (await db.execute(select(Exercise))).scalars()}
    answered = starter["starter_fit"]
    resp = await client.post(
        "/api/grade", json={"exercise_id": str(answered.id), "answer_text": "Mon parcours en bref."}
    )
    assert resp.status_code == 200, resp.text

    plan, _ = await service.plan_for(db, day)
    run = await service.generate_day_sync(db, day, job="claude_code")
    assert run is not None and run.status == "ended"
    assert run.n_succeeded == len(plan.slots) and run.cost_usd == 0

    db.expire_all()
    rows = (await db.execute(select(Exercise).where(Exercise.date == day))).scalars().all()
    slots = {e.slot for e in rows}
    assert {s.slot for s in plan.slots} <= slots
    assert slots - {s.slot for s in plan.slots} == {"starter_fit"}  # answered: kept
    case = next(e for e in rows if e.slot == "case_market_sizing")
    assert case.model_used == "claude-sonnet-5-5" and case.generation_mode == "claude_code"
    assert any(s["verified"] and s["url"] == SEARCH_URL for s in case.sources)

    by_slot = {}
    for call in calls(fake_cli):
        if arg(call, "--system-prompt").startswith("Tu es un senior manager"):
            by_slot[call["stdin"].split("- slot : ")[1].split()[0]] = call
    assert arg(by_slot["case_market_sizing"], "--tools") == "WebSearch"
    assert arg(by_slot["case_market_sizing"], "--allowedTools") == "WebSearch"
    assert arg(by_slot["brainteaser_1"], "--tools") == ""
    assert arg(by_slot["brainteaser_1"], "--effort") == "high"
    stored = (await db.execute(select(CronRun).where(CronRun.job == "claude_code"))).scalar_one()
    assert stored.model == "sonnet"


async def test_without_token_nor_key_the_day_still_gets_the_starter_pack(user_client, db):
    _, user = user_client
    day = today_for(user)
    assert provider.provider() is None
    await service.ensure_day(db, day)
    assert await service.count_exercises(db, day) == 7


def pack_item(slot: str, type_: str, difficulty: int) -> dict:
    is_case = type_ != "brainteaser"
    return {
        "slot": slot,
        "model": "pack test",
        "spec": {
            "slot": slot,
            "type": type_,
            "difficulty": difficulty,
            "language": "fr",
            "style": "wavestone",
            "sector": "banque" if is_case else "général",
            "web_search": is_case,
        },
        "exercise": exercise_json(type_, title=f"Bonus {slot}"),
        "search_urls": [SEARCH_URL] if is_case else [],
    }


async def test_bonus_pack_is_imported_once_and_shown_apart(user_client, db, tmp_path, fake_cli):
    client, user = user_client
    day = today_for(user)
    pack = [
        pack_item("bonustest_case_01", "market_sizing", 4),
        pack_item("bonustest_bt_01", "brainteaser", 2),
        {**pack_item("bonustest_bt_02", "brainteaser", 1), "exercise": {"title": "cassé"}},
    ]
    (tmp_path / "test.json").write_text(json.dumps(pack))
    assert await bonus.import_packs(db, day, tmp_path) == 2  # the broken one is refused
    assert await bonus.import_packs(db, day, tmp_path) == 0  # idempotent
    await service.insert_starter_pack(db, day)
    assert await service.count_exercises(db, day) == 7  # the bonus does not make a day

    cards = await today_service.build_cards(db, user.id, day)
    bonus_cards = [c for c in cards if c.bonus]
    assert [c.exercise.slot for c in bonus_cards] == ["bonustest_bt_01", "bonustest_case_01"]
    assert cards[-2:] == bonus_cards  # after the day's own cards
    assert bonus_cards[0].as_dict()["due_label"] == "Bonus · quand tu veux"
    assert today_service.remaining(cards) == 7

    for c in cards:
        if not c.bonus:
            resp = await client.post(
                "/api/grade",
                json={
                    "exercise_id": str(c.exercise.id),
                    "answer_text": "Une réponse assez longue.",
                },
            )
            assert resp.status_code == 200, resp.text
    target = bonus_cards[0].exercise
    resp = await client.post(
        "/api/grade",
        json={"exercise_id": str(target.id), "answer_text": "Une réponse assez longue."},
    )
    assert resp.status_code == 200
    cards = await today_service.build_cards(db, user.id, day)
    assert today_service.day_complete(cards)  # the other bonus is still open
    assert next(c for c in cards if c.exercise.id == target.id).done  # still shown today

    tomorrow = await today_service.build_cards(db, user.id, day + timedelta(days=1))
    assert [c.exercise.slot for c in tomorrow if c.bonus] == ["bonustest_case_01"]


def test_the_shipped_bonus_pack_is_valid():
    items = bonus.load_packs()
    if not items:
        pytest.skip("no bonus pack shipped")
    assert len({i["slot"] for i in items}) == len(items)
    for item in items:
        bonus.validated(item)
