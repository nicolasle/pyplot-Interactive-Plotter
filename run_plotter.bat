@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Find real pythonw or python executable, explicitly bypassing WindowsApps 0-byte execution aliases
set "PY_BIN="

REM 1. Direct checks in standard user Python directories (instant, avoids WindowsApps AppX broker delays)
if exist "%LOCALAPPDATA%\Python\bin\pythonw.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Python\bin\pythonw.exe"
    goto :launch
)
if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\pythonw.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Python\pythoncore-3.15-64\pythonw.exe"
    goto :launch
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    goto :launch
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    goto :launch
)

REM 2. Look through PATH for pythonw, filtering out any WindowsApps entry
for /f "delims=" %%i in ('where pythonw 2^>nul') do (
    echo "%%i" | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        if not defined PY_BIN set "PY_BIN=%%i"
    )
)

if defined PY_BIN goto :launch

REM 3. Fallback to direct python.exe outside WindowsApps
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_BIN=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :launch
)
for /f "delims=" %%i in ('where python 2^>nul') do (
    echo "%%i" | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        if not defined PY_BIN set "PY_BIN=%%i"
    )
)

:launch
if defined PY_BIN (
    start "" "%PY_BIN%" app.py
) else (
    start "" python app.py
)
endlocal
