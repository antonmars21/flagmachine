@echo off
REM Drag-Drop App Launcher for Windows
REM Starts the Flag Machine + Finish Sheet app (Flask, port 5000)

setlocal enabledelayedexpansion

REM === EDIT THIS PATH IF THE APP FOLDER MOVES ===
set "APP_DIR=C:\Users\anton\flagmachine\drag-drop-app"
REM Dell PC option - to use it, REM the line above and remove REM from this one:
REM set "APP_DIR=C:\Users\Public\Documents\drag-drop-app"

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

REM Desktop icon (kanban "desktop icon"): make sure the "Flag Machine"
REM desktop shortcut exists - it is created automatically on the FIRST run on
REM each machine (e.g. the Dell), pointing at this folder's START.bat with the
REM app icon. Later runs skip it when the .lnk is already there.
if not exist "%USERPROFILE%\Desktop\Flag Machine.lnk" (
    if exist "%APP_DIR%\scripts\make_desktop_shortcut.bat" (
        echo Creating the "Flag Machine" desktop shortcut...
        call "%APP_DIR%\scripts\make_desktop_shortcut.bat" /q
    )
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
REM just open the app windows if they are not already open.
"%PYTHON%" -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/', timeout=2)" >nul 2>&1
if %errorlevel% equ 0 (
    echo The app is ALREADY RUNNING - reusing the existing server.
    echo If the app windows are not already open, they will be opened now.
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
echo App is up - checking whether the app windows are already open.

REM --- Launch lock: only ONE launcher instance may open the windows at a
REM time, so a double-click on the desktop shortcut can never open the RO
REM page twice. The lock file stores the launcher PID; if that process is
REM dead the lock is stale and is taken over.
set "LAUNCHLOCK=%TEMP%\flagmachine_launch.lock"
set "HAVELAUNCH=1"
set "LOCKOWNED=0"
if exist "%LAUNCHLOCK%" call :CHECK_LOCK
if "%HAVELAUNCH%"=="1" call :TAKE_LOCK
if "%HAVELAUNCH%"=="1" call :CHECK_WINDOWS
if "%HAVELAUNCH%"=="0" goto LAUNCH_DONE

REM Kanban bug "Fix screen navigation" (requirements updated 2026-11-03):
REM regular browser windows, not --app mode - tabs work inside every window
REM (Ctrl+Tab, back/forward). RO control, Station 1 and Station 2 start as
REM TABS in ONE NEW Brave window - it gets its own taskbar button (the
REM taskbar is the navigator, as in the earlier version) and the pages stack
REM as tabs instead of floating windows covering each other. Drag a tab out
REM to split a station onto a touch screen when needed. The Display Board
REM opens in its own SEPARATE window of the same browser (Brave) for the
REM outdoor screen.
set "BRAVE="
if exist "%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE=%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
if not defined BRAVE if exist "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE=%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"
if not defined BRAVE if exist "%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE=%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"
set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE set "EDGE=msedge"
REM All pages in Brave if installed (it is the default browser on the club
REM machines), otherwise Edge
if defined BRAVE (set "BROWSER=%BRAVE%") else (set "BROWSER=%EDGE%")

REM RO control + Station 1 + Station 2 as TABS in ONE NEW window of the
REM browser = one own taskbar button; Ctrl+Tab switches between the pages
start "" "%BROWSER%" --new-window "http://localhost:5000/" "http://localhost:5000/finishsheet?station=1" "http://localhost:5000/finishsheet?station=2"
timeout /t 1 /nobreak >nul
REM Display Board in its own SEPARATE window of the same browser (Brave):
REM own taskbar icon, outdoor screen
start "" "%BROWSER%" --new-window "http://localhost:5000/display"

:LAUNCH_DONE
if "%LOCKOWNED%"=="1" if exist "%LAUNCHLOCK%" del "%LAUNCHLOCK%" 2>nul

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
exit /b 0

:CHECK_LOCK
set /p LAUNCHPID=<"%LAUNCHLOCK%"
if "%LAUNCHPID%"=="" goto :eof
tasklist /FI "PID eq %LAUNCHPID%" 2>nul | find /i "%LAUNCHPID%" >nul
if not errorlevel 1 (
    echo Another launch is already opening the app windows - not opening duplicates.
    set "HAVELAUNCH=0"
)
goto :eof

:TAKE_LOCK
for /f "delims=" %%p in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter ([string]::Concat('ProcessId=',$PID))).ParentProcessId"') do set "LAUNCHPID=%%p"
echo %LAUNCHPID%>"%LAUNCHLOCK%"
set "LOCKOWNED=1"
goto :eof

:CHECK_WINDOWS
REM If an app page window is already open, do NOT open another set
REM (bug reports: "RO page opened twice", "display opens twice"). The helper
REM enumerates ALL visible windows, not just each browser process's main one.
powershell -NoProfile -File "%APP_DIR%\scripts\check_app_windows.ps1"
if %errorlevel% equ 0 (
    echo App windows are already open - not opening duplicates.
    set "HAVELAUNCH=0"
)
goto :eof
