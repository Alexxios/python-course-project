# Subscriber appeals API

The `app` service implements all three parts of homework 4:

| Task | Implementation |
| --- | --- |
| Collect subscriber details | `POST /appeals` validates the subscriber's name, birth date, phone, and email with Pydantic, then saves a JSON file. |
| Include the problem | Each appeal includes a reason and the date and time the problem was detected. |
| Support several reasons | `reasons` is a nonempty list, so one request can include any combination of the three supported reasons. |

The final API includes the extra tasks, so reasons and detection time are required
along with the subscriber details. It runs entirely with local files; PostgreSQL,
Redis, and the infrastructure stack are not needed for this assignment.

## Run locally

From the repository root:

```bash
uv sync --package app --group dev
uv run --package app uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000/docs> to submit appeals interactively. The schema is
available at <http://127.0.0.1:8000/openapi.json>.

## Submit an appeal

```bash
curl --fail-with-body -i http://127.0.0.1:8000/appeals \
  -H 'Content-Type: application/json' \
  --data '{
    "last_name": "Иванов",
    "first_name": "Семён",
    "birth_date": "1990-05-21",
    "phone": "+79991234567",
    "email": "ivanov@example.com",
    "reasons": ["нет доступа к сети", "не приходят письма"],
    "detected_at": "2025-01-15T10:30:00+03:00"
  }'
```

The response is **201 Created** only after the JSON file has been written. The
body contains the validated fields and a generated UUID, for example:

```json
{
  "last_name": "Иванов",
  "first_name": "Семён",
  "birth_date": "1990-05-21",
  "phone": "+79991234567",
  "email": "ivanov@example.com",
  "reasons": ["нет доступа к сети", "не приходят письма"],
  "detected_at": "2025-01-15T10:30:00+03:00",
  "id": "7c3d5a6e-2b81-4c6f-9e10-123456789abc"
}
```

The file `data/appeals/<id>.json` contains the same JSON object. Each submission
gets a separate UUID and file, including repeated submissions of the same payload.
The endpoint collects appeals; there are no list, read, update, or delete routes.

## Validation rules

All seven input fields are required and reject `null`. Unknown fields are rejected,
including a client-supplied `id`.

| Field | Accepted values |
| --- | --- |
| `last_name`, `first_name` | Nonempty strings containing only Cyrillic letters, with an uppercase first letter. `Ё` and other Cyrillic alphabets are supported. Remaining letters may use either case. Digits, Latin letters, spaces, punctuation, and hyphens are rejected. |
| `birth_date` | A real calendar date written as `YYYY-MM-DD`, no later than the current UTC date. Numeric timestamps and datetime strings are rejected. |
| `phone` | A string starting with `+`, followed by 8 to 15 ASCII digits; the first digit must be nonzero. Spaces, parentheses, and separators are rejected. This checks the format, not whether the number exists. |
| `email` | An address validated by Pydantic's `EmailStr`. The normalized address is returned and saved; for example, the domain is lowercased. Validation does not check mailbox existence or send email. |
| `reasons` | A nonempty JSON array containing one or more of the values below. Each list item is validated. |
| `detected_at` | A valid ISO 8601 datetime with `T` between date and time and an explicit offset, such as `2025-01-15T10:30:00+03:00` or `2025-01-15T07:30:00Z`. It cannot be in the future. Date-only values and numeric timestamps are rejected. |

Supported reasons are exactly:

- `нет доступа к сети`
- `не работает телефон`
- `не приходят письма`

Invalid requests return **422 Unprocessable Entity** with FastAPI's `detail`
array identifying each invalid field through `loc`, `msg`, and `type`. Rejected
input and validator context are omitted, so values such as non-finite numbers
and unpaired Unicode surrogates cannot crash error serialization. Invalid
requests do not create a file. For example,
`"first_name": "семён"`, `"birth_date": "2025-02-29"`, an unknown reason, or
`"reasons": []` is invalid.

Undecodable request bodies, such as invalid byte encodings, return **400 Bad
Request** before model validation. They also leave storage unchanged.

The explicit phone and date formats above are implementation choices for the
assignment. Pydantic handles validation in `src/app/models.py`; the route does
not manually parse unvalidated request dictionaries. See the
[Pydantic email type](https://docs.pydantic.dev/latest/api/networks/#pydantic.networks.EmailStr)
and [date/time types](https://docs.pydantic.dev/latest/api/standard_library_types/#date-and-time-types)
for the underlying validators.

## Storage configuration

`APPEALS_DATA_DIR` chooses the destination directory. The default is `data/appeals`
relative to the server's working directory. It is created on the first valid
submission. Set the environment variable explicitly when using a custom directory:

```bash
APPEALS_DATA_DIR=/tmp/course-appeals \
  uv run --package app uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The application reads this setting when `create_app()` is called. Tests can pass
