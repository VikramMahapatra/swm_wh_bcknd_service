# Operational Recovery Runbook

## Scope
This runbook provides executable workflows for:
- DLQ and retry replay recovery
- Backup drills for PostgreSQL, Redis, and ClickHouse
- Restore drills with controlled destructive guardrails
- Post-recovery SLA/SLO validation

## Preconditions
- Local or target environment is reachable via Docker Compose services.
- Platform services are running.
- You have operator access to execute scripts.

## 1. Create Recovery Backups
Use this before any destructive remediation or DR test.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/recovery/drill_backup_local.ps1
```

Optional table selection for ClickHouse:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/recovery/drill_backup_local.ps1 -ClickhouseTables raw_telemetry,analytics_daily_kpis
```

Outcome:
- Timestamped backup directory under scripts/recovery/artifacts
- Manifest file with artifact paths

## 2. Queue Replay of Failed Telemetry (Non-Blocking)
Queue a recovery job to replay failed telemetry from DLQ to raw stream.

```bash
uv run python scripts/recovery/replay_telemetry_recovery.py --mode queue --source-stream gps.telemetry.failed --target-stream gps.telemetry.raw --max-messages 5000
```

Track job status:

```bash
uv run python scripts/recovery/replay_telemetry_recovery.py --mode status --job-id <job-id>
```

## 3. Immediate Replay (Synchronous)
Use for urgent operations where replay-worker is not active.

```bash
uv run python scripts/recovery/replay_telemetry_recovery.py --mode process --source-stream gps.telemetry.failed --target-stream gps.telemetry.raw --max-messages 5000
```

## 4. Restore Drill (Destructive)
Restore from a selected backup artifact directory.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/recovery/drill_restore_local.ps1 -ArtifactDir scripts/recovery/artifacts/<timestamp> -Force
```

Safety notes:
- Restore script requires -Force.
- Restore will overwrite existing Redis and ClickHouse table data for restored objects.

## 5. Post-Recovery SLA Validation
Run health and stream-threshold validation.

```bash
uv run python scripts/recovery/sla_validation_check.py
```

Failure indicates readiness risk and should block closure of the incident or drill.

## 6. Bounded Resilience Drill Suite
Run a short burst/failure simulation and enforce readiness thresholds.

```bash
uv run python scripts/recovery/run_resilience_drill_suite.py
```

This script:
- executes the existing GPS loadtest suite with bounded parameters
- validates scenario metrics against guardrail thresholds
- runs SLA validation checks
- exits non-zero on readiness failure

## 7. CI Readiness Gate
Automated gate workflow:

- `.github/workflows/resilience-drill.yml`

The workflow:
- starts local compose stack in CI
- runs bounded resilience drill suite
- uploads generated reports as artifacts
- tears down stack in all cases

## Incident Playbook Template
1. Stabilize ingress: reduce burst or block noisy source.
2. Snapshot state: run backup drill script.
3. Classify failures: inspect retry and DLQ stream volume.
4. Execute replay: queue or process replay jobs.
5. Restore only if replay is insufficient.
6. Validate SLA/SLO using validation script.
7. Publish post-incident summary with timeline and action items.

## Suggested Evidence for DR Validation
- Backup artifact path and manifest.json
- Replay job progress payload
- SLA validation output
- Resilience drill suite output and report artifact
- Service health snapshots
- Duration from incident start to recovery complete
