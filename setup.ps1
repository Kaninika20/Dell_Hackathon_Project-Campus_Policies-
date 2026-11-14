#!/usr/bin/env pwsh
# setup.ps1 — One-time backend setup for CampusPolicy AI
# Run from the Dell_Hackathon_Project root directory.

Write-Host "=== CampusPolicy AI — Backend Setup ===" -ForegroundColor Cyan

Set-Location "$PSScriptRoot\backend"

# Create venv if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "=== Setup complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Copy .env.example to .env and fill in your keys"
Write-Host "  2. Start backend:  cd backend; venv\Scripts\Activate.ps1; uvicorn app.main:app --reload"
Write-Host "  3. Start frontend: cd frontend; npm run dev"
Write-Host "  4. Open: http://localhost:5173"

