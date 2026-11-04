"""Sign in with Apple, native flow only (Tangent ADR-035, without the web flow).

The app gets an `id_token` from iOS and posts it here. We verify it against
Apple's published keys (signature, issuer, audience = our bundle id,
expiry, nonce) and open the session like any login: same cookie.

Configuration (backend/.env): APPLE_BUNDLE_ID. Nothing else: the native
flow needs no client secret.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_users.exceptions import UserAlreadyExists
from pydantic import BaseModel

from .backend import auth_backend
from .manager import get_user_manager

logger = logging.getLogger(__name__)

PROVIDER = "apple"
KEYS_URL = "https://appleid.apple.com/auth/keys"
ISSUER = "https://appleid.apple.com"
BUNDLE_ID = os.getenv("APPLE_BUNDLE_ID", "")

_jwks = jwt.PyJWKClient(KEYS_URL, cache_keys=True, lifespan=24 * 3600)


def is_configured() -> bool:
    return bool(BUNDLE_ID)


def signing_key(id_token: str) -> Any:
    return _jwks.get_signing_key_from_jwt(id_token).key


class AppleIdentity(BaseModel):
    sub: str
    email: str


def nonce_matches(claim: str | None, raw_nonce: str | None) -> bool:
    """iOS puts SHA-256(raw nonce) in the request; Apple echoes it in the token."""
    if raw_nonce is None:
        return True
    if not claim:
        return False
    return claim in (raw_nonce, hashlib.sha256(raw_nonce.encode()).hexdigest())


def verify_id_token(id_token: str, *, nonce: str | None = None) -> AppleIdentity:
    try:
        claims = jwt.decode(
            id_token,
            signing_key(id_token),
            algorithms=["RS256"],
            audience=[BUNDLE_ID],
            issuer=ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"id_token Apple refusé : {exc}") from exc
    if not nonce_matches(claims.get("nonce"), nonce):
        raise ValueError("nonce Apple incorrect")
    email = claims.get("email")
    verified = claims.get("email_verified", False)
    verified = verified is True or str(verified).lower() == "true"
    if not email or not verified:
        raise ValueError("Adresse e-mail Apple absente ou non vérifiée.")
    return AppleIdentity(sub=str(claims["sub"]), email=str(email))


class NativeIn(BaseModel):
    identity_token: str
    nonce: str | None = None
    display_name: str | None = None


def build_router() -> APIRouter:
    router = APIRouter()

    @router.post("/native", status_code=204)
    async def native(
        body: NativeIn,
        request: Request,
        user_manager=Depends(get_user_manager),
        strategy=Depends(auth_backend.get_strategy),
    ) -> Response:
        try:
            identity = verify_id_token(body.identity_token, nonce=body.nonce)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            user = await user_manager.oauth_callback(
                PROVIDER,
                "apple-native",  # marker: the identity token is never stored
                identity.sub,
                identity.email,
                None,
                None,
                request,
                associate_by_email=True,
                is_verified_by_default=True,
            )
        except UserAlreadyExists as exc:
            raise HTTPException(status_code=400, detail="OAUTH_USER_ALREADY_EXISTS") from exc
        if not user.is_active:
            raise HTTPException(status_code=400, detail="LOGIN_BAD_CREDENTIALS")
        if body.display_name and not user.display_name:
            user = await user_manager.user_db.update(
                user, {"display_name": body.display_name.strip()[:64]}
            )
        response = await auth_backend.login(strategy, user)
        await user_manager.on_after_login(user, request, response)
        return response

    return router
