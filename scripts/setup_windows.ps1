$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    $venvCreated = $false

    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3.13 -c "import sys" | Out-Null
            & py -3.13 -m venv .venv
            $venvCreated = $true
            Write-Host "Created .venv with Python 3.13."
        }
        catch {
            Write-Host "Python 3.13 was not available through the py launcher. Falling back to the default python command."
        }
    }

    if (-not $venvCreated) {
        & python -m venv .venv
        Write-Host "Created .venv with the default python command."
    }
}
else {
    Write-Host "Using existing .venv."
}

. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete. Next commands:"
Write-Host "  .\scripts\run_dashboard.ps1"
Write-Host "  .\scripts\run_api.ps1"
Write-Host ""
Write-Host "Manual equivalents:"
Write-Host "  python -m streamlit run dashboard/streamlit_app.py"
Write-Host "  python -m uvicorn api.main:app --reload"
