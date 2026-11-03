# Drag-Drop App Launcher for Windows (PowerShell)
# Starts the Flag Machine + Finish Sheet app (Flask, port 5000), then opens
# the race-day pages (kanban "Fix screen navigation", updated 2026-11-03):
# regular browser windows, not --app mode - tabs work inside every window.
# RO control, Station 1 and Station 2 start as TABS in ONE NEW Brave window
# (its own taskbar button - the taskbar is the navigator; drag a tab out to
# split a station onto a touch screen), and the Display Board opens in its
# own SEPARATE window of the same browser (Brave) for the outdoor screen.

# === EDIT THIS PATH IF THE APP FOLDER MOVES ===
$AppDir = "C:\Users\anton\flagmachine\drag-drop-app"
# Dell PC option - to use it, comment the line above and uncomment this one:
# $AppDir = "C:\Users\Public\Documents\drag-drop-app"

$pythonPath = "C:\ProgramData\miniconda3\python.exe"

$BaseUrl = "http://localhost:5000"

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

function Test-AppUp {
    try {
        $resp = Invoke-WebRequest -Uri $BaseUrl -TimeoutSec 2 -UseBasicParsing
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

# True if any Flag Machine app page window is already open. Enumerates ALL
# visible top-level windows (not just each browser process's main window), so
# a relaunch cannot open a duplicate Display Board window ("display opens
# twice"). Same logic as scripts/check_app_windows.ps1.
function Test-AppWindowsOpen {
    $pattern = 'Race Officer Control|Finish sheet|Outdoor Display'
    if (-not ('Win32Enum' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win32Enum {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc del, IntPtr lParam);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
}
'@
    }
    $script:found = $false
    $cb = {
        param($hWnd, $lParam)
        if ([Win32Enum]::IsWindowVisible($hWnd)) {
            $sb = New-Object System.Text.StringBuilder(512)
            [void][Win32Enum]::GetWindowText($hWnd, $sb, $sb.Capacity)
            if ($sb.ToString() -match $pattern) { $script:found = $true }
        }
        return $true
    }
    $null = [Win32Enum]::EnumWindows($cb, [IntPtr]::Zero)
    return $script:found
}

# SINGLE-INSTANCE GUARD: only ONE Flask server may run at a time. If the app
# already answers on port 5000, do NOT start a second one - just reopen the
# app windows (restores a window that was closed).
if (Test-AppUp) {
    Write-Host "The app is ALREADY RUNNING - reusing the existing server." -ForegroundColor Yellow
    Write-Host "If the app windows are not already open, they will be opened now." -ForegroundColor Yellow
} else {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Starting application..." -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    Start-Process -FilePath $pythonPath -ArgumentList "app.py" -WorkingDirectory $AppDir

    Write-Host "Waiting for the app to come up..."
    $tries = 0
    while (-not (Test-AppUp)) {
        $tries++
        if ($tries -ge 30) {
            Write-Host "WARNING: the app did not answer on $BaseUrl within 30 seconds." -ForegroundColor Yellow
            Write-Host "Open the pages manually from the list below." -ForegroundColor Yellow
            break
        }
        Start-Sleep -Seconds 1
    }
}

# Browsers: Brave (default browser on the club machines) and Edge (present on
# every Windows 10/11 machine, used only if Brave is missing). All pages open
# in Brave: work pages as tabs in one new window, the Display Board in its own
# separate window.
$Brave = $null
foreach ($candidate in @(
    "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe",
    "$env:ProgramFiles\BraveSoftware\Brave-Browser\Application\brave.exe",
    "${env:ProgramFiles(x86)}\BraveSoftware\Brave-Browser\Application\brave.exe"
)) {
    if ($null -eq $Brave -and (Test-Path $candidate)) { $Brave = $candidate }
}
$Edge = $null
foreach ($candidate in @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)) {
    if ($null -eq $Edge -and (Test-Path $candidate)) { $Edge = $candidate }
}
if ($null -eq $Edge) { $Edge = "msedge" }
# All pages in Brave if installed, otherwise Edge
$Browser = if ($Brave) { $Brave } else { $Edge }

# Launch lock + duplicate-window guard (bug report "RO page opened twice"):
# only ONE launcher instance may open the windows at a time (a double-click
# on the desktop shortcut must not open the RO page twice), and if an app
# page window is already open, no second set is opened.
$launchMutex = New-Object System.Threading.Mutex($false, 'Local\FlagMachineLauncher')
$haveLaunch = $launchMutex.WaitOne(0)
if (-not $haveLaunch) {
    Write-Host "Another launch is already opening the app windows - not opening duplicates." -ForegroundColor Yellow
}

if ($haveLaunch -and (Test-AppUp)) {
    if (Test-AppWindowsOpen) {
        Write-Host "App windows are already open - not opening duplicates." -ForegroundColor Yellow
        $haveLaunch = $false
    } else {
        Write-Host "App is up - opening the race-day windows (RO + stations as tabs in one new Brave window, display in its own window)." -ForegroundColor Green
        # RO control + Station 1 + Station 2 as TABS in ONE NEW window of the
        # browser = one own taskbar button; Ctrl+Tab switches between the pages
        Start-Process -FilePath $Browser -ArgumentList '--new-window "http://localhost:5000/" "http://localhost:5000/finishsheet?station=1" "http://localhost:5000/finishsheet?station=2"'
        Start-Sleep -Seconds 1
        # Display Board in its own SEPARATE window of the same browser (Brave):
        # own taskbar icon, outdoor screen
        Start-Process -FilePath $Browser -ArgumentList '--new-window "http://localhost:5000/display"'
    }
}
if ($haveLaunch) { $launchMutex.ReleaseMutex() }

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Race Officer Control: $BaseUrl" -ForegroundColor White
Write-Host "Finish Sheet 1:       $BaseUrl/finishsheet?station=1" -ForegroundColor White
Write-Host "Finish Sheet 2:       $BaseUrl/finishsheet?station=2" -ForegroundColor White
Write-Host "Display Board:        $BaseUrl/display" -ForegroundColor White
Write-Host "`nRO control + Station 1 + Station 2: tabs in ONE new Brave window (own" -ForegroundColor White
Write-Host "taskbar button); Display Board in its own separate Brave window. Tabs" -ForegroundColor White
Write-Host "stack and Ctrl+Tab switches pages; drag a tab out to split a station" -ForegroundColor White
Write-Host "onto a touch screen. To stop the app, close the Python window." -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

Read-Host "Press Enter to continue"
