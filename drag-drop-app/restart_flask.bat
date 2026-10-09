@echo off
REM Kill any existing Python processes on port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do taskkill /PID %%a /F

REM Wait a moment
timeout /t 2 /nobreak

REM Start fresh Flask app with debug=True
C:\ProgramData\miniconda3\python.exe app.py
