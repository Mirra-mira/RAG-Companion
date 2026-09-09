$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path "venv")) {
    Write-Host "[setup] Tao venv..."
    python -m venv venv
}

Write-Host "[setup] Kich hoat venv..."
& ".\venv\Scripts\Activate.ps1"

Write-Host "[setup] Cai requirements..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[setup] Da tao .env tu .env.example - nho sua DATABASE_URL va GEMINI_API_KEY."
}

Write-Host "[setup] Xong. Dung .\run.ps1 de chay server."
