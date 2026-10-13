# Drag-Drop App Launcher for Windows (PowerShell)
# Starts the Flag Machine + Finish Sheet app (Flask, port 5000)

# === EDIT THIS PATH IF THE APP FOLDER MOVES ===
$AppDir = "C:\Users\Public\flagmachine\drag-drop-app"

$pythonPath = "C:\ProgramData\miniconda3\python.exe"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Flag Machine + Finish Sheet" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check app folder exists
if (-not (Test-Path "$AppDir\app.py")) {
    Write-Host "ERROR: app.py not found in $AppDir" -ForegroundColor Red
    Write-Host "Edit `$AppDir at the top of this script." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Python exists
if (-not (Test-Path $pythonPath)) {
    Write-Host "ERROR: Python not found at $pythonPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "App folder: $AppDir" -ForegroundColor Green
Write-Host "Using Python: $pythonPath" -ForegroundColor Green

# Check if Flask is installed
& $pythonPath -c "import flask" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Flask not found. Installing..." -ForegroundColor Yellow
    & $pythonPath -m pip install Flask
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Flask" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "Flask is installed" -ForegroundColor Green
Write-Host "`nStarting application...`n" -ForegroundColor Cyan

Start-Process -FilePath $pythonPath -ArgumentList "app.py" -WorkingDirectory $AppDir

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "App is running!" -ForegroundColor Green
Write-Host "`nFlag Machine:  http://localhost:5000" -ForegroundColor White
Write-Host "Finish Sheet:  http://localhost:5000/finishsheet" -ForegroundColor White
Write-Host "Display Board: http://localhost:5000/display" -ForegroundColor White
Write-Host "`nTo stop the app, close the Python window." -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

Read-Host "Press Enter to continue"
