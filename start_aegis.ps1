<#
  AEGIS one-click launcher (Windows 10/11, PowerShell)
  Usage:  right-click -> "Run with PowerShell"   or   .\start_aegis.ps1
#>
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "=== AEGIS - Assisted Executive Guidance and Intelligence System ===" -ForegroundColor Cyan

# 1. Python virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "[1/5] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"

# 2. Dependencies (skipped when already installed)
if (-not (Test-Path ".venv\.deps_installed")) {
    Write-Host "[2/5] Installing Python dependencies (first run only)..." -ForegroundColor Yellow
    python -m pip install --upgrade pip | Out-Null
    pip install -r requirements.txt
    New-Item ".venv\.deps_installed" -ItemType File | Out-Null
} else {
    Write-Host "[2/5] Dependencies already installed." -ForegroundColor Green
}

# 3. Local vision model
Write-Host "[3/5] Checking YOLOv5m vision model..." -ForegroundColor Yellow
python scripts\download_models.py

# 4. Frontend build (prebuilt dist is committed; rebuild only if Node is available and dist is missing)
if (-not (Test-Path "frontend\dist\index.html")) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "[4/5] Building React frontend..." -ForegroundColor Yellow
        Push-Location frontend
        npm install --no-audit --no-fund
        npm run build
        Pop-Location
    } else {
        Write-Host "[4/5] frontend\dist is missing and Node.js is not installed. Install Node 18+ and re-run." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[4/5] Frontend build found." -ForegroundColor Green
}

if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "      Created .env - add GEMINI_API_KEY to enable Gemini 2.5 Flash reasoning." -ForegroundColor DarkYellow
}

# 5. Launch backend and open the UI
Write-Host "[5/5] Starting AEGIS on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Job -ScriptBlock { Start-Sleep -Seconds 4; Start-Process "http://127.0.0.1:8000" } | Out-Null
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
