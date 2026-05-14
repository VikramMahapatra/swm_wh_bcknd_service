param(
  [string]$Root = "c:\Users\vikik\Projects\swm_wh_bcknd_service\swm-platform",
  [switch]$SkipBootstrap,
  [switch]$SkipLoad,
  [switch]$NoFollowLogs,
  [int]$LoadDurationSeconds = 30,
  [int]$LoadEps = 3000,
  [int]$LoadConcurrency = 1200,
  [int]$LoadTrucks = 600
)

$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "[STEP] $Message" -ForegroundColor Cyan
}

function Write-Ok {
  param([string]$Message)
  Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Write-Warn {
  param([string]$Message)
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Invoke-HealthCheck {
  param(
    [string]$Url,
    [string]$Name
  )
  $maxAttempts = 30
  for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    try {
      $resp = Invoke-RestMethod -Method GET -Uri $Url -TimeoutSec 5
      Write-Ok "$Name healthy"
      return
    } catch {
      if ($attempt -eq $maxAttempts) {
        throw "Health check failed for $Name at $Url after $maxAttempts attempts"
      }
      Start-Sleep -Seconds 2
    }
  }
}

Push-Location $Root
try {
  Write-Step "Repository root: $Root"

  if (-not $SkipBootstrap) {
    Write-Step "Bootstrapping workspace dependencies"
    .\scripts\dev.ps1
    Write-Ok "Bootstrap complete"
  } else {
    Write-Warn "Skipping bootstrap (--SkipBootstrap)"
  }

  Write-Step "Starting full stack with Docker Compose"
  docker compose -f infra/docker-compose.yml up -d --build | Out-Host
  Write-Ok "Compose stack started"

  Write-Step "Waiting for API/Nginx health endpoints"
  Invoke-HealthCheck -Url "http://localhost:8001/healthz" -Name "ingestion-api"
  Invoke-HealthCheck -Url "http://localhost:8003/healthz" -Name "admin-api"
  Invoke-HealthCheck -Url "http://localhost/healthz" -Name "nginx"

  Write-Step "Posting sample GPS payload through nginx route"
  $sampleBody = @(
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

  $sampleResp = Invoke-RestMethod `
    -Method POST `
    -Uri "http://localhost/ingestion/webhook/gps" `
    -Headers @{"X-Vendor-Id"="vendor_a"; "X-Request-Id"="e2e-smoke-1"} `
    -ContentType "application/json" `
    -Body ($sampleBody | ConvertTo-Json -Depth 8)

  Write-Ok "Sample push response: accepted=$($sampleResp.accepted), published=$($sampleResp.published), rejected=$($sampleResp.rejected)"

  Write-Step "Posting one invalid payload to verify quarantine path"
  $badBody = @(@{ imei = "BAD"; latitude = 999; longitude = 77.2 })
  $badBodyJson = "[" + (($badBody[0]) | ConvertTo-Json -Depth 8) + "]"
  try {
    $badResp = Invoke-RestMethod `
      -Method POST `
      -Uri "http://localhost/ingestion/webhook/gps" `
      -Headers @{"X-Vendor-Id"="vendor_a"; "X-Request-Id"="e2e-bad-1"} `
      -ContentType "application/json" `
      -Body $badBodyJson

    Write-Ok "Failure-path response: accepted=$($badResp.accepted), published=$($badResp.published), rejected=$($badResp.rejected)"
  } catch {
    $err = $_.Exception.Message
    Write-Warn "Failure-path request returned non-2xx (continuing): $err"
  }

  if (-not $SkipLoad) {
    Write-Step "Running load test (trucks=$LoadTrucks, eps=$LoadEps, duration=$LoadDurationSeconds, concurrency=$LoadConcurrency)"
    $env:LOADTEST_TRUCKS = "$LoadTrucks"
    $env:LOADTEST_EPS = "$LoadEps"
    $env:LOADTEST_DURATION = "$LoadDurationSeconds"
    $env:LOADTEST_CONCURRENCY = "$LoadConcurrency"
    make loadtest-gps | Out-Host
    Write-Ok "Load test completed"
  } else {
    Write-Warn "Skipping load test (--SkipLoad)"
  }

  Write-Step "Inspecting Redis stream lengths"
  $xlenMain = docker compose -f infra/docker-compose.yml exec -T redis redis-cli XLEN gps.telemetry.raw
  $xlenQuarantine = docker compose -f infra/docker-compose.yml exec -T redis redis-cli XLEN gps.telemetry.retry
  $xlenDlq = docker compose -f infra/docker-compose.yml exec -T redis redis-cli XLEN gps.telemetry.failed

  Write-Ok "gps.telemetry.raw XLEN = $xlenMain"
  Write-Ok "gps.telemetry.retry XLEN = $xlenQuarantine"
  Write-Ok "gps.telemetry.failed XLEN = $xlenDlq"

  Write-Step "Fetching admin inspection sample"
  try {
    $failures = Invoke-RestMethod -Method GET -Uri "http://localhost:8003/v1/ingestion/failures?source=all&limit=10"
    $failureCount = 0
    if ($null -ne $failures -and $null -ne $failures.items) {
      $failureCount = $failures.items.Count
    }
    Write-Ok "Admin failures endpoint returned $failureCount records"
  } catch {
    Write-Warn "Admin failures endpoint request failed (continuing): $($_.Exception.Message)"
  }

  Write-Host ""
  Write-Host "Open these URLs to verify metrics and dashboards:" -ForegroundColor Cyan
  Write-Host "  Prometheus: http://localhost:9090"
  Write-Host "  Grafana:    http://localhost:3000 (admin/admin)"

  if (-not $NoFollowLogs) {
    Write-Step "Following ingestion-api logs (Ctrl+C to stop)"
    docker compose -f infra/docker-compose.yml logs -f ingestion-api
  }

  Write-Ok "E2E local production-like test flow completed"
} finally {
  Pop-Location
}
