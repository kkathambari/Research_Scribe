@echo off
setlocal EnableDelayedExpansion

title ResearchScribe - Local Deployment Launcher

echo ======================================================================
echo   ResearchScribe - Evidence-Grounded AI Research Writing System
echo   Native Windows Local Deployment (Docker-Free)
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python Virtual Environment
if exist "backend\.venv\Scripts\python.exe" (
    echo [OK] Python virtual environment found at backend\.venv
) else (
    echo [INFO] Virtual environment not found. Checking system Python...
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python 3.10+ is required but not found in PATH.
        echo Please install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo [INFO] Creating Python virtual environment in backend\.venv...
    python -m venv backend\.venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Installing required dependencies...
    backend\.venv\Scripts\python.exe -m pip install --upgrade pip
    backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully.
)

:: 2. Check Ollama Status
echo [INFO] Checking local Ollama service at http://localhost:11434...
curl -s http://localhost:11434/api/tags >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Ollama service is running on localhost:11434.
) else (
    echo [WARN] Ollama service is not responding on http://localhost:11434.
    where ollama >nul 2>nul
    if %errorlevel% equ 0 (
        echo [INFO] Found local Ollama executable. Attempting to start 'ollama serve' in background...
        start "Ollama Serve" /B ollama serve
        timeout /t 3 /nobreak >nul
        curl -s http://localhost:11434/api/tags >nul 2>nul
        if %errorlevel% equ 0 (
            echo [OK] Ollama service started successfully.
        ) else (
            echo [WARN] Ollama did not respond immediately. You can start it manually via 'ollama serve'.
        )
    ) else (
        echo [WARN] Ollama is not installed or not in PATH.
        echo        Download from https://ollama.com if you want local LLM generation.
        echo        ResearchScribe can still run using heuristic fallback or Gemini.
    )
)

:: 3. Launch ResearchScribe Server
echo.
echo [INFO] Launching ResearchScribe backend...
cd backend
.venv\Scripts\python.exe run.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] ResearchScribe terminated with error code %errorlevel%.
    pause
)
