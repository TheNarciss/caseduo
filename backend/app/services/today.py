"""Today's cards for a user, in display order, and what is left to do.

Order (spec §4): cadrage_home pinned Friday→Sunday, warm-up brainteaser,
fit, cases by increasing difficulty, the other brainteasers, revenges, then the
bonus pack (DEVIATIONS D15): its exercises not done yet, and those done today.
Bonus cards never count for "journée complète" nor for the remaining badge.
The Sunday mock is not a card: `/today` carries it separately.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..catalog import CASE_TYPES, TYPE_LABELS
from ..db.models import Attempt, Exercise, Revenge
from ..game.xp import base_xp
from ..generation.service import BONUS_MODE

REVENGE_MULTIPLIER = 1.2


@dataclass
class Card:
    exercise: Exercise
    is_revenge: bool = False
    revenge_step: int | None = None
    pinned: bool = False
    done: bool = False
    best_score: int | None = None
    bonus: bool = False

    def as_dict(self) -> dict[str, Any]:
        ex = self.exercise
        xp = base_xp(ex.type, ex.difficulty)
        if self.is_revenge:
            xp = round(xp * REVENGE_MULTIPLIER)
        return {
            "exercise_id": str(ex.id),
            "type": ex.type,
            "type_label": TYPE_LABELS.get(ex.type, ex.type),
            "title": ex.title,
            "difficulty": ex.difficulty,
            "language": ex.language,
            "style": ex.style,
            "sector": ex.sector,
            "estimated_minutes": ex.estimated_minutes,
            "is_revenge": self.is_revenge,
            "revenge_step": self.revenge_step,
            "pinned": self.pinned,
            "done": self.done,
            "best_score": self.best_score,
            "xp_potential": xp,
            "due_label": (
                "À rendre dimanche soir"
                if ex.type == "cadrage_home"
                else ("Bonus · quand tu veux" if self.bonus else None)
            ),
            "is_bonus": self.bonus,
        }


def _is_mock_slot(ex: Exercise) -> bool:
    return ex.slot.startswith("mock_")


async def best_main_scores(
    session: AsyncSession, user_id: uuid.UUID, exercise_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not exercise_ids:
        return {}
    stmt = (
        select(Attempt.exercise_id, func.max(Attempt.score))
        .where(
            Attempt.user_id == user_id,
            Attempt.kind == "main",
            Attempt.exercise_id.in_(exercise_ids),
        )
        .group_by(Attempt.exercise_id)
    )
    return {row[0]: int(row[1]) for row in (await session.execute(stmt)).all()}


async def build_cards(session: AsyncSession, user_id: uuid.UUID, day: date) -> list[Card]:
    exercises = list(
        (await session.execute(select(Exercise).where(Exercise.date == day))).scalars().all()
    )
    # Friday's cadrage_home stays pinned until Sunday.
    pinned: Exercise | None = None
    if day.weekday() in (4, 5, 6):
        friday = day - timedelta(days=day.weekday() - 4)
        stmt = (
            select(Exercise)
            .where(
                Exercise.type == "cadrage_home",
                Exercise.date >= friday,
                Exercise.date <= day,
            )
            .order_by(Exercise.date.desc())
            .limit(1)
        )
        pinned = (await session.execute(stmt)).scalars().first()
    exercises = [
        e
        for e in exercises
        if e.type != "cadrage_home" and not _is_mock_slot(e) and e.generation_mode != BONUS_MODE
    ]

    revenges = (
        await session.execute(
            select(Revenge, Exercise)
            .join(Exercise, Exercise.id == Revenge.exercise_id)
            .where(
                Revenge.user_id == user_id,
                Revenge.due_date <= day,
                Revenge.done_attempt_id.is_(None),
                Exercise.flagged.is_(False),
            )
            .order_by(Revenge.due_date, Revenge.step)
        )
    ).all()

    ids = [e.id for e in exercises] + ([pinned.id] if pinned else [])
    best = await best_main_scores(session, user_id, ids)

    brainteasers = sorted((e for e in exercises if e.type == "brainteaser"), key=lambda e: e.slot)
    fits = [e for e in exercises if e.type == "fit"]
    cases = sorted(
        (e for e in exercises if e.type in (*CASE_TYPES, "tech_screen")),
        key=lambda e: (e.difficulty, e.estimated_minutes, e.slot),
    )

    def card(e: Exercise, **kw: Any) -> Card:
        return Card(exercise=e, done=e.id in best, best_score=best.get(e.id), **kw)

    cards: list[Card] = []
    if pinned is not None:
        cards.append(card(pinned, pinned=True))
    cards += [card(e) for e in brainteasers[:1]]
    cards += [card(e) for e in fits]
    cards += [card(e) for e in cases]
    cards += [card(e) for e in brainteasers[1:]]
    seen: set[uuid.UUID] = set()
    for revenge, ex in revenges:
        if ex.id in seen:  # both steps due at once: one card
            continue
        seen.add(ex.id)
        cards.append(Card(exercise=ex, is_revenge=True, revenge_step=revenge.step))
    cards += await bonus_cards(session, user_id, day)
    return cards


async def bonus_cards(session: AsyncSession, user_id: uuid.UUID, day: date) -> list[Card]:
    """The bonus pack, brainteasers then cases by difficulty: not done yet, or done today."""
    pack = list(
        (
            await session.execute(
                select(Exercise).where(
                    Exercise.generation_mode == BONUS_MODE,
                    Exercise.date <= day,
                    Exercise.flagged.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    if not pack:
        return []
    ids = [e.id for e in pack]
    best = await best_main_scores(session, user_id, ids)
    done_today = set(
        (
            await session.execute(
                select(Attempt.exercise_id).where(
                    Attempt.user_id == user_id,
                    Attempt.kind == "main",
                    Attempt.local_date == day,
                    Attempt.exercise_id.in_(ids),
                )
            )
        )
        .scalars()
        .all()
    )
    shown = [e for e in pack if e.id not in best or e.id in done_today]
    shown.sort(key=lambda e: (e.type != "brainteaser", e.difficulty, e.slot))
    return [
        Card(exercise=e, done=e.id in best, best_score=best.get(e.id), bonus=True) for e in shown
    ]


def remaining(cards: list[Card]) -> int:
    """Cards left today (the icon badge and the widget figure); cadrage_home and bonus excluded."""
    return sum(1 for c in cards if not c.done and not c.bonus and c.exercise.type != "cadrage_home")


def day_complete(cards: list[Card]) -> bool:
    """Every regular card of the day done (revenges, bonus and cadrage_home not required)."""
    regular = [
        c for c in cards if not c.is_revenge and not c.bonus and c.exercise.type != "cadrage_home"
    ]
    return bool(regular) and all(c.done for c in regular)
