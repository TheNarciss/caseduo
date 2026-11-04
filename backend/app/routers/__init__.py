"""HTTP routers. `ROUTERS` are mounted under /api by main.py."""

from fastapi import APIRouter

from . import admin_pages, attempts, exercises, grade, me, today

ROUTERS: list[APIRouter] = [
    today.router,
    exercises.router,
    grade.router,
    attempts.router,
    me.router,
]

__all__ = ["ROUTERS", "admin_pages"]
