"""HTTP routers. `ROUTERS` are mounted under /api by main.py."""

from fastapi import APIRouter

from . import admin_pages

ROUTERS: list[APIRouter] = []

__all__ = ["ROUTERS", "admin_pages"]
