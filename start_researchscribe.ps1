# ResearchScribe - PowerShell Launcher
# Docker-Free Native Windows Deployment

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  ResearchScribe - Evidence-Grounded AI Research Writing System" -ForegroundColor Cyan
Write-Host "  Native Windows Local Deployment (Docker-Free)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$RootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootPath

# 1. Virtual Environment
$VenvPython = Join-Path $RootPath "backend\.venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    Write-Host "[OK] Python virtual environment found at backend\.venv" -ForegroundColor Green
} else {
    Write-Host "[INFO] Creating Python virtual environment in backend\.venv..." -ForegroundColor Yellow
    python -m venv backend\.venv
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r backend\requirements.txt
    Write-Host "[OK] Dependencies installed successfully." -ForegroundColor Green
}

# 2. Check Ollama
Write-Host "[INFO] Checking local Ollama service at http://localhost:11434..." -ForegroundColor Cyan
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($resp) {
        Write-Host "[OK] Ollama is active on localhost:11434." -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] Ollama is not responding on http://localhost:11434." -ForegroundColor Yellow
    $ollamaExe = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaExe) {
        Write-Host "[INFO] Starting 'ollama serve' in background..." -ForegroundColor Cyan
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    } else {
        Write-Host "[WARN] Ollama executable not found in PATH." -ForegroundColor Yellow
    }
}

# 3. Launch Backend
Write-Host ""
Write-Host "[INFO] Launching ResearchScribe backend on http://127.0.0.1:8000..." -ForegroundColor Green
Set-Location (Join-Path $RootPath "backend")
& $VenvPython run.py
