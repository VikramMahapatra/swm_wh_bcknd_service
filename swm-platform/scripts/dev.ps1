$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Error "uv is required. Install from https://docs.astral.sh/uv/"
}

uv sync --all-packages --all-groups
uv run pre-commit install
Write-Host "Workspace bootstrapped successfully"
