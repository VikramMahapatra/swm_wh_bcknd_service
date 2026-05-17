# SWM-FLEET: Fleet Master & Device Registry Platform

Production-grade Python 3.12 monorepo for fleet master data, device registry, telemetry ingestion, realtime fanout, storage, analytics, and alerting.

## Tech Stack
- FastAPI (async-first APIs)
- Redis (pub/sub, low-latency state)
- PostgreSQL (transactional state)
- ClickHouse (historical analytics)
- Prometheus + Grafana (observability)
- Alembic (database migrations)
- Ruff + mypy + pytest (quality gates)
- pre-commit hooks (local enforcement)
- uv (workspace package manager)

## Expected Scale
- 600 active devices
- 600+ events/sec sustained ingestion
- Realtime websocket updates
- Historical analytics pipelines

## Monorepo Tree

swm-platform/
├ apps/
│  ├ ingestion-api/
│  ├ websocket-api/
│  └ admin-api/
├ workers/
│  ├ realtime-worker/
│  ├ storage-worker/
│  ├ analytics-worker/
│  └ alert-worker/
├ libs/
│  ├ schemas/
│  ├ db/
│  ├ redis/
│  ├ auth/
│  └ common/
├ infra/
│  ├ docker-compose.yml
│  ├ prometheus/
│  └ grafana/
├ tests/
├ scripts/
└ docs/

## Quickstart

1. Install uv.
2. From the repository root, run:
   - `uv sync --all-packages --all-groups`
   - `uv run pre-commit install`
3. Copy `.env.example` to `.env` and adjust values.
4. Start local stack:
   - `docker compose -f infra/docker-compose.yml up -d --build`

## Common Commands
- `make sync` install all workspace dependencies
- `make lint` run Ruff
- `make format` format source
- `make typecheck` run mypy strict checks
- `make test` run pytest
- `make compose-up` start local stack
- `make compose-down` stop local stack

## API Endpoints
- Ingestion API: `POST /v1/events`, `GET /healthz`, `GET /metrics`
- WebSocket API: `WS /ws/realtime`, `GET /healthz`, `GET /metrics`
- Admin API: `GET /v1/platform/status`, `GET /healthz`, `GET /metrics`
- Master data API: `/vendors`, `/devices`, `/vehicles`, `/geofences`, `/device-assignments`

## Migration Workflow
- Create migration: `make db-revision MSG="add new table"`
- Apply migrations: `make db-migrate`

## Notes
- Each app, worker, and library is an independently importable package with its own `pyproject.toml`.
- Shared contracts and cross-cutting concerns live in `libs/*`.
- Production hardening (auth policy, retries, circuit breakers, DLQs, backpressure) should be layered into workers as the domain matures.
