# Developer quickstart

The selected final-project theme is **Учебная платформа**. The business API and
interactive documentation are versioned under `/v1`. Earlier homework solutions
remain on the `ASSIGNMENT-4` and `ASSIGNMENT-6` branches.

## Local development

Install Python 3.14+, [uv](https://docs.astral.sh/uv/getting-started/installation/)
and Just, then run from the repository root:

```bash
uv tool install rust-just
just bootstrap
uv run pre-commit install
uv run --package app python -m app init-db
uv run --package app python -m app create-admin --username admin --first-name Admin --last-name User
uv run --package app uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir services/app/src
```

The administrator command prompts for a password of 12 to 128 characters. No
default administrator is created. Open <http://127.0.0.1:8000/v1/docs>, call
`POST /v1/auth/login` with your username and password, and paste the returned
access token into **Authorize**. Use the administration endpoints to create a
course, its ordered lessons, and test questions, then publish the course.

Register a separate student with `POST /v1/auth/register`, log in as that student,
enroll in a published course, and progress through its lessons. The
[API guide](platform.md) describes every endpoint and the grading rules.

The default database is `learning.sqlite3` relative to the current working
directory. It is excluded from Git and Docker build contexts. The application
does not create tables on startup: run `init-db` before serving requests. The
command applies packaged Alembic migrations and is safe to repeat.

To choose an absolute SQLite path or PostgreSQL, export `DATABASE_URL` before
running both the migration and the server:

```bash
export DATABASE_URL=sqlite:////absolute/existing/directory/learning.sqlite3
# Or connect to your PostgreSQL database:
# export DATABASE_URL=postgresql+psycopg://app:app@127.0.0.1:5432/app
uv run --package app python -m app init-db
```

The SQLite parent directory must exist. CLI/server settings come from process
environment variables; `.env` is used by Docker Compose, not loaded implicitly
by the Python application. `just bootstrap` creates `.env` from `.env.example`
only when it is missing.

## Docker Compose

Start Docker Engine or Docker Desktop, then run:

```bash
docker compose up --build -d
docker compose ps
docker compose exec api uv run --no-sync python -m app create-admin --username admin --first-name Admin --last-name User
```

The root `compose.yml` builds the existing service Dockerfile, starts PostgreSQL,
waits for database health, runs migrations, and starts the API. The migration
container exits successfully after applying the schema. PostgreSQL is reachable
only inside the Compose network. The API binds to `127.0.0.1:8000` by default;
set `APP_PORT` in `.env` to change that port. Database data persists in the
`learning-postgres-data` volume.

`POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` default to `app` for local
development. Override them in `.env` before the first startup. Use URL-safe
credentials (letters, digits, `_`, `-`) with this local Compose template, which
interpolates them into the connection URL. The optional monitoring/development infrastructure remains in
`infra/docker-compose.yml`; it is independent of the root application stack.

Inspect logs with `docker compose logs api migrate`. Stop containers with
`docker compose down`; the database volume is retained.

## Check the service

```bash
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8000/v1/courses
just check
```

Liveness reports whether the app can respond. Readiness checks the lifecycle and
database schema access, returning 503 before migration or during a database
outage. The catalog initially contains no courses.

`just check` validates generated documentation, builds MkDocs, runs Ruff, and
executes pytest in isolated member environments. Each scope emits coverage,
JUnit, and Allure artifacts under `reports/`. `just check services/app` checks
only the API service. See [tests](platform.md#tests) for PostgreSQL and fuzz runs.

## Daily workflow

```bash
just format
just check
```

Keep runtime version bounds in the root `pyproject.toml`. Declare dependency
names and extras without bounds in consuming members, and commit the shared
`uv.lock` alongside manifest changes. Edit `templates/readme/*.jinja` for the
generated workspace README and run `just codegen`.

`just new-service <name>` and `just new-lib <name>` still scaffold workspace
members. API tests live in `services/app/tests/`; root `tests/` is the separate
integration scope. `just docs`, `just serve`, and `just reports` retain the
existing documentation and reporting workflows. See [Development tools](tools.md)
and [CI reports](ci-reports.md) for the shared tooling.
