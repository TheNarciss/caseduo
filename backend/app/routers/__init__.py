"""HTTP routers. `ROUTERS` are mounted under /api by main.py."""

from fastapi import APIRouter

from . import (
    admin,
    admin_pages,
    attempts,
    day,
    exercises,
    grade,
    history,
    league,
    me,
    mocks,
    path,
    today,
    training,
)

ROUTERS: list[APIRouter] = [
    today.router,
    training.router,
    path.router,
    exercises.router,
    grade.router,
    attempts.router,
    me.router,
    day.router,
    history.router,
    mocks.router,
    league.router,
    admin.router,
]

__all__ = ["ROUTERS", "admin_pages"]
