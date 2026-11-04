"""OAuthAccount — the Apple identity linked to a User (same table as Tangent).

CaseDuo only has the native Sign in with Apple flow: no access token to
keep, so `access_token` stores a marker, never the identity token itself.
"""

from __future__ import annotations

import uuid

from fastapi_users.db import SQLAlchemyBaseOAuthAccountTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = "oauth_account"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="cascade"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("oauth_name", "account_id", name="uq_oauth_account_provider_id"),
    )
