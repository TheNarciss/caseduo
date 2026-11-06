"""The Parcours engine: which node is active, what a lesson contains, what finishing it earns.

Rules (docs/PARCOURS.md):
- Nodes unlock one after the other across units. Applied steps and legendaries are optional:
  they open when the node before them is done and never block the next one.
- A lesson = its concept card first, then `node.items - 1` graded items from its bank, easiest
  first and an easy one last; ~30 % of them come from earlier lessons (interleaved review) as
  soon as there is something to review. Items never seen come before items already passed.
- A review picks from the unit's lessons, weakest skills first. A checkpoint or a legendary
  uses the items written for it (and the unit's banks if short).
- XP: lesson or review 10 (+5 perfect), checkpoint 20 (+5 perfect), legendary 40 when passed
  (≥ 75 %), replay 5. A checkpoint passes at 60 %. XP feeds the day's goal and the streak.
"""

from __future__ import annotations

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import Integer, and_, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import (
    Attempt,
    Exercise,
    PathItem,
    PathItemResult,
    PathNode,
    PathProgress,
    PathUnit,
)
from ..errors import ConflictError, InvalidRequestError, NotFoundError
from ..services import progress as progress_service
from ..services.clock import today_for
from . import oral

OPTIONAL_KINDS = ("applied", "legendary")
REVIEW_SHARE = 0.3
XP = {"lesson": 10, "review": 10, "checkpoint": 20, "legendary": 40, "applied": 0}
PERFECT_BONUS = 5
REPLAY_XP = 5
PASS_SCORE = {"checkpoint": 60, "legendary": 75}
RETIRE_AFTER_FLAGS = 3


@dataclass
class Course:
    units: list[PathUnit]
    nodes: dict[str, list[PathNode]] = field(default_factory=dict)  # by unit, in position order

    @property
    def ordered(self) -> list[PathNode]:
        return [n for u in self.units for n in self.nodes.get(u.code, [])]


async def load_course(session: AsyncSession) -> Course:
    units = list((await session.execute(select(PathUnit).order_by(PathUnit.order))).scalars())
    nodes = list(
        (
            await session.execute(
                select(PathNode).where(PathNode.active.is_(True)).order_by(PathNode.position)
            )
        ).scalars()
    )
    by_unit: dict[str, list[PathNode]] = defaultdict(list)
    for n in nodes:
        by_unit[n.unit_code].append(n)
    return Course(units=units, nodes=dict(by_unit))


async def progress_of(session: AsyncSession, user: User) -> dict[str, PathProgress]:
    rows = (
        await session.execute(select(PathProgress).where(PathProgress.user_id == user.id))
    ).scalars()
    return {p.node_code: p for p in rows}


def statuses(course: Course, done: dict[str, PathProgress]) -> dict[str, str]:
    """`done`, `active`, `available` (optional, open), `locked` for every node."""
    out: dict[str, str] = {}
    blocked = False
    previous_required_done = True
    for node in course.ordered:
        if node.code in done:
            out[node.code] = "done"
            if node.kind not in OPTIONAL_KINDS:
                previous_required_done = True
            continue
        if node.kind in OPTIONAL_KINDS:
            out[node.code] = "available" if previous_required_done and not blocked else "locked"
            continue
        if not blocked:
            out[node.code] = "active"
            blocked = True
        else:
            out[node.code] = "locked"
        previous_required_done = False
    return out


