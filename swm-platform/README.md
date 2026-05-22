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
- `make test-api-smoke` run admin, webhook, and websocket API regression smoke suite
- `make compose-up` start local stack
- `make compose-down` stop local stack

## API Endpoints
- Ingestion API: `POST /v1/events`, `GET /healthz`, `GET /metrics`
- WebSocket API: `WS /ws/realtime`, `GET /healthz`, `GET /metrics`
- Admin API: `GET /v1/platform/status`, `GET /healthz`, `GET /metrics`
- Master data API: `/vendors`, `/devices`, `/vehicles`, `/geofences`, `/device-assignments`

## Remote Smoke Test

Use the remote probe script to verify the EC2 hostnames shared by the DevOps team:

```bash
uv run python scripts/loadtest/check_remote_services.py \
   --ingestion-url https://ingestion-swm.zentrixel.com \
   --websocket-url wss://websocket-swm.zentrixel.com \
   --grafana-url https://grafana-swm.zentrixel.com
```

The script checks `GET /healthz` on ingestion, `GET /api/health` on Grafana, and a websocket handshake on `/ws/realtime`.

## Analytics (Epic-5)

Analytics processing is now persisted in PostgreSQL from `analytics-worker` and exposed through `admin-api` reporting endpoints.

### Analytics tables
- `analytics_vehicle_state`: per-vehicle stream state for trip/idle/geofence continuity.
- `analytics_trip_records`: trip start/end records with runtime, moving/idle, stoppages, and distance.
- `analytics_idle_records`: idle segments with duration and anchor point.
- `analytics_overspeed_events`: overspeed detections with threshold and severity.
- `analytics_geofence_events`: geofence entry/exit and route deviation events.
- `analytics_daily_kpis`: daily rollup used for period reports.

### Analytics APIs (Admin API)
- Event feeds:
   - `/analytics/trips`
   - `/analytics/idle-segments`
   - `/analytics/overspeed-events`
   - `/analytics/geofence-events`
- Period reports (JSON or CSV with `export=json|csv`):
   - `/analytics/reports/daily`
   - `/analytics/reports/monthly`
   - `/analytics/reports/quarterly`
   - `/analytics/reports/half-yearly`
   - `/analytics/reports/annual`

### Analytics worker logic
- Trip detection start/end based on ignition, speed, idle window, and odometer/distance increments.
- Idle detection using stationary speed threshold + minimum idle duration.
- Overspeed event detection with configurable threshold and severity.
- Geofence entry/exit and dwell tracking (circle + polygon support).
- Route deviation events with cooldown to avoid event flooding.
- Daily KPI upsert aggregation used by period-level report APIs.

## Migration Workflow
- Create migration: `make db-revision MSG="add new table"`
- Apply migrations: `make db-migrate`

## Next Steps (Runbook)

1. Apply DB migration for analytics tables:
   - `make db-migrate`

2. Start or restart the platform services:
   - `docker compose -f infra/docker-compose.yml up -d --build`

3. Start analytics worker (if running outside compose):
   - `uv run --package analytics-worker python -m analytics_worker.main`

4. Verify analytics data is being produced:
   - `uv run --package admin-api python -c "import requests; print(requests.get('http://localhost:8003/analytics/trips', headers={'X-Role':'admin'}).status_code)"`

5. Validate report endpoints (Swagger or curl):
   - `curl "http://localhost:8003/analytics/reports/daily?date_from=2026-05-01&date_to=2026-05-17" -H "X-Role: admin"`
   - `curl "http://localhost:8003/analytics/reports/monthly?export=csv" -H "X-Role: admin" -o analytics-monthly.csv`

## Notes
- Each app, worker, and library is an independently importable package with its own `pyproject.toml`.
- Shared contracts and cross-cutting concerns live in `libs/*`.
- Production hardening (auth policy, retries, circuit breakers, DLQs, backpressure) should be layered into workers as the domain matures.

## Reliability Operations Starter (Epic)

This repository now includes a first implementation slice for platform reliability operations:

- `alert-worker` emits alerts for `offline`, `stale_gps`, `overspeed`, `geofence_breach`, and `panic` events.
- Worker stream runtime emits Prometheus metrics for throughput, pending backlog, stream lag, retry/poison routing, stream length, and heartbeat timestamps.
- Prometheus loads alert rules from `infra/prometheus/alerts.yml`.
- Grafana dashboard `Platform Reliability Operations` is provisioned from `infra/grafana/dashboards/platform-reliability-operations.json`.

### Quick Validate

1. Restart stack:
   - `docker compose -f infra/docker-compose.yml up -d --build`
2. Verify Prometheus rule groups:
   - `http://localhost:9090/rules`
3. Open Grafana and check dashboard:
   - `http://localhost:3000` (admin/admin)
4. Generate traffic and confirm metrics:
   - `swm_stream_consumer_pending`
   - `swm_stream_consumer_lag_seconds`
   - `swm_stream_consumer_retry_total`
   - `swm_alert_worker_alert_event_total`

   ## Security and Resilience Epic

   Phase-wise rollout guidance and toggles are documented in:

   - `docs/security-resilience-epic-phases.md`

   Operational recovery execution runbook is documented in:

   - `docs/operational-recovery-runbook.md`
   - `docs/api-endpoints-reference.md`

   Recovery command shortcuts:

   - `make replay-dlq`
   - `make backup-drill`
   - `make restore-drill ARTIFACT_DIR=scripts/recovery/artifacts/<timestamp>`
   - `make sla-validate`
   - `make resilience-drill`
