"""
Admin CLI: add (or remove) an underwriter's email from the FinScan allowlist.

`users.authorized` in Postgres is the source of truth (apps/api/db/models.py::UserModel).
AUTHORIZED_EMAILS/AUTHORIZED_DOMAINS only seed that column on a user's FIRST login
(apps/api/auth/allowlist.py::seed_authorized) - editing the env var does nothing for
someone who already tried logging in and got denied, since their row already exists
with authorized=false. This script is the "admin flip" UserModel's docstring refers to:
it works for both a brand-new email (creates the row, pre-authorized before they ever
log in) and an existing denied one (flips the row), with one command, no SQL by hand.

Usage (run from the API container, or locally with DATABASE_URL pointed at the same
Postgres - venv must have the project installed):
    python scripts/authorize_user.py add alice@example.com
    python scripts/authorize_user.py add bob@example.com --role RISK_ANALYST
    python scripts/authorize_user.py remove alice@example.com
    python scripts/authorize_user.py list
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from sqlalchemy import select  # noqa: E402

from apps.api.db.models import UserModel  # noqa: E402
from apps.api.db.session import async_session_factory  # noqa: E402

VALID_ROLES = ("SENIOR_UNDERWRITER", "RISK_ANALYST", "COMPLIANCE_OFFICER")


async def add(email: str, role: str) -> None:
    email = email.lower().strip()
    async with async_session_factory() as session:
        res = await session.execute(select(UserModel).where(UserModel.email == email))
        user = res.scalar_one_or_none()
        if user is None:
            user = UserModel(email=email, role=role, authorized=True)
            session.add(user)
            print(f"Created and authorized {email} (role={role}).")
        else:
            user.authorized = True
            user.role = role
            user.updated_at = datetime.now(timezone.utc)
            print(f"Authorized existing user {email} (role={role}).")
        await session.commit()


async def remove(email: str) -> None:
    email = email.lower().strip()
    async with async_session_factory() as session:
        res = await session.execute(select(UserModel).where(UserModel.email == email))
        user = res.scalar_one_or_none()
        if user is None:
            print(f"No such user: {email}")
            return
        user.authorized = False
        user.updated_at = datetime.now(timezone.utc)
        await session.commit()
        print(f"Revoked access for {email}.")


async def list_users() -> None:
    async with async_session_factory() as session:
        res = await session.execute(select(UserModel).order_by(UserModel.email))
        users = res.scalars().all()
        if not users:
            print("No users in the allowlist yet.")
            return
        for u in users:
            flag = "AUTHORIZED" if u.authorized else "denied"
            print(f"{u.email:40s} {u.role:20s} {flag}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Authorize an email (creates the user row if needed).")
    p_add.add_argument("email")
    p_add.add_argument("--role", choices=VALID_ROLES, default="SENIOR_UNDERWRITER")

    p_remove = sub.add_parser("remove", help="Revoke an email's access (row kept, authorized=false).")
    p_remove.add_argument("email")

    sub.add_parser("list", help="List every user and their authorization status.")

    args = parser.parse_args()
    if args.cmd == "add":
        asyncio.run(add(args.email, args.role))
    elif args.cmd == "remove":
        asyncio.run(remove(args.email))
    elif args.cmd == "list":
        asyncio.run(list_users())


if __name__ == "__main__":
    main()