async def view(session: AsyncSession, user: User) -> dict[str, Any]:
    course = await load_course(session)
    done = await progress_of(session, user)
    status = statuses(course, done)
    active = next((c for c, s in status.items() if s == "active"), None)
    units_out = []
    total_done = 0
    for unit in course.units:
        nodes_out = []
        for node in course.nodes.get(unit.code, []):
            p = done.get(node.code)
            total_done += int(p is not None and node.kind not in OPTIONAL_KINDS)
            nodes_out.append(
                {
                    "code": node.code,
                    "kind": node.kind,
                    "title": node.title,
                    "objective": node.objective or None,
                    "status": status[node.code],
                    "best_score": p.best_score if p else None,
                    "times": p.times if p else 0,
                    "items": node.items,
                    "applied_type": node.applied_type,
                    "xp": XP[node.kind],
                }
            )
        required = [n for n in course.nodes.get(unit.code, []) if n.kind not in OPTIONAL_KINDS]
        units_out.append(
            {
                "code": unit.code,
                "order": unit.order,
                "track": unit.track,
                "title": unit.title,
                "subtitle": unit.subtitle,
                "symbol": unit.symbol,
                "done": sum(1 for n in required if n.code in done),
                "total": len(required),
                "nodes": nodes_out,
            }
        )
    required_total = sum(1 for n in course.ordered if n.kind not in OPTIONAL_KINDS)
    return {
        "units": units_out,
        "active_node": active,
        "done": total_done,
        "total": required_total,
    }


# ── Starting a node ─────────────────────────────────────────────────────────


async def node_or_404(session: AsyncSession, code: str) -> PathNode:
    node = await session.get(PathNode, code)
    if node is None or not node.active:
        raise NotFoundError("Étape introuvable.")
    return node


async def _bank(session: AsyncSession, skills: list[str]) -> list[PathItem]:
    if not skills:
        return []
    rows = await session.execute(
        select(PathItem).where(PathItem.skill.in_(skills), PathItem.retired.is_(False))
    )
    return list(rows.scalars())


async def _history(session: AsyncSession, user: User) -> dict[str, tuple[int, int]]:
    """item_id -> (times seen, times correct on first try)."""
    ok = cast(and_(PathItemResult.correct, PathItemResult.first_try), Integer)
    rows = await session.execute(
        select(PathItemResult.item_id, func.count(), func.sum(ok))
        .where(PathItemResult.user_id == user.id)
        .group_by(PathItemResult.item_id)
    )
    return {item_id: (int(seen), int(good or 0)) for item_id, seen, good in rows.all()}


async def _skill_accuracy(session: AsyncSession, user: User) -> dict[str, float]:
    rows = await session.execute(
        select(PathItem.skill, func.avg(cast(PathItemResult.correct, Integer)))
        .join(PathItem, PathItem.id == PathItemResult.item_id)
        .where(PathItemResult.user_id == user.id, PathItemResult.first_try.is_(True))
        .group_by(PathItem.skill)
    )
    return {skill: float(acc or 0) for skill, acc in rows.all()}


def _pick(
    pool: list[PathItem], n: int, history: dict[str, tuple[int, int]], rng: random.Random
) -> list[PathItem]:
    """Never seen first, then failed, then passed; random inside each group."""

    def rank(it: PathItem) -> tuple[int, float]:
        seen, ok = history.get(it.id, (0, 0))
        if seen == 0:
            return (0, rng.random())
        if ok < seen:
            return (1, rng.random())
        return (2, rng.random())

    return sorted(pool, key=rank)[:n]


def _order_for_lesson(items: list[PathItem]) -> list[PathItem]:
    """Easiest first, and the easiest of the rest at the very end (end on a success)."""
    if len(items) < 3:
        return items
    ordered = sorted(items, key=lambda it: it.difficulty)
    last = ordered.pop(1)
    return [*ordered, last]


