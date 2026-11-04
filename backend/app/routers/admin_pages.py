"""HTML pages outside /api (admin review). Filled in by the admin-review commit."""

from fastapi import APIRouter

router = APIRouter(include_in_schema=False)
