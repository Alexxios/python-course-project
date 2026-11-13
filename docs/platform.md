# Учебная платформа: API v1

## DEV-2

Application lifecycle, SQLAlchemy models, the initial Alembic migration,
SQLite/PostgreSQL connections, health probes, and `/v1` documentation.

## DEV-3

Student registration and login, rotating access/refresh sessions, logout,
password changes, current profile, and explicit administrator provisioning.

## DEV-4

Administrator CRUD for courses, ordered lessons, and questions; publication,
public catalog search/pagination, and content freeze after enrollment.

## DEV-5

Enrollment, sequential lesson access, completion, automatic test grading,
progress, and private attempt history.

Interactive docs: `/v1/docs`; OpenAPI: `/v1/openapi.json`.

Create an administrator after applying migrations:

```bash
uv run --package app python -m app create-admin --username admin --first-name Admin --last-name User
```

The CLI prompts for a password. Registration always creates a student account.

## Tests

Run `just check services/app`. Tests mirror `src/app/`, with one directory per
handler and shared fixtures in `conftest.py`. Temporary SQLite databases are
created and migrated per test. Set `TEST_DATABASE_URL` to run against a dedicated
PostgreSQL database with isolated schemas. The test database user must be allowed
to create and drop schemas.

## Async operations

The API uses SQLAlchemy `AsyncEngine` and per-request `AsyncSession` transactions.
SQLite runs through `aiosqlite`; PostgreSQL uses psycopg async connections.
Existing `sqlite:///...` and `postgresql+psycopg://...` URLs remain valid.
Database queries and readiness checks are awaited, and shutdown awaits disposal
of the connection pool. Alembic migrations use `AsyncConnection.run_sync`.
Password hashing and verification run in worker threads. Pure grading and
response projection remain synchronous computations.

Tests use AnyIO's asyncio backend and HTTPX `AsyncClient`. The application,
fixtures, requests, and pooled connections share a single event loop per test.
Each request/task gets its own session. Blocking SQL and password regression
tests verify that liveness remains responsive while those operations are pending.
