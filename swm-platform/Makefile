UV ?= uv
COMPOSE_FILE ?= infra/docker-compose.yml
LOADTEST_BASE_URL ?= http://127.0.0.1:8001
LOADTEST_ENDPOINT ?= /webhook/gps
LOADTEST_TRUCKS ?= 600
LOADTEST_EPS ?= 3000
LOADTEST_DURATION ?= 30
LOADTEST_CONCURRENCY ?= 1200
LOADTEST_TIMEOUT ?= 5
LOADTEST_REPORT_DIR ?= scripts/loadtest/reports

.PHONY: help sync lock lint format typecheck test test-api-smoke pre-commit-up pre-commit-run compose-up compose-down compose-logs db-migrate db-migrate-local db-revision loadtest-gps e2e-webhook-local ch-migrate-raw-telemetry replay-dlq backup-drill restore-drill sla-validate resilience-drill

help:
	@echo "Available targets:"
	@echo "  sync            Install workspace and dev dependencies"
	@echo "  lock            Refresh uv lockfile"
	@echo "  lint            Run Ruff lint checks"
	@echo "  format          Auto-format with Ruff"
	@echo "  typecheck       Run mypy strict checks"
	@echo "  test            Run pytest suite"
	@echo "  test-api-smoke  Run admin, webhook, and websocket API regression smoke suite"
	@echo "  pre-commit-up   Install pre-commit hooks"
	@echo "  pre-commit-run  Run hooks across all files"
	@echo "  compose-up      Start local infrastructure and services"
	@echo "  compose-down    Stop local infrastructure and services"
	@echo "  compose-logs    Tail compose logs"
	@echo "  db-migrate      Apply alembic migrations"
	@echo "  db-migrate-local Auto-migrate local docker postgres"
	@echo "  db-revision     Create a new alembic revision (use MSG=...)"
	@echo "  loadtest-gps    Run GPS webhook load test suite and generate report"
	@echo "  e2e-webhook-local Run full local production-like webhook E2E flow"
	@echo "  ch-migrate-raw-telemetry Apply ClickHouse raw_telemetry migration"
	@echo "  replay-dlq      Queue replay job for failed telemetry recovery"
	@echo "  backup-drill    Run local backup drill for Postgres/Redis/ClickHouse"
	@echo "  restore-drill   Run local restore drill from ARTIFACT_DIR (requires FORCE=true)"
	@echo "  sla-validate    Run post-recovery SLA/SLO validation checks"
	@echo "  resilience-drill Run bounded resilience simulation + SLA gate"

sync:
	$(UV) sync --all-packages --all-groups

lock:
	$(UV) lock

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

typecheck:
	$(UV) run mypy apps workers libs tests

test:
	$(UV) run pytest

test-api-smoke:
	$(UV) run pytest tests/test_admin_api.py tests/test_admin_api_endpoint_matrix.py tests/test_websocket_api.py tests/test_webhook_auth.py tests/test_webhook_gps.py

pre-commit-up:
	$(UV) run pre-commit install

pre-commit-run:
	$(UV) run pre-commit run --all-files

compose-up:
	docker compose -f $(COMPOSE_FILE) up -d --build

compose-down:
	docker compose -f $(COMPOSE_FILE) down

compose-logs:
	docker compose -f $(COMPOSE_FILE) logs -f

db-migrate:
	$(UV) run --active --package swm-db alembic -c libs/db/alembic.ini upgrade head

db-migrate-local:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/db_migrate_local.ps1

db-revision:
	$(UV) run --active --package swm-db alembic -c libs/db/alembic.ini revision --autogenerate -m "$(MSG)"

loadtest-gps:
	$(UV) run python scripts/loadtest/gps_ingestion_load_test.py --base-url $(LOADTEST_BASE_URL) --endpoint $(LOADTEST_ENDPOINT) --trucks $(LOADTEST_TRUCKS) --target-eps $(LOADTEST_EPS) --duration-seconds $(LOADTEST_DURATION) --concurrency $(LOADTEST_CONCURRENCY) --timeout-seconds $(LOADTEST_TIMEOUT) --report-dir $(LOADTEST_REPORT_DIR)

e2e-webhook-local:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/loadtest/run_local_webhook_e2e.ps1 -LoadEps $(LOADTEST_EPS) -LoadDurationSeconds $(LOADTEST_DURATION) -LoadConcurrency $(LOADTEST_CONCURRENCY) -LoadTrucks $(LOADTEST_TRUCKS)

ch-migrate-raw-telemetry:
	$(UV) run python scripts/migrate_clickhouse_raw_telemetry.py

replay-dlq:
	$(UV) run python scripts/recovery/replay_telemetry_recovery.py --mode queue --source-stream gps.telemetry.failed --target-stream gps.telemetry.raw --max-messages 5000

backup-drill:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/recovery/drill_backup_local.ps1

restore-drill:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/recovery/drill_restore_local.ps1 -ArtifactDir $(ARTIFACT_DIR) -Force

sla-validate:
	$(UV) run python scripts/recovery/sla_validation_check.py

resilience-drill:
	$(UV) run python scripts/recovery/run_resilience_drill_suite.py --base-url $(LOADTEST_BASE_URL) --endpoint $(LOADTEST_ENDPOINT) --target-eps 120 --duration-seconds 12 --concurrency 80 --report-dir $(LOADTEST_REPORT_DIR)
