# Infrastructure

## Local stack

Start PostgreSQL, Redis, Prometheus, and Grafana from the workspace root.
`just bootstrap` creates `.env` from `.env.example` if it is missing:

```bash
just bootstrap
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
```

| Service | Local address | Purpose / defaults |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:5432` | Application database. Database, user, and password default to `app`. |
| Redis | `127.0.0.1:6379` | Cache, task broker, or other application state. No password in the local starter. |
| Prometheus | <http://localhost:9090> | Metrics storage; check scrape targets at `/targets`. |
| Grafana | <http://localhost:3000> | Dashboards; sign in with `admin` / `admin` and change the password on first login. |

All published ports bind to localhost. These credentials are local development
defaults. Edit `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_PORT`, and `REDIS_PORT` in `.env` to customize database settings or
avoid host port conflicts. The `--env-file .env` option explicitly loads the
workspace settings even though the Compose files live under `infra/`.

Named volumes preserve PostgreSQL data, Redis data, metrics, dashboards, and
Grafana's password across restarts. Redis enables append-only persistence.
The PostgreSQL volume mounts at `/var/lib/postgresql`, as required by the
[PostgreSQL 18+ image layout](https://hub.docker.com/_/postgres).
PostgreSQL's database/user/password settings initialize an empty volume; changing
them later requires updating the existing database as well.

Stop the infrastructure-only stack with:

```bash
docker compose --env-file .env -f infra/docker-compose.yml down
```

Adding `--volumes` also deletes all stored database, Redis, metrics, and Grafana data.

## Application stack

`docker-compose.dev.yml` adds the learning platform API and migration service to
the infrastructure stack. From the workspace root after `just bootstrap`, run:

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up --build -d api
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.dev.yml ps -a
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.dev.yml exec api \
  uv run --no-sync python -m app create-admin --username admin --first-name Admin --last-name User
```

The API and migration service build `services/app/Dockerfile` with the workspace
root as the build context. Both connect to the shared `postgres:5432` service,
whose data uses the existing `postgres-data` volume. Migrations wait for PostgreSQL
to become healthy; the API starts only after migrations finish successfully. The API listens on
`127.0.0.1:8000`; set `APP_PORT` in `.env` to change that port.

The final `api` limits startup to the application and its database dependencies.
Omit it to include Redis, Prometheus, and Grafana in the same stack. Add future
application services to `docker-compose.dev.yml` as well.

Inspect logs and stop the combined stack with:

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.dev.yml logs api migrate
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.dev.yml down
```

Stopping the stack retains its named volumes. The previous root `compose.yml`
used a separate `learning-platform` project and `learning-postgres-data` volume.
Existing data in that volume is not imported automatically into this stack's
`postgres-data` volume. If you used that stack, stop its containers before starting
this API to free the application port; retain its volume and export/restore the
database if you need those records.

## Database connections

With the default `.env`, applications running on the host can use
`postgresql://app:app@127.0.0.1:5432/app` and `redis://127.0.0.1:6379/0`.
Applications in the same Compose stack use `postgres:5432` and `redis:6379`;
host port overrides do not change these container ports. Adjust the credentials
and database in connection URLs when changing `.env`.

Manage the application's chosen database driver versions in the root manifest
and declare their unversioned names in its member dependencies,
and configure connections and migrations in the application. PostgreSQL and Redis
have health checks, so application services can wait for `service_healthy`, as the
migration service does in `docker-compose.dev.yml`.

For automated tests, Testcontainers fixtures create their own disposable databases
and return their connection details. Those tests can run independently of this
persistent development stack.

## Local monitoring

Prometheus scrapes itself every 15 seconds. In Grafana's Explore view, select
Prometheus and query `up` to verify the connection. Grafana's Prometheus data
source is provisioned automatically.

Edit `prometheus/prometheus.yml` to add scrape targets and
`grafana/provisioning/datasources/prometheus.yml` to change the data source.
Restart the corresponding service after editing its configuration:

```bash
docker compose --env-file .env -f infra/docker-compose.yml restart prometheus
docker compose --env-file .env -f infra/docker-compose.yml restart grafana
```

## Application metrics

Start the application together with the monitoring services:

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up --build -d
```

Once the API exposes a Prometheus-format `/metrics` endpoint, append this job
to `scrape_configs` in `prometheus/prometheus.yml`:

```yaml
  - job_name: api
    metrics_path: /metrics
    static_configs:
      - targets: ["api:80"]
```

Use the Compose service name and its container port. Installing Python packages
alone does not expose an endpoint; configure it in the application. Restart
Prometheus after adding the job, then check `/targets`. Add one job per service.

The image versions are pinned in `docker-compose.yml` and updated by Dependabot.
See the [Prometheus configuration reference](https://prometheus.io/docs/prometheus/latest/configuration/)
and [Grafana provisioning guide](https://grafana.com/docs/grafana/latest/administration/provisioning/)
for additional settings.

## Kubernetes

`just new-service <name>` creates `services/<name>/k8s/` with a Deployment,
ClusterIP Service, and Kustomize configuration. The defaults route Service port
80 to container port 80, use HTTP startup/readiness/liveness probes, and set CPU
and memory requests and limits. Each service README includes image build/push,
manifest preview, apply, rollout, and port-forward commands.

Startup and liveness request `/health/live`; readiness requests `/health/ready`.
The readiness endpoint returns 503 when application initialization is incomplete
or the instance has been marked unavailable. Add essential dependency checks to
readiness as needed; keep liveness independent of database availability.

Configure the service's image, environment, and resource needs before deploying.
For workers, replace the Uvicorn command in the Dockerfile, remove the Service
from the Kustomize resources, and remove or replace the HTTP port and probes.
The Compose databases and monitoring stack above remain local infrastructure;
configure cluster dependencies separately.

`infra/k8s/` is available for shared manifests and environment overlays referencing
the service configurations. `nginx/` is reserved for proxy configuration.
