# Drag-Drop App Launcher for Windows (PowerShell)
# This script starts both the Flag Machine and Sailor Scorer apps

$pythonPath = "C:\ProgramData\miniconda3\python.exe"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Flag Machine + Sailor Scorer" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if Python exists
if (-not (Test-Path $pythonPath)) {
    Write-Host "ERROR: Python not found at $pythonPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Using Python: $pythonPath" -ForegroundColor Green

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

Write-Host "✓ Flask is installed" -ForegroundColor Green
Write-Host "`nStarting applications..." -ForegroundColor Cyan

# Start both apps in separate windows
Write-Host "→ Flag Machine on http://localhost:5000" -ForegroundColor Green
Start-Process -FilePath $pythonPath -ArgumentList "app.py" -WorkingDirectory $PSScriptRoot

Write-Host "→ Sailor Scorer on http://localhost:5001" -ForegroundColor Green
Start-Process -FilePath $pythonPath -ArgumentList "score.py" -WorkingDirectory $PSScriptRoot

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✓ Both apps are running!" -ForegroundColor Green
Write-Host "`nFlag Machine:    http://localhost:5000" -ForegroundColor White
Write-Host "Sailor Scorer:   http://localhost:5001" -ForegroundColor White
Write-Host "`nTo stop the apps, close the Python windows." -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

Read-Host "Press Enter to continue"
