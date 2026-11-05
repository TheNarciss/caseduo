"""Small admin CLI, run inside the backend container.

    python -m app.cli create-user EMAIL [--admin] [--name "Clément"]   (asks the password)
    python -m app.cli make-admin EMAIL

There is no sign-up form in the app (DEVIATIONS D8): the owner's account is
created here, or by Sign in with Apple.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import select

from .auth import User, UserCreate
from .auth.manager import UserManager, password_helper
from .auth.oauth_models import OAuthAccount
from .db import async_session_factory


async def create_user(email: str, password: str, *, admin: bool, name: str | None) -> None:
    async with async_session_factory() as session:
        manager = UserManager(
            SQLAlchemyUserDatabase(session, User, OAuthAccount),  # type: ignore[type-var]
            password_helper=password_helper,
        )
        try:
            user = await manager.create(
                UserCreate(
                    email=email,
                    password=password,
                    is_superuser=admin,
                    is_verified=True,
                    display_name=name,
                ),
                safe=False,
            )
        except UserAlreadyExists:
            print(f"{email} existe déjà.", file=sys.stderr)
            sys.exit(1)
        print(f"Compte créé : {user.email} (admin={user.is_superuser})")


async def make_admin(email: str) -> None:
    async with async_session_factory() as session:
        stmt = select(User).where(User.email == email)  # type: ignore[arg-type]
        user = (await session.execute(stmt)).unique().scalar_one_or_none()
        if user is None:
            print(f"{email} introuvable.", file=sys.stderr)
            sys.exit(1)
        user.is_superuser = True
        await session.commit()
        print(f"{email} est administrateur.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_create = sub.add_parser("create-user")
    p_create.add_argument("email")
    p_create.add_argument("--admin", action="store_true")
    p_create.add_argument("--name")
    p_admin = sub.add_parser("make-admin")
    p_admin.add_argument("email")
    args = parser.parse_args()

    if args.cmd == "create-user":
        password = os.getenv("CASEDUO_PASSWORD") or getpass.getpass("Mot de passe : ")
        asyncio.run(create_user(args.email, password, admin=args.admin, name=args.name))
    elif args.cmd == "make-admin":
        asyncio.run(make_admin(args.email))


if __name__ == "__main__":
    main()
