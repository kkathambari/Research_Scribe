@echo off
setlocal

cd /d "%~dp0"
echo [INFO] Running ResearchScribe Backup...
if exist "backend\.venv\Scripts\python.exe" (
    backend\.venv\Scripts\python.exe scripts\backup_data.py --backup %1
) else (
    python scripts\backup_data.py --backup %1
)
pause
