"""The Parcours' content: units, lessons (nodes) and items, with their validator.

Content lives in the repository as JSON (`content/path/units/*.json`, `content/path/items/*.json`),
is validated here (pydantic, no database), and loaded into the base at startup. The same
validator checks what the generator writes (`python -m app.path check <files>`), so an item
that reaches the app always has exactly one correct answer, an explanation, distractors that
say why they are wrong, and numbers that recompute.

Formats (16 graded on the phone, deterministically, plus one oral item graded by Claude):

| format            | payload                                   | graded by            |
|-------------------|-------------------------------------------|----------------------|
| concept_card      | screens                                   | nothing (read)       |
| choose_structure  | options / correct (cards: mini trees)     | option == correct    |
| pick_so_what      | options / correct + media (chart, table)  | option == correct    |
| first_question    | options / correct                         | option == correct    |
| tree_complete     | options / correct + media (tree)          | option == correct    |
| swipe_valid       | cards (valid / reason)                    | ratio ≥ pass_ratio   |
| spot_error        | lines / wrong_line / fix                  | line == wrong_line   |
| order_steps       | tiles / solution / distractors            | sequence == solution |
| synth_order       | tiles / solution / distractors            | sequence == solution |
| headline_tiles    | tiles / solution / distractors            | sequence == solution |
| mental_math       | questions (computation, tolerance)        | within tolerance     |
| estimate_range    | range / slider                            | lo ≤ x ≤ hi          |
| two_step_calc     | formulas / correct_formula + computation  | both                 |
| fill_blank        | text with {{n}} / slots                   | every slot           |
| mece_sort         | buckets / items                           | every item           |
| match_pairs       | pairs                                     | every pair           |
| oral_prompt       | seconds / rubric / model_answer           | Claude (transcript)  |
"""

from __future__ import annotations

import ast
import json
import operator
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

FORMATS = (
    "concept_card",
    "choose_structure",
    "pick_so_what",
    "first_question",
    "tree_complete",
    "swipe_valid",
    "spot_error",
    "order_steps",
    "synth_order",
    "headline_tiles",
    "mental_math",
    "estimate_range",
    "two_step_calc",
    "fill_blank",
    "mece_sort",
    "match_pairs",
    "oral_prompt",
)
CHOICE_FORMATS = ("choose_structure", "pick_so_what", "first_question", "tree_complete")
TILE_FORMATS = ("order_steps", "synth_order", "headline_tiles")
NODE_KINDS = ("lesson", "review", "applied", "checkpoint", "legendary")
TRACKS = ("common", "transfo", "strat", "finance")
SECTORS = (
    "banque",
    "assurance",
    "retail",
    "énergie",
    "santé",
    "secteur public",
    "industrie",
    "télécoms",
    "transport",
    "luxe",
    "tech",
    "général",
)
BANNED = ("toutes les réponses", "aucune des réponses", "toutes ces réponses", "all of the above")

MAX_STEM = 320
MAX_EXPLANATION = 180
MAX_OPTION = 160


class ContentInvalid(ValueError):
    """An item or a unit that must not reach the app, with the reason."""


# ── Pieces ─────────────────────────────────────────────────────────────────


class Option(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=MAX_OPTION)
    why_wrong: str | None = Field(default=None, max_length=MAX_EXPLANATION)


class ChoicePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    options: list[Option] = Field(min_length=2, max_length=4)
    correct: str
    shuffle: bool = True


class SwipeCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=MAX_OPTION)
    valid: bool
    reason: str = Field(min_length=1, max_length=MAX_EXPLANATION)


class SwipePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cards: list[SwipeCard] = Field(min_length=4, max_length=8)
    pass_ratio: float = Field(default=0.8, ge=0.5, le=1.0)


class Line(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=MAX_OPTION)


class SpotErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lines: list[Line] = Field(min_length=3, max_length=6)
    wrong_line: str
    fix: str = Field(min_length=1, max_length=MAX_EXPLANATION)


