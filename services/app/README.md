# app

Учебная платформа: a FastAPI service with SQLAlchemy and Alembic.

From the workspace root, run `just bootstrap`, then
`uv run --package app python -m app init-db` and
`uv run --package app uvicorn app.main:app --reload`.
The default database is a local SQLite file; export `DATABASE_URL` to use
PostgreSQL. Interactive API documentation is at `/v1/docs`.

Business routers live in `src/app/routers/v1/`; infrastructure probes live in
`src/app/routers/health.py`. Tests mirror `src/app/`, grouped by handler, and use
fixtures from the nearest `conftest.py`. Run `just check services/app`.

See the [API guide](../../docs/platform.md) and [quickstart](../../docs/quickstart.md).
