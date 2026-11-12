# Developer quickstart

Use Python 3.14, uv, and Just. From the workspace root:

```bash
just bootstrap
uv run pre-commit install
uv run --package app python -m app init-db
uv run --package app uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/v1/docs>. SQLite is the default; set `DATABASE_URL`
to use PostgreSQL. Apply migrations before starting the server.
`/health/live` checks responsiveness; `/health/ready` checks database readiness.

Run `just check` for all checks, or `just check services/app` for the service.
Tests mirror the service source tree and use isolated databases.
See the [API guide](platform.md), [tools](tools.md), and [CI reports](ci-reports.md).
