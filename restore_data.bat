@echo off
setlocal

cd /d "%~dp0"
if "%~1"=="" (
    echo [INFO] Available backups:
    if exist "backend\.venv\Scripts\python.exe" (
        backend\.venv\Scripts\python.exe scripts\backup_data.py --list
    ) else (
        python scripts\backup_data.py --list
    )
    echo.
    echo Usage: restore_data.bat backups\filename.zip
    echo Or drag-and-drop a backup zip file onto this .bat file.
    pause
    exit /b 0
)

echo [INFO] Restoring from backup: %1
if exist "backend\.venv\Scripts\python.exe" (
    backend\.venv\Scripts\python.exe scripts\backup_data.py --restore %1
) else (
    python scripts\backup_data.py --restore %1
)
pause
