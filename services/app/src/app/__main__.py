"""Database migration and explicit administrator provisioning."""

import argparse
import asyncio
import getpass
import os
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.database import create_database, upgrade_database
from app.models import User
from app.schemas import Register
from app.security import PASSWORD_HASH


async def run_command(args: argparse.Namespace) -> None:
    engine = create_database(Settings().database_url)
    try:
        if args.command == "init-db":
            await upgrade_database(engine)
            print("Database migrated to head.")
        else:
            password = os.getenv("LEARNING_ADMIN_PASSWORD") or await run_in_threadpool(
                getpass.getpass, "Administrator password: "
            )
            payload = Register(
                username=args.username,
                first_name=args.first_name,
                last_name=args.last_name,
                password=password,
            )
            password_hash = await run_in_threadpool(
                PASSWORD_HASH.hash, payload.password.get_secret_value()
            )
            async with AsyncSession(engine) as session, session.begin():
                session.add(
                    User(
                        username=payload.username,
                        first_name=payload.first_name,
                        last_name=payload.last_name,
                        password_hash=password_hash,
                        role="admin",
                    )
                )
            print(f"Administrator {payload.username} created.")
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Learning platform administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Apply Alembic migrations")
    admin = commands.add_parser(
        "create-admin", help="Create an administrator with a securely entered password"
    )
    admin.add_argument("--username", required=True)
    admin.add_argument("--first-name", required=True)
    admin.add_argument("--last-name", required=True)
    args = parser.parse_args(argv)
    try:
        asyncio.run(run_command(args))
    except IntegrityError:
        parser.exit(1, "This username already exists; no account was changed.\n")
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed. Check DATABASE_URL and run init-db first.\n")
    except ValueError:
        parser.exit(
            1, "Invalid settings or account details; passwords need 12 to 128 characters.\n"
        )


if __name__ == "__main__":
    main()
