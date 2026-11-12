# app

Учебная платформа: a FastAPI service with SQLAlchemy and Alembic.

From the workspace root, run `just bootstrap`, then
`uv run --package app python -m app init-db` and
`uv run --package app uvicorn app.main:app --reload`.
The default database is a local SQLite file; export `DATABASE_URL` to use
PostgreSQL. SQLite uses `aiosqlite`; PostgreSQL uses psycopg async connections.
Existing `sqlite:///...` and `postgresql+psycopg://...` URLs remain supported.
Interactive API documentation is at `/v1/docs`.

The application uses `AsyncEngine` and `async_sessionmaker`; database operations
and readiness checks are awaited. Migrations run through an async connection,
and shutdown awaits connection-pool disposal. Tests use AnyIO with the asyncio
backend and HTTPX `AsyncClient` on the same event loop.

Business routers live in `src/app/routers/v1/`; infrastructure probes live in
`src/app/routers/health.py`. Tests mirror `src/app/`, grouped by handler, and use
fixtures from the nearest `conftest.py`. Run `just check services/app`.

See the [API guide](../../docs/platform.md) and [quickstart](../../docs/quickstart.md).
