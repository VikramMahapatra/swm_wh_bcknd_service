# Local Production-Like Webhook E2E Test Guide

This guide helps you run the backend locally, push GPS traffic to the webhook, and verify data flow end-to-end exactly like a production-style environment.

## 1. Prerequisites

- Docker Desktop running
- `uv` installed
- Repository root opened at `swm-platform`

## 1.1 One-Command E2E (recommended)

If you want everything automated (bootstrap, start stack, smoke push, optional load run, stream checks, admin checks), run:

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
make e2e-webhook-local
Pop-Location
```

Equivalent direct script call:

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
.\scripts\loadtest\run_local_webhook_e2e.ps1
Pop-Location
```

Useful variants:

```powershell
# Fast smoke path (skip heavy load)
.\scripts\loadtest\run_local_webhook_e2e.ps1 -SkipLoad

# Custom load shape
.\scripts\loadtest\run_local_webhook_e2e.ps1 -LoadEps 3500 -LoadDurationSeconds 45 -LoadConcurrency 1600 -LoadTrucks 600

# Same custom load shape via Makefile
make e2e-webhook-local LOADTEST_EPS=3500 LOADTEST_DURATION=45 LOADTEST_CONCURRENCY=1600 LOADTEST_TRUCKS=600

# Skip bootstrap if already done, and do not tail logs at the end
.\scripts\loadtest\run_local_webhook_e2e.ps1 -SkipBootstrap -NoFollowLogs
```

## 2. Bootstrap Dependencies (once)

PowerShell:

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
.\scripts\dev.ps1
Pop-Location
```

## 3. Start Full Stack (production-like)

This starts APIs, workers, Redis, Postgres, ClickHouse, Prometheus, Grafana, and Nginx:

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
docker compose -f infra/docker-compose.yml up -d --build
Pop-Location
```

## 4. Health Checks

Run these and ensure all return healthy responses:

```powershell
Invoke-RestMethod http://localhost:8001/healthz
Invoke-RestMethod http://localhost:8003/healthz
Invoke-RestMethod http://localhost/healthz
```

Expected:
- ingestion-api: `status=ok`
- admin-api: `status=ok`
- nginx health endpoint reachable

## 5. Send Sample GPS Payload to Webhook

Production-like path through Nginx (port 80):

```powershell
$body = @(
  @{
    imei = "990000000000001"
    latitude = 28.6139
    longitude = 77.2090
    speed = 25.5
    heading = 90
    ignition = $true
    odometer = 12345.6
    fuel_level = 61.2
    timestamp = "2026-05-04T10:00:00Z"
  },
  @{
    imei = "990000000000002"
    latitude = 28.6141
    longitude = 77.2092
    speed = 32.7
    heading = 120
    ignition = $true
    odometer = 22345.6
    fuel_level = 54.1
    timestamp = "2026-05-04T10:00:01Z"
  }
)

Invoke-RestMethod `
  -Method POST `
  -Uri http://localhost/ingestion/webhook/gps `
  -Headers @{"X-Vendor-Id"="vendor_a"; "X-Request-Id"="manual-test-1"} `
  -ContentType "application/json" `
  -Body ($body | ConvertTo-Json -Depth 8)
```

Direct ingestion API path (optional, bypass Nginx):

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri http://localhost:8001/webhook/gps `
  -Headers @{"X-Vendor-Id"="vendor_a"; "X-Request-Id"="manual-test-1"} `
  -ContentType "application/json" `
  -Body ($body | ConvertTo-Json -Depth 8)
```

Expected response includes:
- `accepted`
- `published`
- `rejected`
- `error_summary`

## 6. Run High-Load Simulation (600 trucks, 3000 events/sec)

### Option A: Makefile target (recommended)

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
make loadtest-gps
Pop-Location
```

### Option B: Direct script call

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
uv run python scripts/loadtest/gps_ingestion_load_test.py `
  --base-url http://127.0.0.1:8001 `
  --endpoint /webhook/gps `
  --trucks 600 `
  --target-eps 3000 `
  --duration-seconds 30 `
  --concurrency 1200
Pop-Location
```

Reports are generated in:
- `scripts/loadtest/reports/*.json`
- `scripts/loadtest/reports/*.md`

## 7. Verify Data Is Actually Arriving

### A. Check ingestion logs

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
docker compose -f infra/docker-compose.yml logs -f ingestion-api
Pop-Location
```

Look for log events like:
- `webhook_gps.ingested`
- `accepted/published/rejected` counters

### B. Check Redis stream lengths (core signal)

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
docker compose -f infra/docker-compose.yml exec redis redis-cli XLEN gps.telemetry.raw
docker compose -f infra/docker-compose.yml exec redis redis-cli XLEN gps.telemetry.retry
docker compose -f infra/docker-compose.yml exec redis redis-cli XLEN gps.telemetry.failed
Pop-Location
```

### C. Inspect latest entries in telemetry stream

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
docker compose -f infra/docker-compose.yml exec redis redis-cli XREVRANGE gps.telemetry.raw + - COUNT 5
Pop-Location
```

### D. Inspect failed-ingestion records via admin API

```powershell
Invoke-RestMethod "http://localhost:8003/v1/ingestion/failures?source=all&limit=50"
Invoke-RestMethod "http://localhost:8003/v1/ingestion/failures?source=dlq&retryable=true&limit=50"
```

## 8. Validate Metrics / Dashboards

### Prometheus

Open:
- `http://localhost:9090`

Try queries:
- `sum(rate(swm_webhook_gps_requests_total[1m]))`
- `sum(rate(swm_webhook_gps_payload_records_total{stage="published"}[1m]))`
- `histogram_quantile(0.95, sum by (le) (rate(swm_webhook_gps_processing_seconds_bucket[1m]))) * 1000`
- `sum(rate(swm_webhook_gps_validation_failures_total[1m]))`
- `sum by (retryable) (rate(swm_webhook_gps_publish_failures_total[1m]))`

### Grafana

Open:
- `http://localhost:3000`
- user: `admin`
- pass: `admin`

Dashboards:
- `Fleet Platform Overview`
- `Ingestion Webhook Performance`

## 9. Quick Failure Test (to validate quarantine)

Send an invalid record:

```powershell
$bad = @(@{ imei = "BAD"; latitude = 999; longitude = 77.2 })
Invoke-RestMethod `
  -Method POST `
  -Uri http://localhost:8001/webhook/gps `
  -Headers @{"X-Vendor-Id"="vendor_a"} `
  -ContentType "application/json" `
  -Body ($bad | ConvertTo-Json -Depth 8)
```

Then verify quarantine increased:

```powershell
docker compose -f infra/docker-compose.yml exec redis redis-cli XLEN gps.telemetry.retry
```

## 10. Stop Stack

```powershell
Push-Location "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform"
docker compose -f infra/docker-compose.yml down
Pop-Location
```

---

## Troubleshooting

- If load test cannot connect:
  - verify ingestion API health: `http://localhost:8001/healthz`
  - verify container is healthy: `docker compose -f infra/docker-compose.yml ps`
- If admin failures endpoint is empty while you expect failures:
  - generate invalid payloads (step 9)
  - check quarantine stream length in Redis
- If Grafana shows no data:
  - verify Prometheus target scrape success
  - run traffic for at least 1-2 minutes before checking rate queries
