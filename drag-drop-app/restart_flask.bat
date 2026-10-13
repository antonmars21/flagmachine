@echo off
REM Restart the Flask app (kills anything on port 5000, then relaunches)

REM === EDIT THIS PATH IF THE APP FOLDER MOVES ===
set "APP_DIR=C:\Users\Public\flagmachine\drag-drop-app"

set "PYTHON=C:\ProgramData\miniconda3\python.exe"

REM Kill any existing Python processes on port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do taskkill /PID %%a /F

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start fresh Flask app with debug=True
cd /d "%APP_DIR%"
"%PYTHON%" app.py