class Tile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=MAX_OPTION)


class TilesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tiles: list[Tile] = Field(min_length=3, max_length=12)
    solution: list[str] = Field(min_length=3, max_length=12)
    distractors: list[str] = Field(default_factory=list, max_length=4)
    accepted: list[list[str]] = Field(default_factory=list, max_length=4)


class MathQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=8)
    stem: str = Field(min_length=1, max_length=MAX_STEM)
    computation: str = Field(min_length=1, max_length=120)
    answer: float
    unit: str = Field(default="", max_length=12)
    tolerance_pct: float = Field(default=3.0, ge=0, le=25)
    hint: str | None = Field(default=None, max_length=MAX_EXPLANATION)


class MentalMathPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[MathQuestion] = Field(min_length=1, max_length=8)
    seconds: int = Field(default=90, ge=15, le=300)


class EstimatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    range: tuple[float, float]
    slider: tuple[float, float]
    unit: str = Field(default="", max_length=16)
    scale: Literal["log", "linear"] = "log"
    reference: str = Field(min_length=1, max_length=MAX_EXPLANATION)


class TwoStepPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    formulas: list[Option] = Field(min_length=2, max_length=4)
    correct_formula: str
    computation: str = Field(min_length=1, max_length=120)
    answer: float
    unit: str = Field(default="", max_length=12)
    tolerance_pct: float = Field(default=3.0, ge=0, le=25)


class Slot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(ge=1, le=4)
    options: list[str] = Field(min_length=2, max_length=4)
    correct: int = Field(ge=0, le=3)


class FillBlankPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_STEM)
    slots: list[Slot] = Field(min_length=1, max_length=4)


class Bucket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=12)
    label: str = Field(min_length=1, max_length=60)


class SortItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=MAX_OPTION)
    bucket: str


class MeceSortPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    buckets: list[Bucket] = Field(min_length=2, max_length=3)
    items: list[SortItem] = Field(min_length=4, max_length=8)


class Pair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left: str = Field(min_length=1, max_length=80)
    right: str = Field(min_length=1, max_length=120)


class MatchPairsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pairs: list[Pair] = Field(min_length=3, max_length=5)


class Screen(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=900)


class ConceptPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    screens: list[Screen] = Field(min_length=1, max_length=4)


class RubricLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=80)
    weight: int = Field(ge=1, le=5)


class OralPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seconds: int = Field(default=75, ge=30, le=180)
    rubric: list[RubricLine] = Field(min_length=2, max_length=5)
    model_answer: str = Field(min_length=1, max_length=900)


