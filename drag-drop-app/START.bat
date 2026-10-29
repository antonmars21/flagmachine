@echo off
REM Drag-Drop App Launcher for Windows
REM Starts the Flag Machine + Finish Sheet app (Flask, port 5000)

setlocal enabledelayedexpansion

REM === EDIT THIS PATH IF THE APP FOLDER MOVES ===
set "APP_DIR=C:\Users\Public\flagmachine\drag-drop-app"
REM === EDIT THIS PATH IF THE APP FOLDER MOVES ===
set "APP_DIR=C:\Users\Anton\flagmachine\drag-drop-app"

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

REM SINGLE-INSTANCE GUARD: only ONE Flask server may run at a time.
REM If the app already answers on port 5000, do NOT start a second one -
REM just reopen the app windows (restores a window that was closed).
"%PYTHON%" -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/', timeout=2)" >nul 2>&1
if %errorlevel% equ 0 (
    echo The app is ALREADY RUNNING - reusing the existing server.
    echo Reopening the app windows - close any extra ones you do not need.
    goto SERVER_UP
)

start "Flag Machine - http://localhost:5000" cmd /k "cd /d %APP_DIR% && %PYTHON% app.py"

echo Waiting for the app to come up...

REM Wait until the Flask server answers, then open the race-day windows
set /a TRIES=0
:WAIT_SERVER
"%PYTHON%" -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/', timeout=2)" >nul 2>&1
if %errorlevel% equ 0 goto SERVER_UP
set /a TRIES+=1
if %TRIES% geq 30 (
    echo WARNING: the app did not answer on http://localhost:5000 within 30 seconds.
    echo Open the pages manually from the list below.
    goto SHOW_URLS
)
timeout /t 1 /nobreak >nul
goto WAIT_SERVER

:SERVER_UP
echo App is up - opening the race-day windows.

REM Bug 32/34: every page opens in its OWN application window (--app mode:
REM no browser tabs, no back/forward buttons, so the RO control window can
REM never be navigated away or closed by mistake). Chrome if installed,
REM otherwise Edge (present on every Windows 10/11 machine).
set "BROWSER="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER set "BROWSER=msedge"

start "" "%BROWSER%" --app="http://localhost:5000/"
timeout /t 1 /nobreak >nul
start "" "%BROWSER%" --app="http://localhost:5000/finishsheet?station=1"
timeout /t 1 /nobreak >nul
start "" "%BROWSER%" --app="http://localhost:5000/finishsheet?station=2"
timeout /t 1 /nobreak >nul
start "" "%BROWSER%" --app="http://localhost:5000/display"

:SHOW_URLS
echo.
echo ========================================
echo Race Officer Control: http://localhost:5000
echo Finish Sheet 1:        http://localhost:5000/finishsheet?station=1
echo Finish Sheet 2:        http://localhost:5000/finishsheet?station=2
echo Display Board:         http://localhost:5000/display
echo.
echo Close the Command Prompt window to stop the app.
echo ========================================
echo.

timeout /t 3
