"""The night's generation through GitHub: plan export, offline check, import."""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models import CronRun, Exercise
from app.generation.offline import check_against_plan
from app.generation.planner import plan_day
from app.services import nightly
from tests.fake_llm import SEARCH_URL, exercise_json

pytestmark = pytest.mark.integration

DAY = date(2026, 11, 13)  # a Friday
BACKEND = Path(__file__).resolve().parents[2]


def item(type_: str, **kw) -> dict:
    return {"exercise": exercise_json(type_, **kw), "search_urls": [SEARCH_URL]}


async def test_plan_payload(db):
    plan = await nightly.plan_payload(db, DAY)
    assert plan["date"] == DAY.isoformat() and plan["weekday"] == "vendredi"
    assert "senior manager de la practice Data & IA" in plan["system_prompt"]
    assert {s["slot"] for s in plan["slots"]} == {s.slot for s in plan_day(DAY).slots}
    cadrage = next(s for s in plan["slots"] if s["slot"] == "case_cadrage")
    assert "- slot : case_cadrage" in cadrage["user_message"] and cadrage["web_search"] is True
    json.dumps(plan)  # serialisable as is


async def test_offline_check_matches_the_import(db):
    plan = await nightly.plan_payload(db, DAY)
    bad = item("cadrage")
    bad["exercise"]["rubric"][0]["weight"] += 5
    report = check_against_plan(plan, {"case_cadrage": item("cadrage"), "fit": bad, "nope": {}})
    assert report["case_cadrage"] is None
    assert "type" in report["fit"]  # a cadrage sent as fit
    assert report["nope"] == "slot absent du plan"

    result = await nightly.import_items(db, DAY, {"case_cadrage": item("cadrage"), "fit": bad})
    assert result["results"]["case_cadrage"] == "inséré"
    assert result["results"]["fit"].startswith("refusé")
    assert result["status"] == "partial" and "fit" in result["missing"]
    again = await nightly.import_items(db, DAY, {"case_cadrage": item("cadrage")})
    assert again["results"]["case_cadrage"] == "déjà présent"
    ex = (await db.execute(select(Exercise).where(Exercise.slot == "case_cadrage"))).scalar_one()
    assert ex.generation_mode == "claude_code" and ex.sources[0]["verified"] is True
    runs = (await db.execute(select(CronRun).where(CronRun.job == "claude_code"))).scalars().all()
    assert len(runs) == 1 and runs[0].n_succeeded == 1 and runs[0].cost_usd == 0


async def test_check_cli_needs_no_database(db, tmp_path):
    plan = await nightly.plan_payload(db, DAY)
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    folder = tmp_path / "gen"
    folder.mkdir()
    (folder / "case_market_sizing.json").write_text(json.dumps(item("market_sizing")))
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.nightly",
            "check",
            str(folder),
            "--plan",
            str(tmp_path / "plan.json"),
        ],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(BACKEND)},  # no DATABASE_URL, no JWT_SECRET
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK    case_market_sizing" in proc.stdout and "MANQUE fit" in proc.stdout
