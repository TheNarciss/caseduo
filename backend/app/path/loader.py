"""Loading the repository's content (content/path/) into the base at startup, idempotently.

Units and nodes are upserted; nodes no longer in the files are kept but turned inactive.
Items are upserted when their content hash changes, so an edit in the repository reaches
the app at the next deployment without touching the users' results.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PathItem, PathNode, PathUnit
from . import schema

logger = logging.getLogger(__name__)

_REPO_CONTENT = Path(__file__).resolve().parents[3] / "content" / "path"


def content_dir() -> Path:
    configured = os.getenv("CONTENT_DIR")
    if configured and (Path(configured) / "path" / "units").exists():
        return Path(configured) / "path"
    return _REPO_CONTENT


def item_hash(item: schema.Item) -> str:
    raw = json.dumps(item.model_dump(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


async def import_content(session: AsyncSession, folder: Path | None = None) -> dict[str, int]:
    """Upserts units, nodes and items. Returns counts. Raises ContentInvalid on bad files."""
    folder = folder or content_dir()
    units = schema.load_units(folder / "units") if (folder / "units").exists() else []
    items = schema.load_items(folder / "items") if (folder / "items").exists() else []
    known_nodes = {n.code for u in units for n in u.nodes}
    skills = known_nodes | {u.code for u in units}
    for it in items:
        if it.skill not in skills:
            raise schema.ContentInvalid(f"item {it.id} : compétence inconnue {it.skill!r}")

    for unit in units:
        await session.execute(
            pg_insert(PathUnit)
            .values(
                code=unit.code,
                order=unit.order,
                track=unit.track,
                title=unit.title,
                subtitle=unit.subtitle,
                symbol=unit.symbol,
            )
            .on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "order": unit.order,
                    "track": unit.track,
                    "title": unit.title,
                    "subtitle": unit.subtitle,
                    "symbol": unit.symbol,
                },
            )
        )
        for position, node in enumerate(unit.nodes):
            values = {
                "code": node.code,
                "unit_code": unit.code,
                "position": position,
                "kind": node.kind,
                "title": node.title,
                "objective": node.objective,
                "errors": node.errors,
                "formats": node.formats,
                "items": node.items,
                "applied_type": node.applied_type,
                "active": True,
            }
            await session.execute(
                pg_insert(PathNode)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["code"], set_={k: v for k, v in values.items() if k != "code"}
                )
            )
    if known_nodes:
        await session.execute(
            update(PathNode).where(PathNode.code.not_in(known_nodes)).values(active=False)
        )

    existing: dict[str, str] = {
        row[0]: row[1]
        for row in (await session.execute(select(PathItem.id, PathItem.content_hash))).all()
    }
    changed = 0
    for it in items:
        digest = item_hash(it)
        if existing.get(it.id) == digest:
            continue
        changed += 1
        values = {
            "id": it.id,
            "format": it.format,
            "skill": it.skill,
            "unit_code": it.id.split(".")[0],
            "difficulty": it.difficulty,
            "lang": it.lang,
            "sector": it.sector,
            "stem": it.stem,
            "media": it.media.model_dump() if it.media else None,
            "explanation": it.explanation,
            "payload": it.payload,
            "tags": it.tags,
            "source": "repo",
            "content_hash": digest,
        }
        await session.execute(
            pg_insert(PathItem)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["id"], set_={k: v for k, v in values.items() if k != "id"}
            )
        )
    await session.commit()
    counts = {
        "units": len(units),
        "nodes": len(known_nodes),
        "items": len(items),
        "changed": changed,
    }
    if units:
        logger.info("Parcours content: %s", counts)
    return counts