class Media(BaseModel):
    """A small chart, table or tree drawn by the app from data (no image)."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["bar", "line", "table", "tree"]
    title: str | None = Field(default=None, max_length=80)
    unit: str | None = Field(default=None, max_length=16)
    # bar / line: categories and one or two series
    categories: list[str] | None = Field(default=None, max_length=8)
    series: list[dict[str, Any]] | None = Field(default=None, max_length=2)
    # table: header row and rows
    header: list[str] | None = Field(default=None, max_length=5)
    rows: list[list[str]] | None = Field(default=None, max_length=6)
    # tree: root and children (one level, "?" marks the node to complete)
    root: str | None = Field(default=None, max_length=80)
    children: list[str] | None = Field(default=None, max_length=5)


PAYLOADS: dict[str, type[BaseModel]] = {
    "concept_card": ConceptPayload,
    "choose_structure": ChoicePayload,
    "pick_so_what": ChoicePayload,
    "first_question": ChoicePayload,
    "tree_complete": ChoicePayload,
    "swipe_valid": SwipePayload,
    "spot_error": SpotErrorPayload,
    "order_steps": TilesPayload,
    "synth_order": TilesPayload,
    "headline_tiles": TilesPayload,
    "mental_math": MentalMathPayload,
    "estimate_range": EstimatePayload,
    "two_step_calc": TwoStepPayload,
    "fill_blank": FillBlankPayload,
    "mece_sort": MeceSortPayload,
    "match_pairs": MatchPairsPayload,
    "oral_prompt": OralPayload,
}


# ── The item ───────────────────────────────────────────────────────────────


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9]+(\.[a-z0-9_]+)+$", max_length=64)
    format: Literal[FORMATS]  # type: ignore[valid-type]
    skill: str = Field(pattern=r"^[a-z0-9]+\.[a-z0-9_]+$", max_length=48)
    difficulty: int = Field(ge=1, le=5)
    lang: Literal["fr", "en"] = "fr"
    sector: str | None = None
    stem: str = Field(default="", max_length=MAX_STEM)
    media: Media | None = None
    explanation: str = Field(default="", max_length=MAX_EXPLANATION)
    payload: dict[str, Any]
    tags: list[str] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _check(self) -> Item:
        if self.sector is not None and self.sector not in SECTORS:
            raise ValueError(f"secteur inconnu : {self.sector!r}")
        if self.format != "concept_card" and not self.explanation.strip():
            raise ValueError("explication manquante (toujours montrée après la réponse)")
        if self.format not in ("concept_card", "mental_math") and not self.stem.strip():
            raise ValueError("énoncé manquant")
        lowered = json.dumps(self.payload, ensure_ascii=False).lower()
        for banned in BANNED:
            if banned in lowered:
                raise ValueError(f"formulation interdite : « {banned} »")
        try:
            parsed = PAYLOADS[self.format].model_validate(self.payload)
        except ValidationError as exc:
            raise ValueError(f"payload {self.format} : {exc.errors()[:2]}") from exc
        _check_payload(self.format, parsed, self.media)
        return self


def _check_payload(fmt: str, p: Any, media: Media | None) -> None:
    if fmt in CHOICE_FORMATS:
        ids = [o.id for o in p.options]
        if len(set(ids)) != len(ids):
            raise ValueError("identifiants d'options en double")
        if p.correct not in ids:
            raise ValueError("`correct` ne désigne aucune option")
        texts = [o.text.strip().lower() for o in p.options]
        if len(set(texts)) != len(texts):
            raise ValueError("deux options identiques")
        for a in texts:
            for b in texts:
                if a != b and len(a) > 12 and a in b:
                    raise ValueError("une option contient une autre")
        for o in p.options:
            if o.id != p.correct and not (o.why_wrong or "").strip():
                raise ValueError(f"option {o.id} : `why_wrong` manquant")
        lengths = [len(o.text) for o in p.options]
        correct_len = next(len(o.text) for o in p.options if o.id == p.correct)
        others = [n for o, n in zip(p.options, lengths, strict=True) if o.id != p.correct]
        if others and correct_len > 1.6 * max(others):
            raise ValueError("la bonne réponse est de loin la plus longue (indice gratuit)")
        if fmt == "pick_so_what" and media is None:
            raise ValueError("pick_so_what : il faut un graphique ou un tableau (media)")
        if fmt == "tree_complete" and (media is None or media.type != "tree"):
            raise ValueError("tree_complete : il faut un arbre (media.type = tree) avec un « ? »")
        if (
            fmt == "tree_complete"
            and media is not None
            and not any("?" in c for c in media.children or [])
        ):
            raise ValueError("tree_complete : un enfant doit contenir « ? » (le nœud à compléter)")
    elif fmt == "swipe_valid":
        ids = [c.id for c in p.cards]
        if len(set(ids)) != len(ids):
            raise ValueError("cartes en double")
        valid = sum(c.valid for c in p.cards)
        if valid == 0 or valid == len(p.cards):
            raise ValueError("il faut des cartes valides et des cartes invalides")
    elif fmt == "spot_error":
        ids = [line.id for line in p.lines]
        if len(set(ids)) != len(ids):
            raise ValueError("lignes en double")
        if p.wrong_line not in ids:
            raise ValueError("`wrong_line` ne désigne aucune ligne")
    elif fmt in TILE_FORMATS:
        ids = [t.id for t in p.tiles]
        if len(set(ids)) != len(ids):
            raise ValueError("tuiles en double")
        unknown = set(p.solution) - set(ids)
        if unknown:
            raise ValueError(f"solution : tuiles inconnues {sorted(unknown)}")
        if len(set(p.solution)) != len(p.solution):
            raise ValueError("solution : une tuile deux fois")
        if set(p.distractors) & set(p.solution):
            raise ValueError("une tuile intruse est aussi dans la solution")
        if set(p.solution) | set(p.distractors) != set(ids):
            raise ValueError("chaque tuile est soit dans la solution, soit intruse")
        for seq in p.accepted:
            if sorted(seq) != sorted(p.solution):
                raise ValueError("une séquence acceptée n'utilise pas les mêmes tuiles")
    elif fmt == "mental_math":
        ids = [q.id for q in p.questions]
        if len(set(ids)) != len(ids):
            raise ValueError("questions en double")
        for q in p.questions:
            _check_computation(q.computation, q.answer, q.id)
    elif fmt == "estimate_range":
        lo, hi = p.range
        smin, smax = p.slider
        if not (smin < lo < hi < smax):
            raise ValueError("la plage acceptée doit tenir strictement dans le curseur")
        if p.scale == "log" and smin <= 0:
            raise ValueError("curseur logarithmique : minimum > 0")
        if hi / lo > 4:
            raise ValueError("plage acceptée trop large (plus d'un facteur 4)")
    elif fmt == "two_step_calc":
        ids = [f.id for f in p.formulas]
        if p.correct_formula not in ids:
            raise ValueError("`correct_formula` ne désigne aucune formule")
        for f in p.formulas:
            if f.id != p.correct_formula and not (f.why_wrong or "").strip():
                raise ValueError(f"formule {f.id} : `why_wrong` manquant")
        _check_computation(p.computation, p.answer, "calcul")
    elif fmt == "fill_blank":
        slots = re.findall(r"\{\{(\d)\}\}", p.text)
        if sorted(int(s) for s in slots) != sorted(s.id for s in p.slots):
            raise ValueError("les trous du texte et les `slots` ne correspondent pas")
        for s in p.slots:
            if s.correct >= len(s.options):
                raise ValueError(f"trou {s.id} : `correct` hors des options")
            if len({o.strip().lower() for o in s.options}) != len(s.options):
                raise ValueError(f"trou {s.id} : options identiques")
    elif fmt == "mece_sort":
        bucket_ids = [b.id for b in p.buckets]
        if len(set(bucket_ids)) != len(bucket_ids):
            raise ValueError("paniers en double")
        for it in p.items:
            if it.bucket not in bucket_ids:
                raise ValueError(f"item {it.id} : panier inconnu")
        for b in bucket_ids:
            if sum(it.bucket == b for it in p.items) < 2:
                raise ValueError(f"panier {b} : au moins deux items")
    elif fmt == "match_pairs":
        lefts = [x.left.strip().lower() for x in p.pairs]
        rights = [x.right.strip().lower() for x in p.pairs]
        if len(set(lefts)) != len(lefts) or len(set(rights)) != len(rights):
            raise ValueError("paires ambiguës (deux gauches ou deux droites identiques)")
    elif fmt == "oral_prompt":
        keys = [r.key for r in p.rubric]
        if len(set(keys)) != len(keys):
            raise ValueError("critères en double")


# ── Arithmetic, recomputed server-side ─────────────────────────────────────

_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def evaluate(expression: str) -> float:
    """`2.4e6*480*0.72`, `(120-80)/80`, `1.08**5` : numbers and + - * / ** ( ) only."""

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return float(_OPS[type(node.op)](walk(node.left), walk(node.right)))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return float(_OPS[type(node.op)](walk(node.operand)))
        raise ValueError("expression non arithmétique")

    try:
        return walk(ast.parse(expression.replace(",", "."), mode="eval"))
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"calcul illisible : {expression!r}") from exc


def _check_computation(expression: str, answer: float, label: str) -> None:
    value = evaluate(expression)
    if answer == 0 or abs(value - answer) / abs(answer) > 0.005:
        raise ValueError(f"{label} : la formule donne {value:g}, la réponse dit {answer:g}")


# ── Units and nodes ────────────────────────────────────────────────────────


class Node(BaseModel):
    """One circle on the path."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[a-z0-9]+\.[a-z0-9_]+$", max_length=48)
    kind: Literal[NODE_KINDS]  # type: ignore[valid-type]
    title: str = Field(min_length=1, max_length=80)
    objective: str = Field(default="", max_length=240)
    errors: list[str] = Field(default_factory=list, max_length=5)
    formats: list[str] = Field(default_factory=list, max_length=12)
    items: int = Field(default=10, ge=4, le=20)
    # applied: the slot of the day's exercise it opens (case_market_sizing…) or a type
    applied_type: str | None = Field(default=None, max_length=24)

    @model_validator(mode="after")
    def _check(self) -> Node:
        unknown = set(self.formats) - set(FORMATS)
        if unknown:
            raise ValueError(f"formats inconnus : {sorted(unknown)}")
        if self.kind == "lesson" and not self.objective.strip():
            raise ValueError(f"{self.code} : objectif manquant")
        return self


