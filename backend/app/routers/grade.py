"""POST /grade (JSON) and POST /grade/stream (SSE) — same body, same result.

Checks (exercise, parent attempt, budget, API key) run before the stream
opens, so they come back as proper HTTP errors (as Tangent's reviews route).
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..errors import AppError, BudgetExceededError
from ..grading import service
from ..grading.service import GradeRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["grading"])


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/grade")
async def grade(
    body: GradeRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    prepared = await service.prepare(session, user, body)
    return await service.grade(session, prepared)


@router.post("/grade/stream")
async def grade_stream(
    body: GradeRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    prepared = await service.prepare(session, user, body)

    async def events() -> AsyncIterator[str]:
        try:
            async for kind, data in service.stream_grade(session, prepared):
                yield sse(kind, data)
        except BudgetExceededError as exc:
            yield sse("error", {"reason": "budget", "detail": exc.detail})
        except AppError as exc:
            reason = "overloaded" if "surchargé" in exc.detail else "invalid"
            yield sse("error", {"reason": reason, "detail": exc.detail})
        except Exception:
            logger.exception("Grading stream failed user=%s", user.id)
            yield sse(
                "error", {"reason": "internal", "detail": "Erreur interne pendant la notation."}
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
