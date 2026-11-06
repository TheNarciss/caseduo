"""GET/PATCH/DELETE /me — the Profile screen."""

from __future__ import annotations

from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..db.models import UserStory
from ..services import commitments
from ..services.clock import today_for

router = APIRouter(prefix="/me", tags=["me"])
_audit = __import__("logging").getLogger("audit")


async def me_view(session: AsyncSession, user: User) -> dict[str, Any]:
    story = await session.get(UserStory, user.id)
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": user.is_superuser,
        "timezone": user.timezone,
        "daily_goal_xp": user.daily_goal_xp,
        "sounds_enabled": user.sounds_enabled,
        "notifications_enabled": user.notifications_enabled,
        "streak_current": user.streak_current,
        "streak_longest": user.streak_longest,
        "streak_freezes": user.streak_freezes,
        "xp_total": user.xp_total,
        "league": user.league,
        "story_text": story.story_text if story else None,
        "story_updated_at": story.updated_at.isoformat() if story else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "commitment": await commitments.for_screen(session, user, today_for(user)),
    }


class MePatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    timezone: str | None = None
    daily_goal_xp: Literal[30, 50, 80] | None = None
    sounds_enabled: bool | None = None
    notifications_enabled: bool | None = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("fuseau horaire inconnu") from exc
        return v


@router.get("")
async def get_me(
    user: User = Depends(current_active_user), session: AsyncSession = Depends(get_session)
):
    return await me_view(session, user)


@router.patch("")
async def patch_me(
    body: MePatch,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    if body.daily_goal_xp is not None:
        await commitments.guard_goal_change(session, user, today_for(user))
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(
                user,
                key,
                value.strip() if isinstance(value, str) and key == "display_name" else value,
            )
    session.add(user)
    await session.commit()
    return await me_view(session, user)


class CommitmentIn(BaseModel):
    daily_xp: Literal[30, 50, 80]
    days: Literal[7, 14, 30]


@router.post("/commitment")
async def post_commitment(
    body: CommitmentIn,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """« Je m'engage » : the goal for 7, 14 or 30 days from today, locked (DEVIATIONS D16)."""
    await commitments.start(session, user, today_for(user), daily_xp=body.daily_xp, days=body.days)
    await session.commit()
    return await me_view(session, user)


class StoryIn(BaseModel):
    story_text: str = Field(max_length=20_000)


@router.put("/story")
async def put_story(
    body: StoryIn,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """The career story (schools, Thales Rungis, Thales Singapore, projects, why consulting…),
    sent to the grader with every fit answer."""
    story = await session.get(UserStory, user.id)
    if story is None:
        session.add(UserStory(user_id=user.id, story_text=body.story_text.strip()))
    else:
        story.story_text = body.story_text.strip()
    await session.commit()
    return await me_view(session, user)


class PushToken(BaseModel):
    token: str = Field(min_length=32, max_length=200, pattern=r"^[0-9a-fA-F]+$")
    environment: Literal["sandbox", "production"] = "production"


@router.post("/push-token", status_code=204)
async def register_push_token(
    body: PushToken,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """The app sends its APNs token at each launch; the last device wins."""
    user.apns_token = body.token.lower()
    user.apns_environment = body.environment
    session.add(user)
    await session.commit()
    return Response(status_code=204)


@router.delete("", status_code=204)
async def delete_me(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """App Store rule 5.1.1(v): the account and every row of it, for good."""
    _audit.info("ACCOUNT_DELETED user_id=%s", user.id)
    await session.execute(delete(User).where(User.id == user.id))  # type: ignore[arg-type]
    await session.commit()
    response = Response(status_code=204)
    from ..auth.backend import COOKIE_NAME

    response.delete_cookie(COOKIE_NAME)
    return response
