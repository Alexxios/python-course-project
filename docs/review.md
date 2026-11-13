# Final project review branches

The learning platform is split into six cumulative branches. Review each branch
against its immediate predecessor so its diff contains only that feature.
`DEV-1` and the assignment branches are existing work and are unchanged.

| Branch | Review base | Scope |
| --- | --- | --- |
| `DEV-2` | `main` (`ab14799`) | Application/database foundation, models, initial migration, health checks, v1 routing, removal of the old appeals example |
| `DEV-3` | `DEV-2` | Registration, login, rotating sessions, logout, password changes, profile, administrator CLI |
| `DEV-4` | `DEV-3` | Administrator course/lesson/question CRUD, published catalog, content freeze after enrollment |
| `DEV-5` | `DEV-4` | Enrollment, sequential lessons, completion, grading, progress, private attempt history |
| `DEV-6` | `DEV-5` | Personalized practice, local generation and optional AI provider |
| `DEV-7` | `DEV-6` | PostgreSQL Compose/CI, Kubernetes migration job, complete API and development documentation |

Each feature branch includes its own async implementation and tests.
`DEV-2` adds async engines, migrations, lifecycle handling, and database regression
tests. Later branches await their database operations; authentication offloads
password work and practice awaits provider HTTP calls. The published foundation
commit remains in history, with async support added as a follow-up commit.

The shared database schema and dependency lock are introduced in `DEV-2`; subsequent branches enable their
respective routes. All business routers live under `src/app/routers/v1/`, with
the `/v1` prefix registered once in that package. Infrastructure probes stay in
`routers/health.py` at their existing URLs.

Tests mirror the source tree. For example, `auth.refresh` is covered by
`tests/routers/v1/auth/refresh/`, while `learning.grade_answers` is covered by
`tests/learning/grade_answers/`. Fixtures in the nearest `conftest.py` provide
shared setup. Temporary databases and accounts are isolated per test.

```bash
# Inspect one review unit.
git diff DEV-3...DEV-4

# Work with the complete project.
git switch DEV-7
just check

# Run only the refresh handler tests.
uv run --package app pytest -c services/app/pyproject.toml services/app/tests/routers/v1/auth/refresh
```

Merge in numerical order, targeting each review at the base in the table.
After its predecessor lands, retarget the next review to `main`.
The original unsplit implementation is preserved locally on
`backup/final-project-before-split` (`9391a7c`). No remote history is rewritten.

The previous synchronous review stack is preserved locally on
`backup/before-async` (`c4a0351`).