class Unit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[a-z0-9]+$", max_length=16)
    order: int = Field(ge=0, le=99)
    track: Literal[TRACKS] = "common"  # type: ignore[valid-type]
    title: str = Field(min_length=1, max_length=80)
    subtitle: str = Field(default="", max_length=160)
    symbol: str = Field(default="book.fill", max_length=40)
    nodes: list[Node] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _check(self) -> Unit:
        codes = [n.code for n in self.nodes]
        if len(set(codes)) != len(codes):
            raise ValueError("nœuds en double")
        for n in self.nodes:
            if not n.code.startswith(self.code + "."):
                raise ValueError(f"nœud {n.code} : doit commencer par {self.code}.")
        return self


# ── Files ──────────────────────────────────────────────────────────────────


def load_units(folder: Path) -> list[Unit]:
    units = [
        Unit.model_validate(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(folder.glob("*.json"))
    ]
    orders = [u.order for u in units]
    if len(set(orders)) != len(orders):
        raise ContentInvalid("deux unités ont le même ordre")
    return sorted(units, key=lambda u: u.order)


def load_items(folder: Path) -> list[Item]:
    items: list[Item] = []
    for path in sorted(folder.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ContentInvalid(f"{path.name} : une liste d'items attendue")
        for i, data in enumerate(raw):
            try:
                items.append(Item.model_validate(data))
            except ValidationError as exc:
                ident = data.get("id", f"#{i}") if isinstance(data, dict) else f"#{i}"
                raise ContentInvalid(f"{path.name} {ident} : {exc.errors()[0]['msg']}") from exc
    ids = [it.id for it in items]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ContentInvalid(f"items en double : {sorted(dupes)[:5]}")
    return items


def check_files(paths: list[Path]) -> list[tuple[str, str]]:
    """`(file, "OK" | "REFUS …")` per file, for the CLI."""
    out: list[tuple[str, str]] = []
    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for i, data in enumerate(raw):
                    try:
                        Item.model_validate(data)
                    except ValidationError as exc:
                        ident = data.get("id", f"#{i}") if isinstance(data, dict) else f"#{i}"
                        out.append((f"{path.name} {ident}", f"REFUS {exc.errors()[0]['msg']}"))
            else:
                Unit.model_validate(raw)
            if not any(name.startswith(path.name) for name, _ in out):
                out.append((path.name, "OK"))
        except (ValidationError, ValueError, OSError) as exc:
            msg = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
            out.append((path.name, f"REFUS {msg}"))
    return out
