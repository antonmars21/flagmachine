"""Kanban "desktop icon" (small fix, for the Dell): the "Flag Machine" desktop
shortcut existed only on the Windows laptop (created manually 2026-10-29 via
scripts/make_desktop_shortcut.bat). The Dell had no desktop icon.

Fix (2026-11-05): both launchers now ENSURE the shortcut on every run -
START.bat calls scripts\\make_desktop_shortcut.bat /q when
%USERPROFILE%\\Desktop\\Flag Machine.lnk is missing, and START.ps1 creates the
.lnk inline via WScript.Shell under the same condition. The first START.bat run
on the Dell therefore creates the desktop icon automatically, pointing at that
machine's own START.bat (make_desktop_shortcut.bat resolves APP_DIR from its own
location) with the app.ico pennant icon. make_desktop_shortcut.bat gained a /q
quiet mode (no pause / no closing timeout) so the launcher is not held up, while
running it by hand still shows the instructions.
"""

import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

with open('START.bat', encoding='utf-8') as f:
    bat = f.read()
with open('START.ps1', encoding='utf-8') as f:
    ps1 = f.read()
with open('scripts/make_desktop_shortcut.bat', encoding='utf-8') as f:
    mk = f.read()

# --- 1. START.bat creates the desktop shortcut when missing, BEFORE launching ---
assert 'if not exist "%USERPROFILE%\\Desktop\\Flag Machine.lnk"' in bat, \
    'START.bat must check for the missing desktop shortcut'
assert 'make_desktop_shortcut.bat" /q' in bat, \
    'START.bat must call the shortcut installer in quiet mode'
server_start = bat.index('start "Flag Machine - http://localhost:5000"')
shortcut_pos = bat.index('Flag Machine.lnk')
assert shortcut_pos < server_start, \
    'the desktop icon must be ensured before the server/windows are launched'
print('PASS: START.bat ensures the desktop icon on first run, before launching')

# --- 2. START.ps1 creates the .lnk inline when missing, BEFORE launching ---
assert "'Flag Machine.lnk'" in ps1 and 'CreateShortcut' in ps1, \
    'START.ps1 must create the desktop shortcut inline'
assert '$lnk.TargetPath = "$AppDir\\START.bat"' in ps1, \
    'the shortcut must point at this machine\'s START.bat'
assert 'app.ico' in ps1, 'the shortcut must use the app icon'
ps1_launch = ps1.index('Start-Process -FilePath $pythonPath')
ps1_shortcut = ps1.index('Flag Machine.lnk')
assert ps1_shortcut < ps1_launch, \
    'the desktop icon must be ensured before the app is started'
print('PASS: START.ps1 ensures the desktop icon on first run, before launching')

# --- 3. the installer still works standalone and supports /q ---
assert 'for %%i in ("%~dp0..") do set "APP_DIR=%%~fi"' in mk, \
    'installer must resolve APP_DIR from its own location (correct on the Dell)'
assert "$lnk.TargetPath = '%APP_DIR%\\START.bat'" in mk
assert 'app.ico' in mk
assert 'if /i "%~1"=="/q" set "QUIET=1"' in mk, 'installer must support /q'
assert mk.count('if "%QUIET%"=="0" pause') == 3, 'all 3 interactive pauses must be quiet-gated'
assert 'if "%QUIET%"=="0" (' in mk and 'timeout /t 3' in mk, \
    'the closing timeout must be quiet-gated'
print('PASS: make_desktop_shortcut.bat /q quiet mode, standalone behaviour intact')

# --- 4. the icon file itself is valid (PNG-in-ICO, as test_navigation checks) ---
assert os.path.exists('scripts/make_desktop_shortcut.bat')
with open('static/icons/app.ico', 'rb') as f:
    ico = f.read()
assert struct.unpack('<HHH', ico[:6]) == (0, 1, 1), 'app.ico header invalid'
off = 6 + 16
assert ico[off:off + 8] == b'\x89PNG\r\n\x1a\n', 'app.ico must contain a PNG entry'
print('PASS: app.ico present and valid')

print('\nPASS kanban "desktop icon": first START.bat/START.ps1 run on any machine (incl. the Dell) creates the Flag Machine desktop shortcut')
