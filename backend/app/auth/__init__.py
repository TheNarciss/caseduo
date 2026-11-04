"""Auth module — fastapi-users with a cookie JWT backend (same as Tangent).

Exports:
- fastapi_users: singleton
- current_active_user / current_superuser: FastAPI dependencies
- User, OAuthAccount, Base, schemas
"""

import uuid

from fastapi_users import FastAPIUsers

from .backend import auth_backend
from .manager import get_user_manager
from .models import Base, User
from .oauth_models import OAuthAccount
from .schemas import UserCreate, UserRead, UserUpdate

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])  # type: ignore[type-var]

current_user = fastapi_users.current_user()
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
current_active_user_optional = fastapi_users.current_user(active=True, optional=True)

__all__ = [
    "Base",
    "OAuthAccount",
    "User",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "auth_backend",
    "current_active_user",
    "current_active_user_optional",
    "current_superuser",
    "current_user",
    "fastapi_users",
]
