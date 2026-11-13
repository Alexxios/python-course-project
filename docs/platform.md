# Учебная платформа: API v1

The final project implements theme 5 from the course brief: a backend for a
learning platform. All business endpoints are under `/v1`. Interactive docs are
at `/v1/docs`, ReDoc at `/v1/redoc`, and OpenAPI at `/v1/openapi.json`.

Follow the [quickstart](quickstart.md) for SQLite development or the PostgreSQL
Docker Compose stack. The [review stack](review.md) ends at `DEV-7`. Assignments 4 and
6 remain on their dedicated remote branches.

## Requirements and implementation

| Brief requirement | Implementation |
| --- | --- |
| Course catalog | Public, published courses; title search and pagination |
| Course, lesson, and test data model | SQLAlchemy models, foreign keys, constraints, and Alembic migration |
| User registration and authentication | Student registration, login, bearer sessions, refresh rotation, password changes, logout |
| Administrator CRUD | Separate course, lesson, and question endpoints under `/v1/admin` |
| Sequential course completion | Enrollment and prerequisites checked for every lesson read, completion, and test submission |
| Previously learned content | Completed lessons remain accessible for revision |
| Automatic test grading | Server-side answer validation, score calculation, passing threshold, and attempt history |
| Personal cabinet | Current profile, enrolled courses, completion percentages, and private grades |
| Personalized test generation | Local adaptive question selection and optional AI generation from completed lessons |
| Deployment | Existing Dockerfile plus Compose files in `infra/` with shared PostgreSQL and migration startup dependency |
| Testing | Endpoint, authorization, persistence, migration, property, and OpenAPI tests |

Optional video links are supported on lessons. Teacher accounts and course
reviews are not part of this implementation; course authoring uses the
administrator role specified in the backend requirements.

## Authentication

All bodies and results are JSON. Public registration always creates a `student`;
clients cannot choose their role. Provision an administrator using the CLI:

```bash
uv run --package app python -m app create-admin --username admin --first-name Admin --last-name User
```

The command prompts for a password. For noninteractive provisioning, supply it
through `LEARNING_ADMIN_PASSWORD` in the command's environment. Existing accounts
are never silently promoted or overwritten.

```bash
curl --fail-with-body http://127.0.0.1:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"student","first_name":"Иван","last_name":"Ли","password":"a unique long example password"}'

curl --fail-with-body http://127.0.0.1:8000/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"student","password":"a unique long example password"}'
```

Login returns `access_token`, `refresh_token`, `token_type: "bearer"`, and
`expires_in` in seconds. Send `Authorization: Bearer <access_token>` for protected
requests. Swagger's **Authorize** button accepts the access token directly.

Usernames contain 3–50 ASCII letters, digits, or underscores and are normalized
to lowercase. Names are required. Passwords contain 12–128 characters and are
stored using Argon2id. Tokens are cryptographically random opaque values; only
SHA-256 token digests are stored in the database. Responses never contain password
hashes. Access tokens expire after 15 minutes and refresh tokens after 7 days by
default. `ACCESS_TOKEN_SECONDS` and `REFRESH_TOKEN_SECONDS` configure those limits.

Refresh tokens are single use: refresh replaces both tokens and invalidates the
old access token. Logout revokes the current token pair. A password change checks
the current password and revokes every session; log in again afterward.

| Method | Path | Request / purpose |
| --- | --- | --- |
| POST | `/v1/auth/register` | `username`, `first_name`, `last_name`, `password`; returns 201 |
| POST | `/v1/auth/login` | `username`, `password`; returns a token pair |
| POST | `/v1/auth/refresh` | `refresh_token`; rotates the token pair |
| POST | `/v1/auth/change-password` | `current_password`, `new_password`; returns 204 |
| POST | `/v1/auth/logout` | Revoke current session; returns 204 |
| GET | `/v1/me` | Current user's public profile |

## Administrator API

Every `/v1/admin` operation requires an administrator access token. `POST` returns
201, `GET` and `PUT` return 200, and successful `DELETE` returns 204. Updates use
full `PUT` bodies; omitted optional fields take their defaults.

