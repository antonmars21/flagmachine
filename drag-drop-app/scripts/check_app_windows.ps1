# check_app_windows.ps1 - exit code 0 if any Flag Machine app page window is
# already open, 1 otherwise.
#
# Enumerates ALL visible top-level windows (user32 EnumWindows), not just each
# browser process's main window: Get-Process MainWindowTitle only sees one
# window per process, so a relaunch could miss an already-open Display Board
# window and open it a second time ("display opens twice"). Pure stdlib/P-Invoke,
# no new requirements.
#
# Page titles (templates/*.html <title>):
#   Flag Machine - Race Officer Control Panel
#   Finish sheet <n>
#   Flag Machine - Outdoor Display
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

if ($script:found) { exit 0 } else { exit 1 }
