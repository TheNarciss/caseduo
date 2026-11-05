"""Strict validation of a generated exercise before it is inserted.

The model answers JSON; we validate it with Pydantic, then check what a
schema cannot express: rubric keys allowed for the type, weights summing to
100, 3–6 facts for a case, every real figure sourced, parts count, no
invented URL. Small mistakes are repaired (a fact without URL becomes an
hypothesis, the planned type/language/difficulty win); anything else raises
`GenerationInvalid` and the slot is retried.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from ..catalog import CASE_TYPES, CRITERIA, RUBRIC_KEYS, allowed_rubric_keys, criterion_label
from ..llm.messages import normalize_url
from .planner import SlotSpec


class GenerationInvalid(ValueError):
    """The model's answer cannot be inserted as is."""


class Fact(BaseModel):
    label: str = Field(min_length=1, max_length=300)
    value: str = Field(min_length=1, max_length=300)
    source_url: str | None = None
    hypothesis: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def _stringify(cls, v: Any) -> Any:
        return str(v) if isinstance(v, int | float) else v


class Document(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)


class ContextData(BaseModel):
    facts: list[Fact] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)


class Levels(BaseModel):
    zero: str = Field(alias="0", min_length=1)
    one: str = Field(alias="1", min_length=1)
    two: str = Field(alias="2", min_length=1)


class Criterion(BaseModel):
    key: str
    label: str = ""
    weight: int = Field(gt=0, le=100)
    levels: Levels


class Source(BaseModel):
    url: str = Field(min_length=8)
    title: str = ""


class Part(BaseModel):
    question: str = Field(min_length=5)
    data: str | None = None


class GeneratedExercise(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    type: str
    style: str = "wavestone"
    language: str = "fr"
    difficulty: int = Field(ge=1, le=5)
    sector: str = ""
    prompt: str = Field(min_length=40)
    parts: list[Part] | None = None
    context_data: ContextData = Field(default_factory=ContextData)
    model_answer: str = Field(min_length=80)
    rubric: list[Criterion] = Field(min_length=4, max_length=6)
    sources: list[Source] = Field(default_factory=list)
    targets_weakness: list[str] = Field(default_factory=list)
    estimated_minutes: int | None = Field(default=None, ge=1, le=240)


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def is_duplicate(title: str, sector: str, recent: list[tuple[str, str]]) -> bool:
    """Same sector and (nearly) the same title as an exercise of the last 60 days."""
    norm = normalize_title(title)
    for other_title, other_sector in recent:
        if other_sector != sector:
            continue
        other = normalize_title(other_title)
        if norm == other or SequenceMatcher(None, norm, other).ratio() > 0.85:
            return True
    return False


def validate(
    data: dict[str, Any],
    spec: SlotSpec,
    *,
    search_urls: set[str] | None = None,
    weaknesses: list[str] | None = None,
    recent_titles: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Validated, repaired fields for an `Exercise` row. Raises GenerationInvalid."""
    try:
        ex = GeneratedExercise.model_validate(data)
    except ValidationError as exc:
        raise GenerationInvalid(f"schéma : {exc.errors()[:3]}") from exc

    if ex.type != spec.type:
        raise GenerationInvalid(f"type {ex.type!r} au lieu de {spec.type!r}")

    # ── Rubric ───────────────────────────────────────────────────────────
    allowed = allowed_rubric_keys(spec.type, spec.style)
    keys = [c.key for c in ex.rubric]
    if len(set(keys)) != len(keys):
        raise GenerationInvalid(f"critères en double : {keys}")
    unknown = set(keys) - allowed
    if unknown:
        raise GenerationInvalid(f"critères non autorisés pour {spec.type}: {sorted(unknown)}")
    required = set(RUBRIC_KEYS[spec.type])
    if spec.type in (*CASE_TYPES, "fit", "cadrage_home") and not required <= set(keys):
        raise GenerationInvalid(f"critères manquants : {sorted(required - set(keys))}")
    if sum(c.weight for c in ex.rubric) != 100:
        raise GenerationInvalid(f"poids = {sum(c.weight for c in ex.rubric)}, pas 100")

    # ── Facts and sources ────────────────────────────────────────────────
    sources = {normalize_url(s.url): s for s in ex.sources}
    facts = []
    for fact in ex.context_data.facts:
        url = fact.source_url.strip() if fact.source_url else None
        if not url or not url.startswith("http"):
            fact = fact.model_copy(update={"source_url": None, "hypothesis": True})
        elif normalize_url(url) not in sources:
            sources[normalize_url(url)] = Source(url=url, title=url)
        facts.append(fact)
    if spec.type in (*CASE_TYPES, "cadrage_home") and not 3 <= len(facts) <= 6:
        raise GenerationInvalid(f"{len(facts)} chiffres dans context_data (3 à 6 attendus)")
    if spec.type == "cadrage_home" and not 2 <= len(ex.context_data.documents) <= 3:
        raise GenerationInvalid("cadrage_home : 2 ou 3 documents de contexte attendus")

    verified = {u for u in (search_urls or set())}
    source_list = [
        {"url": s.url, "title": s.title or s.url, "verified": key in verified}
        for key, s in sources.items()
    ]
    if search_urls is not None and spec.web_search and verified:
        invented = [s for s in source_list if not s["verified"]]
        if invented and len(invented) == len(source_list):
            raise GenerationInvalid("aucune source ne vient de la recherche web")

    # ── Parts ────────────────────────────────────────────────────────────
    parts = None
    if spec.parts:
        if not ex.parts or len(ex.parts) != spec.parts:
            raise GenerationInvalid(f"{len(ex.parts or [])} parties au lieu de {spec.parts}")
        parts = [p.model_dump() for p in ex.parts]

    # ── Weaknesses, duplicates ───────────────────────────────────────────
    targets = [k for k in ex.targets_weakness if k in CRITERIA]
    if spec.target_weakness and not targets and weaknesses:
        targets = list(weaknesses)
    if recent_titles and is_duplicate(ex.title, spec.sector, recent_titles):
        raise GenerationInvalid(f"doublon d'un exercice récent : {ex.title!r}")

    rubric = [
        {
            "key": c.key,
            "label": criterion_label(c.key),
            "weight": c.weight,
            "levels": {"0": c.levels.zero, "1": c.levels.one, "2": c.levels.two},
        }
        for c in ex.rubric
    ]
    return {
        "type": spec.type,
        "style": spec.style,
        "language": spec.language,
        "difficulty": spec.difficulty,
        "sector": spec.sector,
        "title": ex.title.strip()[:200],
        "prompt": ex.prompt.strip(),
        "parts": parts,
        "context_data": {
            "facts": [f.model_dump() for f in facts],
            "constraints": ex.context_data.constraints,
            "documents": [d.model_dump() for d in ex.context_data.documents],
        },
        "model_answer": ex.model_answer.strip(),
        "rubric": rubric,
        "sources": source_list,
        "targets_weakness": targets,
        "estimated_minutes": ex.estimated_minutes or spec.estimated_minutes,
    }
