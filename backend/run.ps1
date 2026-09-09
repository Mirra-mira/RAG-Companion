$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path "venv")) {
    Write-Host "[run] Chua co venv - chay .\setup.ps1 truoc."
    exit 1
}

& ".\venv\Scripts\Activate.ps1"
# --host 0.0.0.0 de nghe ca IPv4 va IPv6 (fix Failed to fetch khi frontend goi localhost)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
