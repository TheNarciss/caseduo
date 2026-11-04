"""UserManager (fastapi-users) — argon2 hashing, password rules, audit logs (as Tangent)."""

import logging
import os
import uuid

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions
from fastapi_users.password import PasswordHelper
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .models import User
from .oauth_models import OAuthAccount
from .schemas import UserCreate

logger = logging.getLogger(__name__)
_audit = logging.getLogger("audit")

_password_hash = PasswordHash((Argon2Hasher(),))
password_helper = PasswordHelper(_password_hash)


def _ip(request: Request | None) -> str | None:
    return request.client.host if request and request.client else None


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):  # type: ignore[type-var]
    reset_password_token_secret = os.getenv("JWT_SECRET", "CHANGE_ME")
    verification_token_secret = os.getenv("JWT_SECRET", "CHANGE_ME")

    async def validate_password(  # type: ignore[override]
        self, password: str, user: UserCreate | User
    ) -> None:
        if len(password) < 8:
            raise exceptions.InvalidPasswordException(
                reason="Le mot de passe doit faire au moins 8 caractères."
            )

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        _audit.info("AUTH_REGISTER user_id=%s ip=%s", user.id, _ip(request))

    async def on_after_login(
        self, user: User, request: Request | None = None, response=None
    ) -> None:
        _audit.info("AUTH_LOGIN_SUCCESS user_id=%s ip=%s", user.id, _ip(request))

    async def authenticate(self, credentials: OAuth2PasswordRequestForm) -> User | None:
        """An Apple-only account has no password: the form is refused, not crashed."""
        try:
            user = await self.get_by_email(credentials.username)
        except exceptions.UserNotExists:
            user = None
        if user is not None and user.hashed_password is None:
            self.password_helper.hash(credentials.password)  # same timing as a real check
            return None
        return await super().authenticate(credentials)

    async def oauth_callback(  # type: ignore[override]
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> User:
        existing = await self.user_db.get_by_email(account_email)
        user = await super().oauth_callback(
            oauth_name,
            access_token,
            account_id,
            account_email,
            expires_at,
            refresh_token,
            request,
            associate_by_email=associate_by_email,
            is_verified_by_default=is_verified_by_default,
        )
        if existing is None and user.hashed_password is not None:
            # The library gives a new OAuth user a random password nobody knows.
            user = await self.user_db.update(user, {"hashed_password": None})
        _audit.info(
            "%s user_id=%s oauth_name=%s ip=%s",
            "OAUTH_REGISTER" if existing is None else "OAUTH_LOGIN_SUCCESS",
            user.id,
            oauth_name,
            _ip(request),
        )
        return user


async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db, password_helper=password_helper)
