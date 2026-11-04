"""Auth backend: cookie transport + JWT strategy (same as Tangent, ADR-003/035).

- HTTP-only cookie, Secure in prod, SameSite=lax
- JWT HS256, 7 days, renewed while the session is used (session.py)
"""

import os

from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

COOKIE_NAME = os.getenv("COOKIE_NAME", "caseduo_auth")
COOKIE_LIFETIME = int(os.getenv("COOKIE_LIFETIME_SECONDS", 7 * 24 * 3600))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

cookie_transport = CookieTransport(
    cookie_name=COOKIE_NAME,
    cookie_max_age=COOKIE_LIFETIME,  # persistent: the phone's cookie store keeps it
    cookie_secure=COOKIE_SECURE,
    cookie_httponly=True,
    cookie_samesite="lax",
)

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET or JWT_SECRET == "GENERATE_ME_WITH_SECRETS_TOKEN_URLSAFE":
    raise RuntimeError(
        "JWT_SECRET manquant ou laissé au placeholder. "
        'Génère-en un : python -c "import secrets; print(secrets.token_urlsafe(48))" '
        "puis mets-le dans backend/.env"
    )


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=COOKIE_LIFETIME, algorithm="HS256")


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
