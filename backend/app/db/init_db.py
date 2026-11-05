"""Schema migrations at startup, via an Alembic subprocess (same as Tangent).

We invoke alembic as a subprocess instead of calling `command.upgrade()`
directly: the latter nests an `asyncio.run()` inside FastAPI's event loop,
which deadlocks at startup (FastAPI #13008, Alembic #1606).
"""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# backend/ is two levels up from app/db/init_db.py
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


async def init_db() -> None:
    """Apply DB migrations to head. Idempotent; raises if alembic exits non-zero."""
    if not _ALEMBIC_INI.exists():
        logger.error("alembic.ini not found at %s, skipping migrations", _ALEMBIC_INI)
        return

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(_ALEMBIC_INI),
        "upgrade",
        "head",
        cwd=str(_BACKEND_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout_bytes, _ = await proc.communicate()
    output = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""

    if proc.returncode != 0:
        logger.error("Alembic migration failed (exit=%s):\n%s", proc.returncode, output)
        raise RuntimeError(f"Alembic upgrade failed with exit code {proc.returncode}")

    if output.strip():
        logger.info("Alembic output:\n%s", output.rstrip())
    logger.info("DB migrations applied (alembic upgrade head)")
