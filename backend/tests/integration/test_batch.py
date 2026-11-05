"""Batch generation: submit, poll, insert, redo failures in sync, 05:30 fallback."""

from datetime import date, datetime

import pytest
from sqlalchemy import func, select

from app.db.models import CronRun, Exercise
from app.generation import batch, jobs, service
from app.generation.planner import plan_day
from app.llm import anthropic_client
from tests.fake_llm import FakeClient, attach_batches

pytestmark = pytest.mark.integration

DAY = date(2026, 11, 10)  # a Tuesday


@pytest.fixture
def fake():
    client = FakeClient()
    batches = attach_batches(client)
    anthropic_client.set_client_for_testing(client)
    yield client, batches
    anthropic_client.set_client_for_testing(None)


async def n_exercises(db, day=DAY):
    stmt = select(func.count()).select_from(Exercise).where(Exercise.date == day)
    return (await db.execute(stmt)).scalar()


def test_custom_id_round_trip():
    cid = batch.custom_id(DAY, "case_market_sizing")
    assert cid == "gen_20261110_case_market_sizing"
    assert batch.parse_custom_id(cid) == (DAY, "case_market_sizing")
    assert batch.parse_custom_id("gap_x") is None


async def test_submit_poll_insert(db, fake):
    _client, batches = fake
    run = await batch.submit_batch(db, DAY)
    n = len(plan_day(DAY).slots)
    assert run.status == "in_progress" and run.n_requests == n and run.estimated_cost_usd > 0
    assert await batch.submit_batch(db, DAY) is None  # already in flight

    assert await batch.poll_batches(db) == 0  # Anthropic still processing
    assert await n_exercises(db) == 0

    batches.status[run.anthropic_batch_id] = "ended"
    assert await batch.poll_batches(db) == 1
    assert await n_exercises(db) == n
    stored = (await db.execute(select(CronRun).where(CronRun.id == run.id))).scalar_one()
    assert stored.status == "ended" and stored.n_succeeded == n
    assert stored.output_tokens > 0 and stored.cost_usd > 0
    modes = set((await db.execute(select(Exercise.generation_mode))).scalars())
    assert modes == {"batch"}
    assert await batch.submit_batch(db, DAY) is None  # complete


async def test_failed_batch_slots_are_redone_synchronously(db, fake):
    _client, batches = fake
    run = await batch.submit_batch(db, DAY)
    batches.errored = {"fit"}
    batches.status[run.anthropic_batch_id] = "ended"
    await batch.poll_batches(db)
    assert await n_exercises(db) == len(plan_day(DAY).slots)
    fit = (await db.execute(select(Exercise).where(Exercise.slot == "fit"))).scalar_one()
    assert fit.generation_mode == "sync"


async def test_fallback_cancels_and_goes_sync(db, fake, monkeypatch):
    _client, batches = fake
    monkeypatch.setattr(jobs, "now_local", lambda: datetime(2026, 11, 9, 5, 30, tzinfo=jobs.TZ))
    run = await batch.submit_batch(db, DAY)
    await jobs.job_fallback()
    assert batches.cancelled == [run.anthropic_batch_id]
    assert await n_exercises(db) == len(plan_day(DAY).slots)
    assert await n_exercises(db, date(2026, 11, 9)) > 0  # today checked too
    # the cancelled batch ends later: its results are read, nothing duplicated
    batches.status[run.anthropic_batch_id] = "ended"
    await batch.poll_batches(db)
    assert await n_exercises(db) == len(plan_day(DAY).slots)


async def test_without_key_the_day_still_gets_the_starter_pack(db, monkeypatch):
    anthropic_client.set_client_for_testing(None)
    monkeypatch.setattr(jobs, "now_local", lambda: datetime(2026, 11, 9, 5, 30, tzinfo=jobs.TZ))
    await jobs.job_fallback()
    assert await n_exercises(db) > 0
    assert await n_exercises(db, date(2026, 11, 9)) > 0


def test_missed_jobs_detection():
    tz = jobs.TZ
    at = jobs.SUBMIT_AT
    assert not jobs.missed(datetime(2026, 11, 9, 2, 0, tzinfo=tz), at, None)
    assert jobs.missed(datetime(2026, 11, 9, 4, 0, tzinfo=tz), at, None)
    assert not jobs.missed(
        datetime(2026, 11, 9, 4, 0, tzinfo=tz), at, datetime(2026, 11, 9, 3, 0, 5, tzinfo=tz)
    )
    assert jobs.missed(
        datetime(2026, 11, 9, 4, 0, tzinfo=tz), at, datetime(2026, 11, 8, 3, 0, tzinfo=tz)
    )


async def test_budget_refuses_batch(db, fake, monkeypatch):
    from app.llm import cost_tracker

    monkeypatch.setattr(cost_tracker, "DAILY_CAP_USD", 0.0)
    assert await batch.submit_batch(db, DAY) is None


async def test_ensure_day_noop_when_complete(db, fake):
    await service.generate_day_sync(db, DAY)
    calls = len(fake[0].calls)
    await service.ensure_day(db, DAY)
    assert len(fake[0].calls) == calls
