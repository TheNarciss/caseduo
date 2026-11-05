"""Sync generation end to end with a fake Claude: insert, idempotence, retries,
cron_runs logging, starter pack when generation is impossible."""

from datetime import date

import pytest
from sqlalchemy import func, select

from app.db.models import CronRun, Exercise, LLMDailyCost
from app.generation import service
from app.generation.planner import plan_day
from app.llm import anthropic_client
from tests.fake_llm import FakeClient

pytestmark = pytest.mark.integration

DAY = date(2026, 11, 6)  # a Friday: 5 cases, fit, 2 brainteasers, cadrage_home


@pytest.fixture
def fake_client():
    client = FakeClient()
    anthropic_client.set_client_for_testing(client)
    yield client
    anthropic_client.set_client_for_testing(None)


async def count(db, day):
    return (
        await db.execute(select(func.count()).select_from(Exercise).where(Exercise.date == day))
    ).scalar()


async def test_generate_day_sync_inserts_every_slot_once(db, fake_client):
    run = await service.generate_day_sync(db, DAY, job="seed")
    n = len(plan_day(DAY).slots)
    assert run.n_succeeded == n and run.status == "ended"
    assert await count(db, DAY) == n
    assert run.input_tokens > 0 and run.cost_usd > 0
    assert (await db.execute(select(LLMDailyCost.cumulative_cost_usd))).scalar() > 0
    # cases use web search, brainteasers and fit do not
    with_tools = [c for c in fake_client.calls if "tools" in c]
    assert len(with_tools) == 6  # 5 cases + cadrage_home on a Friday
    # system prompt is cached
    assert fake_client.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}
    # idempotent
    assert await service.generate_day_sync(db, DAY) is None
    assert len(fake_client.calls) == n


async def test_failed_slot_is_retried_twice_and_logged(db):
    client = FakeClient(fail_slots={"fit"})
    anthropic_client.set_client_for_testing(client)
    try:
        run = await service.generate_day_sync(db, DAY)
    finally:
        anthropic_client.set_client_for_testing(None)
    fit_calls = [c for c in client.calls if "slot : fit" in c["messages"][0]["content"]]
    assert len(fit_calls) == 3
    assert run.status == "partial" and run.n_failed == 1
    assert len([e for e in run.errors if e.get("slot") == "fit"]) == 3
    stored = (await db.execute(select(CronRun).where(CronRun.id == run.id))).scalar_one()
    assert stored.errors


async def test_ensure_day_falls_back_to_starter_pack_without_key(db):
    anthropic_client.set_client_for_testing(None)
    await service.ensure_day(db, DAY)
    rows = (await db.execute(select(Exercise).where(Exercise.date == DAY))).scalars().all()
    assert rows and all(r.generation_mode == "starter" for r in rows)