| Resource | Collection operations | Individual operations |
| --- | --- | --- |
| Courses | `GET/POST /v1/admin/courses` | `GET/PUT/DELETE /v1/admin/courses/{course_id}` |
| Lessons | `GET/POST /v1/admin/courses/{course_id}/lessons` | `GET/PUT/DELETE /v1/admin/lessons/{lesson_id}` |
| Questions | `GET/POST /v1/admin/lessons/{lesson_id}/questions` | `GET/PUT/DELETE /v1/admin/questions/{question_id}` |

A course starts unpublished. Create it with `title`, optional `description`, and
`passing_score` (1–100, default 70). Add lessons before publishing it through
`PUT /v1/admin/courses/{id}` with `published: true`. Course lists accept an optional
`published` filter.

A lesson has `title`, `description`, nonempty text `content`, positive `position`,
and optional HTTP(S) `video_url`. Positions are unique within the course and need
not be contiguous. A lesson's test consists of its ordered question records.

```json
{
  "prompt": "Which Python collection is mutable?",
  "options": ["list", "tuple"],
  "correct_option": 0,
  "position": 1
}
```

Questions have 2–6 distinct options, a zero-based `correct_option`, and a unique
positive position within the lesson. A lesson supports at most 100 questions.
Only administrator responses contain answer keys.

Once anyone enrolls, course settings, lessons, and questions cannot be edited or
deleted (409). Create a new course revision instead. This keeps prerequisites,
grades, and completion history consistent. Before enrollment, deletions cascade
through dependent lesson/question records. Unpublish a course before deleting its
last lesson.

## Student API and learning rules

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/courses` | Public published catalog; `search`, `limit`, `offset` |
| GET | `/v1/courses/{course_id}` | Public course description |
| POST | `/v1/courses/{course_id}/enroll` | Enroll current user; returns 201 and progress |
| GET | `/v1/courses/{course_id}/lessons` | Enrolled user's lesson outline with unlocked/completed flags |
| GET | `/v1/lessons/{lesson_id}` | Accessible lesson content and questions without answer keys |
| POST | `/v1/lessons/{lesson_id}/complete` | Complete a lesson without a test, or return existing completion |
| POST | `/v1/lessons/{lesson_id}/attempts` | Submit and grade all questions; returns 201 |
| GET | `/v1/me/courses` | Paginated enrolled courses with progress |
| GET | `/v1/me/courses/{course_id}/progress` | Progress and next lesson for one enrollment |
| GET | `/v1/me/attempts` | Private grade history; optional `course_id` and `lesson_id` filters |

Only the catalog and public course descriptions are anonymous. Enrollment is
required to see lesson content. The first lesson is unlocked immediately; all
earlier lessons must be complete to access a later lesson. The outline never
exposes locked content. Completed lessons remain accessible.

Submit exactly one selected option for every question in the lesson:

```json
{"answers": [{"question_id": 1, "option": 0}]}
```

Missing, extra, duplicate, or out-of-range answers return 422 without recording an
attempt. Valid answers produce `correct_count`, `question_count`, `score`, and
`passed`. Score is the percentage of correct answers, rounded to two decimals for
display. Passing uses the exact ratio against the course threshold. A passed test
automatically completes the lesson. Failed tests can be retried; every valid
attempt is retained. A later failed retry does not revoke an earned completion.

The completion endpoint cannot bypass a required test. Completion is idempotent.
Progress is calculated as completed lessons divided by the total, not accepted
from client input. Separate users have separate enrollments, completions, and
grade histories. Duplicate enrollment returns 409.

Paginated collections return `{items, total, limit, offset}`, with default limit
20, maximum 100, and stable ordering. Resource IDs and offsets are bounded by
the database's signed 32-bit integer range. The curriculum is returned as an ordered
outline. Grades and practice quizzes are listed newest first.

## Personalized practice

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/me/practice-quizzes` | Generate with `course_id` and `question_count` (1–10, default 5) |
| GET | `/v1/me/practice-quizzes` | Current user's paginated practice history |
| GET | `/v1/me/practice-quizzes/{quiz_id}` | Retrieve a private quiz |
| POST | `/v1/me/practice-quizzes/{quiz_id}/submit` | Submit one answer per generated question |

At least one lesson must be completed. Generated questions use their own IDs
within the practice quiz and identify a `source_lesson_id`. Answer keys remain
server-side. A quiz can be submitted once; generate another for a retry. Practice
scores do not modify course progress or replace required lesson tests.

