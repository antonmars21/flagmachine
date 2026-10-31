@echo off
REM Drag-Drop App Launcher for Windows
REM Starts the Flag Machine + Finish Sheet app (Flask, port 5000)

setlocal enabledelayedexpansion

REM === CHECK BOTH POSSIBLE LOCATIONS ===
set "APP_DIR="
if exist "C:\Users\Public\Documents\flagmachine\drag-drop-app" (
    set "APP_DIR=C:\Users\Public\Documents\flagmachine\drag-drop-app"
) else if exist "C:\Users\Anton\flagmachine\drag-drop-app" (
    set "APP_DIR=C:\Users\Anton\flagmachine\drag-drop-app"
)

if not defined APP_DIR (
    echo ERROR: Could not find the app folder in either location.
    pause
    exit /b 1
)
REM Use miniconda Python
set "PYTHON=C:\ProgramData\miniconda3\python.exe"

REM Check app folder exists
if not exist "%APP_DIR%\app.py" (
    echo ERROR: app.py not found in %APP_DIR%
    echo Edit APP_DIR at the top of this script.
    pause
    exit /b 1
)

REM Check if Python exists
if not exist "%PYTHON%" (
    echo ERROR: Python not found at %PYTHON%
    echo Edit PYTHON at the top of this script.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Flag Machine + Finish Sheet
echo ========================================
echo.
echo App folder: %APP_DIR%
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
echo Starting app...
echo ========================================
echo.

start "Flag Machine - http://localhost:5000" cmd /k "cd /d %APP_DIR% && %PYTHON% app.py"

echo.
echo ========================================
echo App started! Open your browser:
echo.
echo Flag Machine:    http://localhost:5000
echo Finish Sheet:    http://localhost:5000/finishsheet
echo Display Board:   http://localhost:5000/display
echo.
echo Close the Command Prompt window to stop the app.
echo ========================================
echo.

timeout /t 3
