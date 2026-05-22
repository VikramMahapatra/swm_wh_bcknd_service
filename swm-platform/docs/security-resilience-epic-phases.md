# Security and Resilience Epic - Phase Plan

## Objective
Implement production-safe security controls, resiliency safeguards, scale protections, and operational recovery workflows for the fleet telemetry platform without disruptive cutovers.

## Delivery Strategy
- Ship controls behind environment flags.
- Start in observe-only mode where possible.
- Enable incrementally per service and endpoint.
- Validate with focused test gates and rollback switches.

## Phase 0 - Baseline and Hardening Readiness
### Goals
- Establish safe toggles and secure configuration surface.
- Remove risky sample credentials from checked-in templates.

### Delivered in this phase
- Added auth and security feature flags in shared settings.
- Added ingestion webhook auth and rate-limit configuration knobs.
- Added websocket auth toggle.
- Sanitized `.env.example` infrastructure credentials and secrets.

### Rollback
- Set `AUTH_ENFORCE_JWT=false`.
- Set `INGESTION_WEBHOOK_AUTH_ENABLED=false`.
- Set `INGESTION_RATE_LIMIT_ENABLED=false`.
- Set `WEBSOCKET_AUTH_REQUIRED=false`.

## Phase 1 - Authentication, RBAC, and Scoped Access
### Goals
- Introduce JWT/API-key auth for backend APIs.
- Preserve backward compatibility with legacy role headers during migration.
- Support role normalization for enterprise roles.

### Delivered in this phase
- `admin-api` now supports auth context from:
  - `Authorization: Bearer <jwt>`
  - `X-API-Key`
  - Legacy `X-Role` fallback (controlled by `AUTH_ALLOW_LEGACY_ROLE_HEADER`)
- Added canonical role mapping:
  - admin, fleet_manager, supervisor, operator, analyst, read_only
  - legacy aliases (`ops`, `viewer`, `readonly`) still work
- JWT and API-key failures return 401, role mismatch returns 403.

### Migration sequence
1. Populate `AUTH_API_KEYS_JSON` for service integrations.
2. Start passing JWT in Admin API clients.
3. Set `AUTH_LEGACY_DEFAULT_ROLE=read_only`.
4. Disable header fallback: `AUTH_ALLOW_LEGACY_ROLE_HEADER=false`.
5. Enforce JWT globally: `AUTH_ENFORCE_JWT=true`.

## Phase 2 - Ingestion Edge Security
### Goals
- Protect webhook entrypoint with layered controls.
- Add anti-abuse limits with granular scopes.

### Delivered in this phase
- Optional `WebhookAuthMiddleware` in `ingestion-api` with:
  - secret header validation
  - HMAC signature validation
  - source IP allow-list
  - nonce replay prevention via Redis
- Optional Redis sliding-window rate-limiter middleware with global, vendor, IP, and IMEI scopes.

### Migration sequence
1. Turn on `INGESTION_RATE_LIMIT_ENABLED=true` with permissive limits.
2. Tune limits using Prometheus metrics and blocked-request logs.
3. Enable webhook auth with secret only.
4. Add HMAC and nonce checks.
5. Add strict IP allow-list.

## Phase 3 - WebSocket Access Protection
### Goals
- Prevent unauthenticated realtime stream access.

### Delivered in this phase
- Optional JWT validation for `/ws/realtime` when `WEBSOCKET_AUTH_REQUIRED=true`.
- Token can be supplied via query param (`token`) or Bearer header.
- Invalid or missing token closes connection with policy violation.

### Migration sequence
1. Roll clients with token support.
2. Turn on `WEBSOCKET_AUTH_REQUIRED=true` in staging.
3. Validate reconnect behavior and token refresh.
4. Enable in production.

## Phase 4 - Recovery and Operational Resilience
### Delivered controls
- Replay tooling for failed telemetry and dead-letter remediation:
  - `scripts/recovery/replay_telemetry_recovery.py`
- Backup/restore drill scripts for PostgreSQL, Redis, and ClickHouse:
  - `scripts/recovery/drill_backup_local.ps1`
  - `scripts/recovery/drill_restore_local.ps1`
- Runbook-backed incident workflows and evidence checklist:
  - `docs/operational-recovery-runbook.md`
- SLA/SLO validation script for post-recovery acceptance:
  - `scripts/recovery/sla_validation_check.py`

### Pending expansion
- Additional production-scale stress profiles and chaos drills for non-local environments.

### CI gate delivery
- Added bounded resilience drill gate workflow:
  - `.github/workflows/resilience-drill.yml`
- Gate executes:
  - load/burst/failure simulation (`scripts/recovery/run_resilience_drill_suite.py`)
  - post-recovery SLA validation (`scripts/recovery/sla_validation_check.py`)
  - artifact retention for drill reports

## Acceptance Gates per Phase
- Unit/integration tests pass for impacted modules.
- No regression in healthz and metrics endpoints.
- Explicit rollback switch validated in staging.
- Deployment checklist and runbook updates completed.
