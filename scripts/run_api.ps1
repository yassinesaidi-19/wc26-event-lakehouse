$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    throw "Virtual environment not found. Run .\scripts\setup_windows.ps1 first."
}

. .\.venv\Scripts\Activate.ps1

$apiPath = "api\main.py"
if (-not (Test-Path $apiPath)) {
    throw "API entrypoint not found: $apiPath"
}

$requiredPaths = @(
    "data\processed\event_log\event_log.csv",
    "data\processed\canonical\dim_team.csv",
    "data\processed\canonical\fact_match.csv",
    "data\processed\canonical\fact_match_event.csv",
    "data\processed\state\state_group_standings.csv",
    "data\processed\marts\mart_group_standings.csv",
    "data\processed\marts\mart_match_center.csv",
    "data\processed\marts\mart_team_performance.csv",
    "data\quality\quality_report.json"
)

$missingPaths = @($requiredPaths | Where-Object { -not (Test-Path $_) })
if ($missingPaths.Count -gt 0) {
    Write-Host "Processed outputs missing. Running python run_pipeline.py first..."
    python run_pipeline.py
}

python -m uvicorn api.main:app --reload
