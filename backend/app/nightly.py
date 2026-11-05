"""CLI of the night's generation through GitHub (services/nightly.py, DEVIATIONS D13).

On the VM (GitHub Actions, inside the backend container):
    python -m app.nightly plan [--date YYYY-MM-DD]        → plan JSON on stdout (default: tomorrow)
    python -m app.nightly import < bundle.json            → results JSON on stdout

In the Claude Code session (no database, only pydantic needed):
    python -m app.nightly check DIR --plan PLAN.json      → exit 1 if a file would be refused

A bundle is {"date": "...", "items": {"<slot>": {"exercise": {...}, "search_urls": [...]}}};
DIR holds one `<slot>.json` per exercise, same shape as an item.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def _tomorrow() -> date:
    from .llm.cost_tracker import today_jobs_tz

    return today_jobs_tz() + timedelta(days=1)


async def _plan(day: date) -> dict[str, Any]:
    from .db import async_session_factory
    from .services import nightly

    async with async_session_factory() as session:
        return await nightly.plan_payload(session, day)


async def _import(bundle: dict[str, Any]) -> dict[str, Any]:
    from .db import async_session_factory
    from .services import nightly

    async with async_session_factory() as session:
        return await nightly.import_items(
            session, date.fromisoformat(bundle["date"]), bundle.get("items", {})
        )


def read_dir(folder: Path) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.json")):
        items[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return items


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.nightly")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--date", type=date.fromisoformat)
    i = sub.add_parser("import")
    i.add_argument("bundle", nargs="?", default="-")
    c = sub.add_parser("check")
    c.add_argument("folder", type=Path)
    c.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()

    if args.cmd == "plan":
        out = asyncio.run(_plan(args.date or _tomorrow()))
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    elif args.cmd == "import":
        raw = sys.stdin.read() if args.bundle == "-" else Path(args.bundle).read_text()
        out = asyncio.run(_import(json.loads(raw)))
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    else:
        from .generation.offline import check_against_plan

        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        report = check_against_plan(plan, read_dir(args.folder))
        for slot, error in sorted(report.items()):
            print(
                f"{'OK   ' if error is None else 'REFUS'} {slot}" + (f" — {error}" if error else "")
            )
        missing = sorted({s["slot"] for s in plan["slots"]} - set(report))
        for slot in missing:
            print(f"MANQUE {slot}")
        sys.exit(1 if any(report.values()) else 0)


if __name__ == "__main__":
    main()