async def start(
    session: AsyncSession, user: User, node: PathNode, *, seed: int | None = None
) -> dict[str, Any]:
    if node.kind == "applied":
        raise InvalidRequestError("Une étape en situation se joue sur l'exercice du jour.")
    course = await load_course(session)
    done = await progress_of(session, user)
    status = statuses(course, done)[node.code]
    if status == "locked":
        raise ConflictError("Cette étape est encore verrouillée.")
    rng = random.Random(seed)
    history = await _history(session, user)
    unit_lessons = [n.code for n in course.nodes.get(node.unit_code, []) if n.kind == "lesson"]
    earlier_lessons = [
        n.code
        for n in course.ordered
        if n.kind == "lesson" and course.ordered.index(n) < course.ordered.index(node)
    ]
    chosen: list[PathItem] = []
    concept: list[PathItem] = []

    if node.kind == "lesson":
        own = await _bank(session, [node.code])
        concept = [it for it in own if it.format == "concept_card"][:1]
        orals = [it for it in own if it.format == "oral_prompt"][:1]  # the lesson ends aloud
        graded = [it for it in own if it.format not in ("concept_card", "oral_prompt")]
        n_total = max(1, node.items - len(concept) - len(orals))
        n_review = round(n_total * REVIEW_SHARE) if earlier_lessons and done else 0
        own_pick = _pick(graded, n_total - n_review, history, rng)
        review_pool = [
            it
            for it in await _bank(session, earlier_lessons)
            if it.format not in ("concept_card", "oral_prompt")
        ]
        accuracy = await _skill_accuracy(session, user)
        review_pool.sort(key=lambda it: accuracy.get(it.skill, 0.5))
        review_pick = _pick(review_pool, n_review, history, rng) if n_review else []
        chosen = _order_for_lesson(own_pick + review_pick)
        if len(chosen) < n_total:  # a thin bank: fill with whatever the unit has
            extra = [it for it in review_pool if it not in chosen][: n_total - len(chosen)]
            chosen = _order_for_lesson(chosen + extra)
        chosen += orals
    elif node.kind == "review":
        pool = [
            it
            for it in await _bank(session, [node.code, *unit_lessons])
            if it.format not in ("concept_card", "oral_prompt")
        ]
        accuracy = await _skill_accuracy(session, user)
        pool.sort(key=lambda it: accuracy.get(it.skill, 0.5))
        chosen = _order_for_lesson(_pick(pool, node.items, history, rng))
    else:  # checkpoint, legendary
        own = [it for it in await _bank(session, [node.code]) if it.format != "concept_card"]
        orals = [it for it in own if it.format == "oral_prompt"]
        graded = [it for it in own if it.format != "oral_prompt"]
        n_graded = max(0, node.items - len(orals))
        chosen = _pick(graded, n_graded, history, rng)
        if len(chosen) < n_graded:
            pool = [
                it
                for it in await _bank(session, unit_lessons)
                if it.format not in ("concept_card", "oral_prompt") and it.difficulty >= 3
            ]
            chosen += _pick(
                [it for it in pool if it not in chosen], n_graded - len(chosen), history, rng
            )
        chosen = sorted(chosen, key=lambda it: it.difficulty) + orals

    if not chosen and not concept:
        raise ConflictError("Cette étape n'a pas encore d'exercices.")
    return {
        "node": {
            "code": node.code,
            "kind": node.kind,
            "title": node.title,
            "objective": node.objective or None,
        },
        "items": [item_dict(it) for it in concept + chosen],
        "xp": XP[node.kind] if node.code not in done else REPLAY_XP,
        "perfect_bonus": PERFECT_BONUS if node.kind != "legendary" else 0,
        "pass_score": PASS_SCORE.get(node.kind),
    }


def item_dict(it: PathItem) -> dict[str, Any]:
    return {
        "id": it.id,
        "format": it.format,
        "skill": it.skill,
        "difficulty": it.difficulty,
        "lang": it.lang,
        "sector": it.sector,
        "stem": it.stem,
        "media": it.media,
        "explanation": it.explanation,
        "payload": it.payload,
    }


# ── Finishing a node ────────────────────────────────────────────────────────


@dataclass
class ItemResultIn:
    item_id: str
    correct: bool
    first_try: bool = True
    ms: int = 0
    response: dict[str, Any] | None = None
    transcript: str | None = None  # oral items: graded here


