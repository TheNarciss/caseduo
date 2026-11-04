"""Extension points around a grading: features plug in here as they arrive
(revenges, fit context, mocks, badges), keeping grading/service.py stable."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Attempt, MockRun
from ..errors import NotFoundError

if TYPE_CHECKING:
    from ..services.progress import ProgressResult
    from .service import Prepared


async def before_grading(session: AsyncSession, p: Prepared) -> None:
    if p.body.mock_run_id is not None:
        run = await session.get(MockRun, p.body.mock_run_id)
        if run is None or run.user_id != p.user.id:
            raise NotFoundError("Mock introuvable.")
        p.mock_run = run


async def after_grading(
    session: AsyncSession, p: Prepared, attempt: Attempt, result: ProgressResult
) -> None:
    return None
