"""HTTP routers. `ROUTERS` are mounted under /api by main.py."""

from fastapi import APIRouter

from . import admin_pages, attempts, exercises, grade

ROUTERS: list[APIRouter] = [exercises.router, grade.router, attempts.router]

__all__ = ["ROUTERS", "admin_pages"]
