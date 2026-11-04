"""HTTP routers. `ROUTERS` are mounted under /api by main.py."""

from fastapi import APIRouter

from . import admin_pages, attempts, day, exercises, grade, history, me, today

ROUTERS: list[APIRouter] = [
    today.router,
    exercises.router,
    grade.router,
    attempts.router,
    me.router,
    day.router,
    history.router,
]

__all__ = ["ROUTERS", "admin_pages"]
