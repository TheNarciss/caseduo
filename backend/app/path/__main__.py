"""`python -m app.path check <files…>` : validate units and item files, no database.

Prints one line per file (or per refused item): OK, or REFUS with the reason. Exit code 1
if anything is refused. Needs only pydantic, so content writers can run it anywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .schema import check_files


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "check":
        print("usage : python -m app.path check <fichier.json> [...]", file=sys.stderr)
        return 2
    results = check_files([Path(p) for p in argv[1:]])
    bad = 0
    for name, verdict in results:
        print(f"{verdict:<6} {name}" if verdict == "OK" else f"{name} : {verdict}")
        bad += verdict != "OK"
    print(f"{len(results) - bad} OK, {bad} refusé(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
