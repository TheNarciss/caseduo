"""Bonus packs: exercises written ahead, outside any day's plan (DEVIATIONS D15).

Each `packs/*.json` is a list of `{"slot", "spec", "exercise", "search_urls"}`. At boot,
every item whose slot is not in the base yet is checked by the same validator as a
generated exercise, then inserted for that day with generation_mode "bonus". The day
screen lists the bonus exercises not done yet after the day's own cards; they never
count for "journée complète" nor for the remaining badge.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Exercise
from ..generation import schema, service
from ..generation.planner import SlotSpec
from ..llm.messages import normalize_url

logger = logging.getLogger(__name__)

PACKS_DIR = Path(__file__).parent / "packs"


def load_packs(folder: Path = PACKS_DIR) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        items += json.loads(path.read_text(encoding="utf-8"))
    return items


def validated(item: dict[str, Any]) -> dict[str, Any]:
    """Exercise fields, as the nightly generation would insert them. Raises GenerationInvalid."""
    spec = SlotSpec(**item["spec"])
    urls = {normalize_url(u) for u in item.get("search_urls") or []}
    return schema.validate(item["exercise"], spec, search_urls=urls if spec.web_search else None)


async def import_packs(session: AsyncSession, day: date, folder: Path = PACKS_DIR) -> int:
    """Inserts the pack items not in the base yet (idempotent). Returns how many."""
    items = load_packs(folder)
    if not items:
        return 0
    slots = [item["slot"] for item in items]
    have = set(
        (await session.execute(select(Exercise.slot).where(Exercise.slot.in_(slots))))
        .scalars()
        .all()
    )
    inserted = 0
    for item in items:
        if item["slot"] in have:
            continue
        try:
            fields = validated(item)
        except ValueError as exc:
            logger.warning("Bonus %s rejected: %s", item["slot"], exc)
            continue
        inserted += int(
            await service.insert_exercise(
                session,
                day,
                item["slot"],
                fields,
                mode=service.BONUS_MODE,
                run_id=None,
                model=item.get("model"),
            )
        )
    await session.commit()
    if inserted:
        logger.info("Bonus pack: %d exercise(s) added on %s", inserted, day)
    return inserted