`create_app(data_dir=...)` to override it without changing process environment.

Files use UTF-8 with readable Cyrillic text. A request writes and flushes a temporary
file in the destination directory, then atomically renames it to `<id>.json`.
Concurrent submissions use separate filenames. Handled write failures remove the
temporary file and return **503 Service Unavailable** without reporting success.
Already accepted files remain intact. A process terminated during writing may leave
a `.tmp` file; only `.json` files represent completed submissions.

The destination must be writable by the service. For containers, mount persistent
storage and set `APPEALS_DATA_DIR` to the mount path; the supplied Kubernetes
Deployment does not configure a persistent volume. Files stored only in a
container's writable layer do not survive container replacement.

Local assignment materials (`assignments/`) and the default saved appeals
(`**/data/appeals/`) are excluded from Git and Docker build contexts. If you choose
a custom storage path inside the repository, add that path to both ignore files.

## Tests

From the repository root:

```bash
just check services/app
just check
```

The service suite covers valid submissions with all combinations of reasons,
Cyrillic names, phone boundaries, email normalization, invalid/missing fields,
calendar dates and time zones, JSON round trips, persistence across restarts,
concurrent writes, storage failures and retries, configuration, OpenAPI, and health
checks. Tests use temporary directories and FastAPI's in-process client; no
external services or running HTTP server are needed.

`just check` additionally checks the generated README, documentation, shared
tooling, and integration scope. Coverage and test reports are written under
`reports/services/app/`.

### Fuzzing

`tests/test_fuzz.py` uses the existing Hypothesis and Schemathesis dependencies.
It runs automatically in `just test services/app`, `just check`, and member CI.
The default `app` profile generates up to 50 examples per property; the `fuzz`
profile increases that budget to 1,000. Each example creates a fresh application
and temporary storage directory, which are cleaned up afterward.

The suite checks generated valid appeals, mutated fields, non-Cyrillic characters,
arbitrary JSON shapes, malformed request bytes, and positive/negative requests
generated from OpenAPI. It asserts that accepted appeals match the saved JSON
and rejected requests leave no files. Schemathesis also checks response status,
content type, and response schema. Custom Cyrillic and past-date rules are not
fully expressible in OpenAPI, so schema-generated inputs may return 422; separate
domain-valid strategies require 201 and verify the returned values.
Negative schema generation can also produce raw bytes, for which 400 is a valid
decoding error response.

Run the full service suite with the larger generation budget from the repository
root:

```bash
HYPOTHESIS_PROFILE=fuzz just test services/app
```

To run only fuzzing and print generation statistics, enter the service directory:

```bash
cd services/app
uv run --package app --group dev python -m pytest -m fuzz --hypothesis-show-statistics
```

For a longer reproducible run from that directory:

```bash
uv run --package app --group dev python -m pytest -m fuzz \
  --hypothesis-profile=fuzz --hypothesis-seed=20261109 --hypothesis-show-statistics
```

Use the same seed and dependency versions to repeat a run. Hypothesis shrinks
failures, caches examples locally in the ignored `.hypothesis/` directory, and
prints reproduction information for generated failures. Keep minimized failures
as regression tests; `tests/test_errors.py` covers the unsafe Unicode and
non-finite-number error responses found while adding this suite.

See [Hypothesis settings](https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html)
and [Schemathesis strategies](https://schemathesis.readthedocs.io/en/stable/guides/hypothesis-strategies/)
for extending the profiles and generators.