async def complete(
    session: AsyncSession, user: User, node: PathNode, results: list[ItemResultIn]
) -> dict[str, Any]:
    done = await progress_of(session, user)
    if node.kind == "applied":
        raise InvalidRequestError("Une étape en situation se valide avec l'exercice du jour.")
    ids = [r.item_id for r in results]
    items = {
        it.id: it
        for it in (await session.execute(select(PathItem).where(PathItem.id.in_(ids)))).scalars()
    }
    unknown = set(ids) - set(items)
    if unknown:
        raise InvalidRequestError(f"Items inconnus : {sorted(unknown)[:3]}")

    graded = 0
    first_try_ok = 0
    orals: list[dict[str, Any]] = []
    for r in results:
        it = items[r.item_id]
        if it.format == "concept_card":
            continue
        correct = r.correct
        if it.format == "oral_prompt":
            verdict = await oral.grade(it, r.transcript or "")
            orals.append({"item_id": it.id, **verdict})
            correct = verdict["score"] is None or verdict["score"] >= 50
        graded += 1
        first_try_ok += int(correct and r.first_try)
        session.add(
            PathItemResult(
                id=uuid.uuid4(),
                user_id=user.id,
                item_id=it.id,
                node_code=node.code,
                correct=correct,
                first_try=r.first_try,
                ms=max(0, r.ms),
                response=r.response,
            )
        )
    score = round(100 * first_try_ok / graded) if graded else 100
    passed = score >= PASS_SCORE.get(node.kind, 0)
    replay = node.code in done
    xp = 0
    if passed:
        xp = REPLAY_XP if replay else XP[node.kind]
        if score == 100 and node.kind != "legendary" and not replay:
            xp += PERFECT_BONUS
        previous = done.get(node.code)
        await session.execute(
            pg_insert(PathProgress)
            .values(user_id=user.id, node_code=node.code, best_score=score, times=1)
            .on_conflict_do_update(
                index_elements=["user_id", "node_code"],
                set_={
                    "best_score": func.greatest(PathProgress.best_score, score),
                    "times": PathProgress.times + 1,
                    "completed_at": func.now(),
                },
            )
        )
        del previous
    progress = await progress_service.apply_xp(session, user, today_for(user), xp)
    await session.commit()
    course = await load_course(session)
    status = statuses(course, await progress_of(session, user))
    return {
        "node": node.code,
        "passed": passed,
        "score": score,
        "xp": xp,
        "replay": replay,
        "oral": orals,
        "progress": progress.as_dict(),
        "next_node": next((c for c, s in status.items() if s == "active"), None),
        "unit_done": all(
            status[n.code] == "done"
            for n in course.nodes.get(node.unit_code, [])
            if n.kind not in OPTIONAL_KINDS
        ),
    }


async def complete_applied(
    session: AsyncSession, user: User, node: PathNode, attempt_id: uuid.UUID
) -> dict[str, Any]:
    """An applied step is done once the user answered a matching exercise today."""
    if node.kind != "applied":
        raise InvalidRequestError("Cette étape n'est pas une étape en situation.")
    attempt = await session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user.id or attempt.kind != "main":
        raise NotFoundError("Tentative introuvable.")
    exercise = await session.get(Exercise, attempt.exercise_id)
    wanted = node.applied_type or "case"
    matches = exercise is not None and (
        (wanted == "case" and exercise.type not in ("brainteaser", "fit"))
        or exercise.type == wanted
    )
    if not matches:
        raise InvalidRequestError("Cet exercice ne correspond pas à l'étape.")
    await session.execute(
        pg_insert(PathProgress)
        .values(user_id=user.id, node_code=node.code, best_score=attempt.score, times=1)
        .on_conflict_do_update(
            index_elements=["user_id", "node_code"],
            set_={
                "best_score": func.greatest(PathProgress.best_score, attempt.score),
                "times": PathProgress.times + 1,
                "completed_at": func.now(),
            },
        )
    )
    await session.commit()
    return {"node": node.code, "passed": True, "score": attempt.score, "xp": 0}


async def flag(session: AsyncSession, item_id: str, note: str | None) -> dict[str, Any]:
    item = await session.get(PathItem, item_id)
    if item is None:
        raise NotFoundError("Exercice introuvable.")
    item.flag_count += 1
    if note:
        item.flag_note = note[:300]
    if item.flag_count >= RETIRE_AFTER_FLAGS:
        item.retired = True
    await session.commit()
    return {"id": item.id, "flag_count": item.flag_count, "retired": item.retired}


def applied_today(day: date) -> date:  # kept for symmetry with the day services
    return day
