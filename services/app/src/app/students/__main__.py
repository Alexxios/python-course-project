"""Run with uv run --package app python -m app.students --help."""

import argparse
import json
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from app.students.database import create_database, upgrade_database
from app.students.repository import StudentRepository


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Assignment 6 student database")
    parser.add_argument("--database-url", help="Override STUDENTS_DATABASE_URL")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Apply Alembic migrations")
    importer = commands.add_parser("import-csv", help="Append all CSV rows in one transaction")
    importer.add_argument("path")
    students = commands.add_parser("students", help="List distinct students in a faculty")
    students.add_argument("--faculty", required=True)
    commands.add_parser("courses", help="List unique courses")
    low_grades = commands.add_parser(
        "low-grades", help="List students with a course grade below 30"
    )
    low_grades.add_argument("--course", required=True)
    average = commands.add_parser("average", help="Average all grade rows for a faculty")
    average.add_argument("--faculty", required=True)
    args = parser.parse_args(argv)
    engine = None
    try:
        engine = create_database(args.database_url)
        repository = StudentRepository(engine)
        match args.command:
            case "init-db":
                upgrade_database(engine)
                result = {"status": "ready"}
            case "import-csv":
                result = {"imported": repository.import_csv(args.path)}
            case "students":
                result = [s.model_dump() for s in repository.students_by_faculty(args.faculty)]
            case "courses":
                result = repository.unique_courses()
            case "low-grades":
                result = [s.model_dump() for s in repository.students_below_30(args.course)]
            case "average":
                result = {
                    "faculty": args.faculty,
                    "average_grade": repository.average_grade_by_faculty(args.faculty),
                }
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed. Check the URL and run init-db before queries.\n")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
