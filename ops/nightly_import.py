#!/usr/bin/env python3
"""Run by .github/workflows/nightly-import.yml on the VM (host Python, stdlib only).

For each `generated/<date>/` of the `nightly` checkout, from today on: if the files
changed since the last import (hash), bundle them, pipe the bundle into
`python -m app.nightly import` inside the backend container, and write the answer
to `results/<date>.json`. Prints the dates it imported.

    python3 ops/nightly_import.py <nightly checkout> <project dir>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.prod.yml"]


def main() -> int:
    nightly, project = Path(sys.argv[1]), Path(sys.argv[2])
    today = datetime.now(ZoneInfo("Asia/Singapore")).date().isoformat()
    imported = []
    for folder in sorted((nightly / "generated").glob("*/")):
        day = folder.name
        if day < today:
            continue
        files = sorted(folder.glob("*.json"))
        if not files:
            continue
        digest = hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()[:16]
        result_path = nightly / "results" / f"{day}.json"
        if result_path.exists() and json.loads(result_path.read_text()).get("input_hash") == digest:
            continue
        items = {}
        for path in files:
            try:
                items[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                items[path.stem] = {"exercise": None, "json_error": str(exc)}
        bundle = json.dumps({"date": day, "items": items}, ensure_ascii=False)
        proc = subprocess.run(
            [*COMPOSE, "exec", "-T", "backend", "python", "-m", "app.nightly", "import"],
            input=bundle,
            capture_output=True,
            text=True,
            cwd=project,
        )
        if proc.returncode != 0:
            print(f"::error::import {day} failed: {proc.stderr[-2000:]}")
            return 1
        result = json.loads(proc.stdout)
        result["input_hash"] = digest
        result_path.parent.mkdir(exist_ok=True)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        inserted = sum(1 for v in result["results"].values() if v == "inséré")
        print(f"{day}: {inserted} inséré(s), statut {result['status']}, manquants {len(result['missing'])}")
        for slot, outcome in result["results"].items():
            if outcome.startswith("refusé"):
                print(f"  {slot}: {outcome}")
        imported.append(day)
    if not imported:
        print("Rien de nouveau à importer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
