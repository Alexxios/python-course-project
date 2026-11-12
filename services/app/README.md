# app

[![lint](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/services/app/badges/lint.json)](https://alexxios.github.io/python-course-project/reports/services/app/)
[![tests](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/services/app/badges/tests.json)](https://alexxios.github.io/python-course-project/reports/services/app/)
[![coverage](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/services/app/badges/coverage.json)](https://alexxios.github.io/python-course-project/reports/services/app/)

Student grades and subscriber appeals service for the Python course project.
Assignment 6 adds SQLAlchemy storage, Alembic migrations, CSV import, and all
required queries, including grades below 30. See the
[Student grades guide](../../docs/students.md) for CLI and API examples.

```bash
uv run --package app python -m app.students init-db
uv run --package app python -m app.students import-csv services/app/examples/students.csv
uv run --package app python -m app.students average --faculty ФПМИ
```

Run these commands from the workspace root. Import appends all rows; import once
per database. `STUDENTS_DATABASE_URL` defaults to `sqlite:///students.sqlite3`.
Apply migrations before student API requests; the server does not create tables.
Migrations are packaged with the service for installed and container use.

All three homework 4
tasks are implemented by `POST /appeals`: Pydantic validation of subscriber
details, multiple problem reasons and detection time, and JSON file persistence.
See the [API guide](../../docs/appeals.md) for request examples, validation rules,
storage configuration, and test coverage.

Run `just check services/app` from the workspace root.
This includes Hypothesis and Schemathesis fuzz tests. Use
`HYPOTHESIS_PROFILE=fuzz just test services/app` for a larger generation budget;
see [fuzzing commands and reproduction](../../docs/appeals.md#fuzzing).
Manage runtime versions with `uv add <dependency>` from the repository root.
List dependency names and required extras without version bounds in this
service's `pyproject.toml`; the root manifest and shared lockfile control versions.

## Structure

```text
src/app/
├── __init__.py
├── main.py              # Application factory, lifespan, and ASGI app
├── errors.py            # JSON-safe validation error responses
├── models.py            # Pydantic request/response models and reason enum
├── storage.py           # Atomic JSON file persistence
├── students/            # SQLAlchemy model, queries, CSV import, CLI, migrations
├── py.typed
└── routers/
    ├── __init__.py
    ├── appeals.py       # POST /appeals
    ├── students.py      # Assignment 6 INSERT/SELECT and aggregate queries
    └── health.py        # Liveness and readiness routes
```

`src/` separates installable Python code from tests and project tooling.
`app` is the import package, so imports use
`app.routers`, without `src` in the module path.
The package name also keeps services' modules distinct in workspace integration
tests. See the [Python layout comparison](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).

`main.py` assembles the application with `create_app()` and registers routers.
Add route groups under `routers/` and include them in the factory. Initialize
required resources in `lifespan()` before setting `app.state.ready = True`;
close them during cleanup. Each application instance has its own readiness state.

## Server

`src/app/main.py` exposes the FastAPI `app`.
The Dockerfile starts it with:

```bash
uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 80
```

FastAPI, Pydantic with email validation, and Uvicorn have their version requirements
in the root `pyproject.toml` and unversioned declarations in this service. The image
installs them from the workspace lockfile at build time; `--no-sync` reuses that environment
at startup. For local development, run from the workspace root:

```bash
uv run --package app uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

`APPEALS_DATA_DIR` defaults to `data/appeals` relative to the server's working
directory. Each accepted appeal is stored as `<uuid>.json`; the same object is
returned with status 201. Invalid input returns 422; a storage failure returns
503. Set `APPEALS_DATA_DIR` to a writable persistent volume for container
deployments. The supplied Kubernetes manifest does not provision one.

## Health checks

| Endpoint | Successful response | Purpose |
| --- | --- | --- |
| `GET /health/live` | `200 {"status":"ok"}` | The application can respond. Keep it independent of external services. |
| `GET /health/ready` | `200 {"status":"ready"}` | This instance has finished initialization and can accept traffic. Returns 503 when `app.state.ready` is false. |

Readiness starts false, becomes true during startup, and resets during lifespan
cleanup. The default checks application lifecycle only. Add bounded checks for
required dependencies in `routers/health.py`; return 503 if an essential dependency
is unavailable. A database outage should not make the liveness endpoint fail.

## Kubernetes

`k8s/` contains a Deployment, a ClusterIP Service, and a Kustomize configuration.
The Kubernetes resource name is `app`; the Python
package and workspace directory remain `app`.

Uvicorn listens on `0.0.0.0:80` in the container. The Service routes port 80 to
the container's named `http` port. Startup and liveness probes request
`/health/live`; readiness requests `/health/ready`. A failed readiness probe
stops Service traffic, while repeated startup or liveness failures restart the
container. For a worker without HTTP endpoints, remove the
Service from `kustomization.yaml`, remove or replace the ports and HTTP probes,
and replace the Uvicorn command in the Dockerfile with the worker command.

The Deployment starts one replica, requesting 100m CPU and 128Mi memory with
limits of 500m CPU and 256Mi memory. Adjust resources, replica count, ports, and
probes for the application. Configure application environment variables and
Secret references in `deployment.yaml`; the local Compose stack and `.env` are
not provisioned in Kubernetes.

Set `images[].newName` and `newTag` in `k8s/kustomization.yaml` to your image
repository and an immutable release tag. Replace the example registry and tag
in these commands to match. Build from the workspace root so local libraries
and the shared lockfile are available:

```bash
uv lock
docker build -f services/app/Dockerfile -t registry.example.com/your-team/app:dev .
docker push registry.example.com/your-team/app:dev
kubectl kustomize services/app/k8s
kubectl apply -n default -k services/app/k8s
kubectl rollout status -n default deployment/app
kubectl port-forward -n default service/app 8080:80
```

Use your intended kubectl context and replace `default` with an existing target
namespace. For private registries, configure `imagePullSecrets` in the Deployment.
The Service is cluster-internal; port forwarding exposes it at
<http://localhost:8080> for local testing. Shared environment overlays can live
under `infra/k8s/`. See the
[Kustomize guide](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
for image overrides and overlays, and the
[probe guide](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
for application health checks.
