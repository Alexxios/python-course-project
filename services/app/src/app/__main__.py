"""Apply database migrations before starting the learning platform."""

import argparse
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import create_database, upgrade_database


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Learning platform administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Apply Alembic migrations")
    parser.parse_args(argv)
    engine = None
    try:
        engine = create_database(Settings().database_url)
        upgrade_database(engine)
        print("Database migrated to head.")
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed. Check DATABASE_URL.\n")
    except ValueError:
        parser.exit(1, "Invalid database settings.\n")
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
