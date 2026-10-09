@echo off
REM Drag-Drop App Launcher for Windows
REM This script starts both the Flag Machine and Sailor Scorer apps

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Flag Machine + Sailor Scorer
echo ========================================
echo.

REM Use miniconda Python
set PYTHON=C:\ProgramData\miniconda3\python.exe

REM Check if Python exists
if not exist "%PYTHON%" (
    echo ERROR: Python not found at %PYTHON%
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
echo.

REM Check if Flask is installed
"%PYTHON%" -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo Flask not found. Installing...
    "%PYTHON%" -m pip install Flask
    if !errorlevel! neq 0 (
        echo ERROR: Failed to install Flask
        pause
        exit /b 1
    )
)

echo ========================================
echo Starting both apps in separate windows...
echo ========================================
echo.

REM Open two separate Command Prompt windows for each app
start "Flag Machine - http://localhost:5000" cmd /k "cd /d %cd% && %PYTHON% app.py"
timeout /t 2

start "Sailor Scorer - http://localhost:5001" cmd /k "cd /d %cd% && %PYTHON% score.py"

echo.
echo ========================================
echo Apps started! Open your browser:
echo.
echo Flag Machine:    http://localhost:5000
echo Sailor Scorer:   http://localhost:5001
echo.
echo Each app runs in its own Command Prompt window.
echo Close those windows to stop the apps.
echo ========================================
echo.

timeout /t 3
