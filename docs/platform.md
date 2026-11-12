# Учебная платформа: API v1

## DEV-2

Application lifecycle, SQLAlchemy models, the initial Alembic migration,
SQLite/PostgreSQL connections, health probes, and `/v1` documentation.

Interactive docs: `/v1/docs`; OpenAPI: `/v1/openapi.json`.

## Tests

Run `just check services/app`. Tests mirror `src/app/`, with one directory per
handler and shared fixtures in `conftest.py`. Temporary SQLite databases are
created and migrated per test. Set `TEST_DATABASE_URL` to run against a dedicated
PostgreSQL database with isolated schemas. The test database user must be allowed
to create and drop schemas.
