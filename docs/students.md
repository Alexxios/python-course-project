# Student grades (Assignment 6)

The student module implements every Assignment 6 requirement, including the
optional query for students with a course grade below 30. It uses SQLAlchemy,
Alembic, and the existing FastAPI service, uv workspace, Just commands, Ruff,
pytest, Hypothesis, Schemathesis, coverage, and Allure reports.

`ASSIGNMENT-4` preserves the earlier subscriber appeals solution.
`ASSIGNMENT-6` adds this student database solution. The appeals API remains available.

## Run the supplied data

From the repository root:

```bash
just bootstrap
uv run --package app python -m app.students init-db
uv run --package app python -m app.students import-csv services/app/examples/students.csv
uv run --package app python -m app.students students --faculty АВТФ
uv run --package app python -m app.students courses
uv run --package app python -m app.students low-grades --course 'Мат. Анализ'
uv run --package app python -m app.students average --faculty ФПМИ
```

The import returns `{"imported": 215}`. There are six distinct courses and ten
distinct students in АВТФ. The ФПМИ average is `49.225`.
The CSV in `services/app/examples/students.csv` is an unchanged copy of the
supplied assignment data, included so these commands work in a fresh checkout.

The default database is `students.sqlite3` in the current working directory.
Run the CLI and server from the same directory, or configure an absolute path:

```bash
export STUDENTS_DATABASE_URL=sqlite:////absolute/existing/directory/students.sqlite3
uv run --package app python -m app.students init-db
```

The parent directory must exist and be writable. Database files are ignored by
Git. SQLite requires no separate database server or driver installation.
All CLI commands also accept `--database-url URL` **before** the subcommand.
`init-db` explicitly applies packaged Alembic migrations and is safe to repeat.
The HTTP server does not create tables or import data automatically.

## Model and query semantics

`app.students.models.StudentGrade` stores one CSV row per database record:

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | Integer primary key | Unique identifier for an observation |
| `last_name` | String, at most 200 characters | Фамилия |
| `first_name` | String, at most 200 characters | Имя |
| `faculty` | String, at most 200 characters | Факультет |
| `course` | String, at most 200 characters | Курс (subject name) |
| `grade` | Integer from 0 to 100 | Оценка |

The CSV contains repeated student/course observations, including one exact
duplicate. All 215 rows are retained. There is deliberately no uniqueness
constraint on names or student/course pairs. Each faculty average is SQL `AVG`
over **all grade rows** in that faculty, including repeated observations; it is
not an average of per-student averages.

Student lists are distinct `(last_name, first_name, faculty)` triples, ordered
by those fields. The source supplies no student ID, so namesakes within the same
faculty cannot be distinguished. Students with a matching course and **any grade
strictly below 30** appear once in the optional query; a grade of 30 is excluded.
Course names are distinct and sorted. Faculty and course filters are exact,
case-sensitive matches with bound SQL parameters. Unknown filters return empty
lists; a faculty with no grades has an average of `null`.

Names, faculty, and course are nonempty UTF-8 text; surrounding whitespace is
trimmed. Input validation rejects invalid grades, extra API fields, and malformed
Unicode. Database constraints also enforce nonempty text and the grade range.
Indexes cover faculty lookups and course/grade filtering.

## Repository and CSV import

`app.students.repository.StudentRepository` provides the required INSERT and
SELECT class:

| Method | Result |
| --- | --- |
| `insert(GradeCreate(...))` | Persisted grade with its generated ID |
| `select_all()` | All grade records ordered by ID |
| `import_csv(path)` | Number of imported rows |
| `students_by_faculty(faculty)` | Distinct students in that faculty |
| `unique_courses()` | Sorted distinct course names |
| `students_below_30(course)` | Distinct students with a grade below 30 for the course |
| `average_grade_by_faculty(faculty)` | Average grade, or `None` for no records |

For example, from Python in the service environment:

```python
from app.students.database import create_database, upgrade_database
from app.students.repository import StudentRepository

engine = create_database()
try:
    upgrade_database(engine)
    repository = StudentRepository(engine)
    print(repository.unique_courses())
    print(repository.average_grade_by_faculty("ФПМИ"))
finally:
    engine.dispose()
```

The importer accepts UTF-8 with or without a BOM, quoted CSV values, and the exact
five Russian headers in any order. It reports invalid rows by CSV line number.
Every import runs in one transaction: malformed rows, invalid values, decoding
errors, and database failures roll back that import, preserving existing records.
A file containing only the correct header imports zero rows.

Import is **append-only**. Reimporting the file adds another 215 observations.
This preserves source duplicates without inventing a deduplication rule. Import
once per database; use a different database URL when a fresh dataset is needed.

## HTTP API

After running the migration and import commands:

```bash
uv run --package app uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000/docs> for the generated API documentation.

| Endpoint | Purpose |
| --- | --- |
| `POST /students/grades` | Insert one grade, returning 201 and its ID |
| `GET /students/grades` | Select all grade records |
| `GET /students?faculty=АВТФ` | Students by faculty |
| `GET /students/courses` | Unique courses |
| `GET /students/low-grades?course=Мат. Анализ` | Students with a course grade below 30 |
| `GET /students/average?faculty=ФПМИ` | Faculty name and average grade |

```bash
curl --get http://127.0.0.1:8000/students/average --data-urlencode 'faculty=ФПМИ'
curl --get http://127.0.0.1:8000/students/low-grades --data-urlencode 'course=Мат. Анализ'
curl -X POST http://127.0.0.1:8000/students/grades \
  -H 'Content-Type: application/json' \
  -d '{"last_name":"Ли","first_name":"Иван","faculty":"АВТФ","course":"Физика","grade":29}'
```

API grades must be JSON integers; strings, booleans, and fractional values are
rejected. Invalid input returns 422. Database errors, including a missing schema,
return 503 without exposing SQL or database paths. Run `init-db` before student
requests. Health probes continue to report application lifecycle; they do not
check database connectivity. The appeals endpoints retain their JSON file storage.

CSV import is a local CLI/repository operation; the HTTP API does not accept server
filesystem paths. In containers, configure a persistent database volume, run the
migration command once before starting replicas, and use the same database URL
for the migration and server processes. The supplied Kubernetes manifests do not
provision database storage.

## Tests and tooling

```bash
just check services/app
just check
HYPOTHESIS_PROFILE=fuzz just test services/app
```

Tests use temporary databases and real Alembic migrations. They verify the full
supplied CSV, all required queries, the 29/30 boundary, duplicate preservation,
import rollback, database constraints, persistence across app instances, CLI
output, API validation, migration/model consistency, and downgrade/upgrade.
Hypothesis and Schemathesis generate additional grade requests and check averages
and persistence. Existing Assignment 4 tests continue to run in the same scope.
Coverage and Allure results remain under `reports/services/app/`.

Runtime version bounds remain in the root `pyproject.toml`; the service declares
SQLAlchemy and Alembic without bounds, and `uv.lock` pins their resolutions.

Implementation references: [SQLAlchemy sessions](https://docs.sqlalchemy.org/en/21/orm/session_basics.html)
and [Alembic programmatic migrations](https://alembic.sqlalchemy.org/en/latest/api/commands.html).
