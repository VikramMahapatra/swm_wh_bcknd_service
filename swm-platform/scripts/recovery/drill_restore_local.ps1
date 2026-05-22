param(
  [string]$ComposeFile = "infra/docker-compose.yml",
  [Parameter(Mandatory = $true)]
  [string]$ArtifactDir,
  [string]$PostgresService = "postgres",
  [string]$RedisService = "redis",
  [string]$ClickhouseService = "clickhouse",
  [string]$PostgresDb = "swm",
  [string]$PostgresUser = "swm",
  [string]$ClickhouseDb = "swm",
  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Log-Info {
  param([string]$Message)
  Write-Host "[INFO] $Message"
}

if (-not $Force) {
  throw "Refusing restore without -Force. This operation is destructive."
}

$manifestPath = Join-Path $ArtifactDir "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
  throw "manifest.json not found under $ArtifactDir"
}

$manifest = Get-Content -Raw -Path $manifestPath | ConvertFrom-Json
$postgresDump = [string]$manifest.postgres_dump
$redisRdb = [string]$manifest.redis_rdb
$clickhouseTables = @($manifest.clickhouse_tables)

if (-not (Test-Path -LiteralPath $postgresDump)) {
  throw "PostgreSQL dump not found: $postgresDump"
}
if (-not (Test-Path -LiteralPath $redisRdb)) {
  throw "Redis RDB not found: $redisRdb"
}

Log-Info "Restoring PostgreSQL from $postgresDump"
docker compose -f $ComposeFile cp $postgresDump "${PostgresService}:/tmp/drill_restore.sql"
docker compose -f $ComposeFile exec -T $PostgresService sh -lc "psql -U $PostgresUser -d $PostgresDb -f /tmp/drill_restore.sql"

Log-Info "Restoring Redis from $redisRdb"
docker compose -f $ComposeFile cp $redisRdb "${RedisService}:/data/dump.rdb"
docker compose -f $ComposeFile restart $RedisService

foreach ($table in $clickhouseTables) {
  $safeName = [string]$table
  $schemaPath = Join-Path (Join-Path $ArtifactDir "clickhouse") ($safeName.Replace(".", "_") + ".create.sql")
  $dataPath = Join-Path (Join-Path $ArtifactDir "clickhouse") ($safeName.Replace(".", "_") + ".tsv")

  if (-not (Test-Path -LiteralPath $schemaPath)) {
    throw "ClickHouse schema file not found: $schemaPath"
  }
  if (-not (Test-Path -LiteralPath $dataPath)) {
    throw "ClickHouse data file not found: $dataPath"
  }

  Log-Info "Restoring ClickHouse table $ClickhouseDb.$table"
  $schemaSql = Get-Content -Raw -Path $schemaPath

  # Recreate table before data import.
  $dropSql = "DROP TABLE IF EXISTS $ClickhouseDb.$table"
  docker compose -f $ComposeFile exec -T $ClickhouseService clickhouse-client --query $dropSql | Out-Null
  docker compose -f $ComposeFile exec -T $ClickhouseService clickhouse-client --query $schemaSql | Out-Null

  Get-Content -Path $dataPath -Raw |
    docker compose -f $ComposeFile exec -T $ClickhouseService clickhouse-client --query "INSERT INTO $ClickhouseDb.$table FORMAT TSVWithNamesAndTypes" | Out-Null
}

Write-Host "[OK] Restore drill completed successfully"