`QUIZ_GENERATOR=local` is the default and needs no external service. It selects
questions from completed lessons, prioritizing lessons with lower average test
scores, then course order. It returns up to the requested number when fewer
questions are available, or 409 if completed lessons have no questions. This is
adaptive question-bank selection, not AI generation.

For new AI-generated questions, configure:

```bash
export QUIZ_GENERATOR=openai
export OPENAI_API_KEY='your-api-key'
export OPENAI_MODEL='your-compatible-model-id'
```

Choose a model available to your account that supports Responses structured
outputs. The integration uses the
[OpenAI Responses API with Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
Only titles, IDs, and text excerpts from completed lessons are sent (up to ten
lessons and 2,000 characters per lesson). Identity, credentials, and grades are
not sent; provider response storage is disabled. The generator validates answer
options, requested count, and source lesson IDs before storing anything.
Unconfigured AI returns 503; timeout, refusal, malformed output, or a question
referencing unlearned material returns 502. It does not silently switch providers.
AI questions may be imperfect and are used for revision, not official grading.

## Data, migrations, and deployment

The nine application tables are `users`, `auth_sessions`, `courses`, `lessons`,
`questions`, `enrollments`, `completions`, `attempts`, and `practice_quizzes`.
`alembic_version` tracks migrations. All timestamps are UTC Unix seconds. Foreign
keys are enabled in SQLite as well as PostgreSQL. Writes use request-scoped
transactions that commit before a response is sent or roll back on failure.

Migrations are packaged with the service and run with `python -m app init-db`.
The API never automatically creates or upgrades a schema. See the
[quickstart](quickstart.md#docker-compose) for the Compose stack in `infra/`. In Kubernetes,
provide the `learning-platform` Secret with a `database-url` key and run the
`services/app/k8s/migration-job.yaml` job with the same release image before
rolling out the deployment. Set the job image as well as the Kustomize image;
the standalone job is not part of the deployment's Kustomization.

Readiness requires database access and an initialized user table. Liveness stays
independent of the database. Application errors use 401 for invalid credentials,
403 for permissions/prerequisites, 404 for missing or private resources, 409 for
conflicts, and 422 for input validation. Database failures return 503 without
exposing SQL, credentials, or connection paths.

## Tests

```bash
just check
just check services/app
HYPOTHESIS_PROFILE=fuzz just test services/app
```

Tests cover every endpoint, authentication and role boundaries, refresh replay
and expiry, password change revocation, CRUD, frozen enrolled courses, sequential
access, grading, progress, privacy, migrations, and AI validation. All AI calls in
tests use RESPX mocks; no key or paid request is needed. Hypothesis checks grading
properties; Schemathesis generates catalog requests. Reproduce a reported seed
by running the relevant module from `services/app/`:

```bash
uv run --package app pytest tests/integration/routers/v1/test_learning.py -m fuzz --hypothesis-seed=<seed>
```

Unit tests under `services/app/tests/unit/` cover package metadata and pure
grading logic, with mocks or patches for external dependencies. Integration
tests under `services/app/tests/integration/` cover API, OpenAI provider,
database, migration, CLI, and concurrency behavior using SQLite.

Both suites mirror directories under `src/app/`. Tests for a single source file
are named `test_<filename>.py`: `routers/v1/auth.py` maps to
`tests/integration/routers/v1/test_auth.py`, and `learning.py` maps to
`tests/unit/test_learning.py`. Database/client fixtures live in
`tests/integration/conftest.py`; shared API factories live in
`tests/integration/routers/v1/conftest.py`. Module-specific fixtures live in the
corresponding test file.

Run both suites with `just test services/app`. From `services/app/`, select one
with `uv run --package app pytest tests/unit` or
`uv run --package app pytest tests/integration`. Select a handler with, for example,
`uv run --package app pytest tests/integration/routers/v1/test_auth.py -k refresh`.

Integration fixtures create a temporary SQLite database per test and apply
migrations. API fuzz examples use fresh in-memory SQLite databases. PostgreSQL
integration coverage is deferred; the existing PostgreSQL row-lock concurrency
test is explicitly skipped. CI does not start a database service for these tests.
Coverage, JUnit, and Allure output for both suites go under `reports/services/app/`.
The separate root `tests/` scope remains available for workspace-level integration
tests and reports under `reports/integration/`.

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

AI requests use HTTPX `AsyncClient`; a regression test checks liveness while
a provider response is pending. No live provider calls are made in tests.
