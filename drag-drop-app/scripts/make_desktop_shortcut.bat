@echo off
REM Creates/updates the "Flag Machine" desktop shortcut for the CURRENT
REM user: double-clickable launcher for START.bat with the app icon (pennant
REM flags). Safe to run repeatedly - it just overwrites the shortcut.
REM Works from any checkout location: the shortcut always points at the
REM START.bat sitting next to this script's parent folder.

setlocal
for %%i in ("%~dp0..") do set "APP_DIR=%%~fi"

if not exist "%APP_DIR%\START.bat" (
    echo ERROR: START.bat not found in %APP_DIR%
    pause
    exit /b 1
)
if not exist "%APP_DIR%\static\icons\app.ico" (
    echo ERROR: app.ico not found - run scripts\make_window_icons.py first.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ws = New-Object -ComObject WScript.Shell;" ^
 "$lnk = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Flag Machine.lnk'));" ^
 "$lnk.TargetPath = '%APP_DIR%\START.bat';" ^
 "$lnk.WorkingDirectory = '%APP_DIR%';" ^
 "$lnk.IconLocation = '%APP_DIR%\static\icons\app.ico,0';" ^
 "$lnk.Description = 'Flag Machine + Finish Sheet';" ^
 "$lnk.Save();" ^
 "Write-Host ('Shortcut created: ' + $lnk.FullName)"

if errorlevel 1 (
    echo ERROR: shortcut creation failed.
    pause
    exit /b 1
)
echo.
echo Done. Double-click "Flag Machine" on the desktop to launch the app
echo (only ONE server will run, no matter how many times it is launched).
timeout /t 3
