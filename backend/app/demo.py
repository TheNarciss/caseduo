"""A demonstration account with a believable history, for Apple's reviewers (as Tangent).

    DEMO_EMAIL=demo@riskybusinesses.uk DEMO_PASSWORD='…' python -m app.demo

The reviewer must find every screen alive: today's exercises, a 5-day
streak, scored attempts with feedback, a revenge due today, a career story,
a few badges, a league. Running it again refreshes the same account (same
e-mail, new password, history rebuilt). Not an administrator. Grading a
new answer calls Claude like for anyone else.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import logging_config
from .auth import User, UserCreate
from .auth.manager import UserManager, password_helper
from .auth.oauth_models import OAuthAccount
from .db import async_session_factory
from .db.models import (
    Attempt,
    DailyActivity,
    Exercise,
    LeagueWeek,
    MockRun,
    Reveal,
    Revenge,
    UserBadge,
    UserStory,
)
from .game.revenge import schedule
from .game.xp import attempt_xp
from .generation import service
from .grading.scoring import weighted_score
from .services.clock import today_for

logger = logging.getLogger("app.demo")

STORY = (
    "Ingénieur ESILV (majeure data & IA). Alternance puis CDI chez Thales à Rungis : "
    "pipelines de données pour la maintenance de systèmes radar, premier modèle de détection "
    "d'anomalies mis en production. Mutation chez Thales à Singapour : chef de projet data pour "
    "trois clients de la région. Pourquoi le conseil : j'ai vu que la valeur se jouait dans le "
    "cadrage et l'adoption, pas dans le modèle ; je veux voir plus de secteurs et parler aux "
    "dirigeants. Pourquoi partir : après 3 ans, apprendre plus vite que dans un seul groupe."
)
FEEDBACK_FR = (
    "### Ce qui était bien\n- Reformulation claire de l'objectif.\n- Un chiffre décomposé avec ses hypothèses.\n\n"
    "### À corriger\n- Plan annoncé trop tard → « Je vois trois axes : la demande, la capacité, la rentabilité. »\n"
    "- Recommandation hésitante → « Je recommande de lancer un pilote de trois mois sur un site. »\n\n"
    "### En 30 secondes tu aurais dû dire\n« Je reformule, j'annonce trois axes, je pose mes hypothèses, "
    "je chiffre, je teste la sensibilité et je recommande un pilote, avec son principal risque. »"
)
# marks per day (0, 1, 2), cycling over the rubric criteria: a visible weakness on "structure"
MARK_PATTERNS = ([2, 1, 1, 2, 1], [2, 0, 2, 1, 2], [1, 1, 2, 2, 1], [2, 1, 2, 2, 2])


async def _user(session: AsyncSession, email: str, password: str) -> User:
    manager = UserManager(
        SQLAlchemyUserDatabase(session, User, OAuthAccount),  # type: ignore[type-var]
        password_helper=password_helper,
    )
    try:
        user = await manager.create(
            UserCreate(email=email, password=password, is_verified=True, display_name="Démo"),
            safe=False,
        )
    except UserAlreadyExists:
        stmt = select(User).where(User.email == email)  # type: ignore[arg-type]
        user = (await session.execute(stmt)).unique().scalar_one()
        user.hashed_password = password_helper.hash(password)
    return user


async def refresh(email: str, password: str) -> uuid.UUID:
    async with async_session_factory() as session:
        user = await _user(session, email, password)
        uid = user.id
        for table in (
            Attempt,
            DailyActivity,
            Revenge,
            Reveal,
            UserStory,
            MockRun,
            LeagueWeek,
            UserBadge,
        ):
            await session.execute(delete(table).where(table.user_id == uid))  # type: ignore[attr-defined]
        fresh = await session.get(User, uid)
        assert fresh is not None
        user = fresh
        user.is_superuser = False
        user.display_name = "Démo"
        user.timezone = "Asia/Singapore"
        user.daily_goal_xp = 50
        user.created_at = datetime.now(UTC) - timedelta(days=21)
        user.league = "bronze"
        await session.commit()

        today = today_for(user)
        await service.ensure_day(session, today, job="seed")
        for back in range(1, 7):
            day = today - timedelta(days=back)
            if await service.count_exercises(session, day) == 0:
                await service.insert_starter_pack(session, day)

        session.add(UserStory(user_id=uid, story_text=STORY))
        xp_total = 0
        for back in range(6, 0, -1):
            day = today - timedelta(days=back)
            exercises = list(
                (
                    await session.execute(
                        select(Exercise).where(Exercise.date == day).order_by(Exercise.slot)
                    )
                ).scalars()
            )
            exercises = [e for e in exercises if not e.slot.startswith("mock_")][
                : 2 if back == 6 else 3
            ]
            day_xp = 0
            for i, ex in enumerate(exercises):
                pattern = MARK_PATTERNS[(back + i) % len(MARK_PATTERNS)]
                if back == 3 and i == 0:
                    pattern = [1, 0, 1, 0, 0]  # a miss, back as a revenge today
                scores = [
                    {
                        "key": c["key"],
                        "label": c["label"],
                        "weight": c["weight"],
                        "score": pattern[j % len(pattern)],
                        "justification": "Exemple de justification du correcteur.",
                        "quote": "",
                    }
                    for j, c in enumerate(ex.rubric)
                ]
                score = weighted_score(scores)
                xp = attempt_xp(ex.type, ex.difficulty, "main", score).earned
                attempt = Attempt(
                    user_id=uid,
                    exercise_id=ex.id,
                    kind="main",
                    answer_text="Réponse de démonstration : je reformule, j'annonce trois axes, je chiffre et je recommande.",
                    duration_seconds=240 + 30 * i,
                    input_mode="voice" if i % 2 else "text",
                    score=score,
                    rubric_scores=scores,
                    feedback=FEEDBACK_FR,
                    follow_up="D'où vient ton hypothèse de 30 % ?",
                    xp_earned=xp,
                    local_date=day,
                    model_used="demo",
                    created_at=datetime.combine(day, datetime.min.time(), tzinfo=UTC)
                    + timedelta(hours=2 + i),
                )
                session.add(attempt)
                await session.flush()
                if score < 60:
                    for step, due in schedule(day):
                        session.add(
                            Revenge(
                                user_id=uid,
                                exercise_id=ex.id,
                                source_attempt_id=attempt.id,
                                step=step,
                                due_date=due,
                            )
                        )
                day_xp += xp
            session.add(
                DailyActivity(
                    user_id=uid,
                    date=day,
                    xp_earned=day_xp,
                    exercises_done=len(exercises),
                    goal_met=back <= 5 and day_xp >= 50,
                )
            )
            xp_total += day_xp
        await session.flush()

        met = (
            await session.execute(
                select(DailyActivity.date).where(
                    DailyActivity.user_id == uid, DailyActivity.goal_met.is_(True)
                )
            )
        ).scalars()
        met_days = set(met)
        streak, day = 0, today - timedelta(days=1)
        while day in met_days:
            streak += 1
            day -= timedelta(days=1)
        user.streak_current = streak
        user.streak_longest = max(streak, 7)
        user.streak_freezes = 2
        user.streak_last_date = today - timedelta(days=1) if streak else None
        user.xp_total = xp_total
        for code in ("first_case", "streak_3"):
            session.add(UserBadge(user_id=uid, badge_code=code))
        await session.commit()
        print(f"Compte de démo prêt : {email} — série {streak} jours, {xp_total} XP")
        return uid


def main() -> None:
    logging_config.configure()
    email = os.getenv("DEMO_EMAIL", "").strip()
    password = os.getenv("DEMO_PASSWORD", "")
    if not email or len(password) < 8:
        print("DEMO_EMAIL et DEMO_PASSWORD (8 caractères ou plus) sont requis.", file=sys.stderr)
        sys.exit(1)
    asyncio.run(refresh(email, password))


if __name__ == "__main__":
    main()
