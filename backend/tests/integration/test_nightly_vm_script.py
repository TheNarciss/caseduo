"""ops/nightly_import.py as the VM runs it, with a fake `docker` that calls the real CLI."""

import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.db.models import Exercise
from tests.fake_llm import SEARCH_URL, exercise_json

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "backend"


def run_script(nightly: Path, bin_dir: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    return subprocess.run(
        [sys.executable, str(REPO / "ops/nightly_import.py"), str(nightly), str(REPO)],
        capture_output=True,
        text=True,
        env=env,
    )


async def test_vm_script_imports_once_and_writes_results(db, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(f"#!/bin/sh\ncd {BACKEND} && exec {sys.executable} -m app.nightly import\n")
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)

    tomorrow = (datetime.now(ZoneInfo("Asia/Singapore")).date() + timedelta(days=1)).isoformat()
    folder = tmp_path / "nightly" / "generated" / tomorrow
    folder.mkdir(parents=True)
    (folder / "case_market_sizing.json").write_text(
        json.dumps({"exercise": exercise_json("market_sizing"), "search_urls": [SEARCH_URL]})
    )
    (folder / "fit.json").write_text("{pas du json")
    old = tmp_path / "nightly" / "generated" / "2020-01-01"
    old.mkdir()
    (old / "fit.json").write_text("{}")

    first = run_script(tmp_path / "nightly", bin_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    assert f"{tomorrow}: 1 inséré(s)" in first.stdout and "fit: refusé" in first.stdout
    result = json.loads((tmp_path / "nightly" / "results" / f"{tomorrow}.json").read_text())
    assert result["results"]["case_market_sizing"] == "inséré" and result["input_hash"]
    assert not (tmp_path / "nightly" / "results" / "2020-01-01.json").exists()

    second = run_script(tmp_path / "nightly", bin_dir)
    assert "Rien de nouveau" in second.stdout
    rows = (
        (await db.execute(select(Exercise).where(Exercise.slot == "case_market_sizing")))
        .scalars()
        .all()
    )
    assert len(rows) == 1 and rows[0].generation_mode == "claude_code"
