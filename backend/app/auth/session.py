"""Sliding session renewal (Tangent ADR-035): a session that is used stays open.

`renewed_token` mints a fresh token once the current one is older than
`RENEW_AFTER_SECONDS`; `main.py` applies it on `GET /api/users/me`, which the
app calls on every launch.
"""

from __future__ import annotations

import os
import time

import jwt
from fastapi_users.jwt import decode_jwt, generate_jwt

from .backend import COOKIE_LIFETIME, JWT_SECRET

RENEW_AFTER_SECONDS = int(os.getenv("SESSION_RENEW_AFTER_SECONDS", str(24 * 3600)))
SESSION_AUDIENCE = "fastapi-users:auth"  # JWTStrategy's default audience


def renewed_token(token: str, *, now: float | None = None) -> str | None:
    """A fresh token for the same user when this one has aged past the threshold."""
    try:
        data = decode_jwt(token, JWT_SECRET, [SESSION_AUDIENCE])
    except jwt.PyJWTError:
        return None
    now = now if now is not None else time.time()
    issued_at = float(data["exp"]) - COOKIE_LIFETIME
    if now - issued_at < RENEW_AFTER_SECONDS:
        return None
    return generate_jwt({"sub": data["sub"], "aud": SESSION_AUDIENCE}, JWT_SECRET, COOKIE_LIFETIME)
