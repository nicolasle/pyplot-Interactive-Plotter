@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw app.py
) else (
    python app.py
)
