$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
    docker compose -f infra/docker-compose.yml up -d postgres | Out-Null

    $previousDsn = $env:POSTGRES_DSN
    $env:POSTGRES_DSN = "postgresql+asyncpg://swm:swm@localhost:55432/swm"

    if (Test-Path ".venv/Scripts/python.exe") {
        & ".venv/Scripts/python.exe" -m alembic -c libs/db/alembic.ini upgrade head
    } else {
        python -m alembic -c libs/db/alembic.ini upgrade head
    }
}
finally {
    if ($null -ne $previousDsn) {
        $env:POSTGRES_DSN = $previousDsn
    } else {
        Remove-Item Env:POSTGRES_DSN -ErrorAction SilentlyContinue
    }
    Pop-Location
}
