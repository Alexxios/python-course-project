# app

[![lint](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/services/app/badges/lint.json)](https://alexxios.github.io/python-course-project/reports/services/app/)
[![tests](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/services/app/badges/tests.json)](https://alexxios.github.io/python-course-project/reports/services/app/)
[![coverage](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/services/app/badges/coverage.json)](https://alexxios.github.io/python-course-project/reports/services/app/)

Final project: **Учебная платформа**, a FastAPI backend under `/v1` with SQLAlchemy
and Alembic. It implements authentication, admin course/lesson/test CRUD,
sequential learning, automatic grading, private progress and grade history,
and personalized practice.

From the workspace root:

```bash
just bootstrap
uv run --package app python -m app init-db
uv run --package app python -m app create-admin --username admin --first-name Admin --last-name User
uv run --package app uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000/v1/docs>. The default database is `learning.sqlite3` in
the working directory. Export `DATABASE_URL` for a different SQLite path or a
`postgresql+psycopg://` connection. Run migrations explicitly before the server.
An administrator password is prompted securely; no default account is installed.

For containers, `docker compose up --build -d` at the workspace root starts
PostgreSQL, runs migrations, and starts the API. The existing Dockerfile installs
locked runtime dependencies and starts Uvicorn on port 80. The root Compose file
publishes port 8000 on localhost. PostgreSQL data lives in a named volume.

Database work uses SQLAlchemy async sessions with `aiosqlite` or psycopg.
AI requests use HTTPX `AsyncClient`; password work runs in worker threads.
Tests use AnyIO and HTTPX on one asyncio loop per test.

See the [API guide](../../docs/platform.md) for every endpoint, data model,
authorization and grading rules, and optional AI configuration. See the
[quickstart](../../docs/quickstart.md) for deployment and development commands.

## Structure

```text
src/app/
├── main.py             # Application assembly, /v1 router, and lifecycle
├── __main__.py         # Migration and administrator CLI
├── config.py           # Environment settings
├── database.py         # Engines and migrations
├── models.py           # SQLAlchemy entities
├── schemas.py          # Validated API contracts
├── dependencies.py     # Transactions, authentication, and authorization
├── security.py         # Password hashing and bearer tokens
├── learning.py         # Prerequisites, progress, and grading
├── practice.py         # Local and AI quiz generation
├── migrations/         # Packaged Alembic revisions
└── routers/
    ├── health.py       # Unversioned infrastructure probes
    └── v1/             # Versioned business API
        ├── __init__.py # /v1 prefix and router registration
        ├── auth.py
        ├── admin.py
        ├── learning.py
        └── practice.py
```

`tests/` mirrors `src/app/`. Each handler has its own directory, such as
`tests/routers/v1/auth/refresh/` or `tests/routers/v1/admin/create_course/`.
Non-router tests follow the same convention, for example `tests/learning/grade_answers/`.
The root `conftest.py` owns database/client fixtures; `routers/v1/conftest.py`
provides accounts and course factories. Router-level fixtures provide enrollment,
registration, and practice setup without sharing mutable state between tests.

Run one handler's tests from the workspace root:

```bash
uv run --package app pytest -c services/app/pyproject.toml services/app/tests/routers/v1/auth/refresh
```

Run `just check services/app` for the service or `just check` for all scopes,
generated README validation, and documentation. The suite uses pytest, coverage,
Allure, Hypothesis, Schemathesis, and RESPX. Set `TEST_DATABASE_URL` to a dedicated
PostgreSQL test database to run the API tests in isolated PostgreSQL schemas.

Manage runtime version bounds in the root `pyproject.toml`. This member declares
dependency names and extras without bounds; the shared `uv.lock` controls the
resolved versions.

## Health and Kubernetes

`/health/live` checks responsiveness. `/health/ready` returns 503 unless the
lifecycle is ready and the database user table is accessible.

For Kubernetes, configure `k8s/kustomization.yaml` with the release image and
provide a Secret named `learning-platform` containing `database-url`. Set the
same image in the standalone `k8s/migration-job.yaml`, apply that job, and wait
for completion before applying the deployment. Run a fresh migration job for
each release. The manifests do not provision PostgreSQL. The Service is internal
and exposes the container's port 80. Health probes retain their existing paths.
