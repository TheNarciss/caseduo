"""The prompt lab writes stored vs new versions and inserts nothing."""

from datetime import date

import pytest
from sqlalchemy import func, select

from app import prompt_lab
from app.db.models import Exercise
from app.generation import service
from app.llm import anthropic_client
from tests.fake_llm import FakeClient

pytestmark = pytest.mark.integration


async def test_generate_writes_files_without_inserting(db, tmp_path):
    client = FakeClient()
    anthropic_client.set_client_for_testing(client)
    try:
        day = date(2026, 11, 12)
        await service.generate_day_sync(db, day, only=["fit"])
        before = (await db.execute(select(func.count()).select_from(Exercise))).scalar()
        await prompt_lab.cmd_generate(day, ["fit", "case_cadrage"], tmp_path)
        after = (await db.execute(select(func.count()).select_from(Exercise))).scalar()
    finally:
        anthropic_client.set_client_for_testing(None)
    assert before == after
    folder = tmp_path / day.isoformat()
    assert (folder / "fit.stored.md").exists() and (folder / "fit.new.md").exists()
    assert (folder / "case_cadrage.new.json").exists()
    assert "## Corrigé" in (folder / "fit.new.md").read_text()
