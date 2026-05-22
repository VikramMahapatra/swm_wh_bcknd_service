param(
  [string]$ComposeFile = "infra/docker-compose.yml",
  [string]$BackupDir = "scripts/recovery/artifacts",
  [string]$PostgresService = "postgres",
  [string]$RedisService = "redis",
  [string]$ClickhouseService = "clickhouse",
  [string]$PostgresDb = "swm",
  [string]$PostgresUser = "swm",
  [string]$ClickhouseDb = "swm",
  [string[]]$ClickhouseTables = @("raw_telemetry")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-DirIfMissing {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }
}

function Log-Info {
  param([string]$Message)
  Write-Host "[INFO] $Message"
}

function Save-PostgresDump {
  param(
    [string]$OutputPath
  )

  Log-Info "Creating PostgreSQL backup at $OutputPath"
  $containerPath = "/tmp/drill_postgres.sql"
  $cmd = "pg_dump -U $PostgresUser -d $PostgresDb -Fp -f $containerPath"
  docker compose -f $ComposeFile exec -T $PostgresService sh -lc $cmd
  docker compose -f $ComposeFile cp "${PostgresService}:$containerPath" $OutputPath
}

function Save-RedisRdb {
  param([string]$OutputPath)

  Log-Info "Creating Redis RDB backup at $OutputPath"
  $containerPath = "/tmp/drill_backup.rdb"
  docker compose -f $ComposeFile exec -T $RedisService sh -lc "redis-cli --rdb $containerPath >/dev/null"
  docker compose -f $ComposeFile cp "${RedisService}:$containerPath" $OutputPath
}

function Save-ClickhouseTable {
  param(
    [string]$Table,
    [string]$SchemaPath,
    [string]$DataPath
  )

  Log-Info "Backing up ClickHouse table $ClickhouseDb.$Table"
  $schemaSql = docker compose -f $ComposeFile exec -T $ClickhouseService clickhouse-client --query "SHOW CREATE TABLE $ClickhouseDb.$Table"
  [System.IO.File]::WriteAllText($SchemaPath, [string]$schemaSql)

  $dataText = docker compose -f $ComposeFile exec -T $ClickhouseService clickhouse-client --query "SELECT * FROM $ClickhouseDb.$Table FORMAT TSVWithNamesAndTypes"
  [System.IO.File]::WriteAllText($DataPath, [string]$dataText)
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $BackupDir $timestamp
New-DirIfMissing -Path $runDir

$pgDumpPath = Join-Path $runDir "postgres.sql"
$redisRdbPath = Join-Path $runDir "redis.rdb"
$chDir = Join-Path $runDir "clickhouse"
New-DirIfMissing -Path $chDir

Save-PostgresDump -OutputPath $pgDumpPath
Save-RedisRdb -OutputPath $redisRdbPath

foreach ($table in $ClickhouseTables) {
  $safeName = $table.Replace(".", "_")
  $schemaPath = Join-Path $chDir "$safeName.create.sql"
  $dataPath = Join-Path $chDir "$safeName.tsv"
  Save-ClickhouseTable -Table $table -SchemaPath $schemaPath -DataPath $dataPath
}

$manifest = [ordered]@{
  created_at = (Get-Date).ToString("o")
  compose_file = $ComposeFile
  postgres_dump = $pgDumpPath
  redis_rdb = $redisRdbPath
  clickhouse_tables = $ClickhouseTables
  clickhouse_db = $ClickhouseDb
}
$manifestPath = Join-Path $runDir "manifest.json"
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "[OK] Backup drill completed"
Write-Host "[OK] Artifact directory: $runDir"
