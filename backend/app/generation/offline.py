"""Validation of generated files without a database — what the night's Claude Code
session runs before pushing (`python -m app.nightly check`). Only pydantic is needed:
this module imports neither SQLAlchemy nor the Anthropic SDK."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..llm.messages import normalize_url
from . import schema
from .planner import SlotSpec

SPEC_FIELDS = tuple(asdict(SlotSpec("x", "fit", 1, "fr", "wavestone", "x", False)).keys())


def spec_dict(spec: SlotSpec) -> dict[str, Any]:
    return asdict(spec)


def spec_from(data: dict[str, Any]) -> SlotSpec:
    return SlotSpec(**{k: data[k] for k in SPEC_FIELDS if k in data})


def check_item(
    item: dict[str, Any],
    spec: SlotSpec,
    *,
    weaknesses: list[str],
    recent_titles: list[tuple[str, str]] | None,
) -> dict[str, Any]:
    """One generated file `{"exercise": {...}, "search_urls": [...]}` → validated fields.
    Raises GenerationInvalid."""
    exercise = item.get("exercise")
    if not isinstance(exercise, dict):
        raise schema.GenerationInvalid(
            'le fichier doit contenir {"exercise": {...}, "search_urls": [...]}'
        )
    urls = item.get("search_urls")
    return schema.validate(
        exercise,
        spec,
        search_urls={normalize_url(u) for u in urls} if isinstance(urls, list) else None,
        weaknesses=weaknesses,
        recent_titles=recent_titles,
    )


def check_against_plan(
    plan: dict[str, Any], items: dict[str, dict[str, Any]]
) -> dict[str, str | None]:
    """slot → None if valid, else the reason. Same rules as the import on the VM."""
    specs = {s["slot"]: spec_from(s) for s in plan["slots"]}
    recent = {t: [(x[0], x[1]) for x in v] for t, v in plan.get("recent_titles", {}).items()}
    report: dict[str, str | None] = {}
    for slot, item in items.items():
        spec = specs.get(slot)
        if spec is None:
            report[slot] = "slot absent du plan"
            continue
        try:
            check_item(
                item,
                spec,
                weaknesses=list(plan.get("weaknesses", [])),
                recent_titles=recent.get(spec.type),
            )
            report[slot] = None
        except schema.GenerationInvalid as exc:
            report[slot] = str(exc)
    return report
