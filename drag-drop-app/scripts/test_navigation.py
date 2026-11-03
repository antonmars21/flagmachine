"""Verify the bug 32/34 fix: NO page-to-page navigation buttons at all.

Bug 32 + 34 (RO report 2026-10-28): navigating from RO control to a finish
station replaced the RO page (the bug-30 same-tab fix moved the RO window onto
the station page, so the RO control - and its countdown, horn and voice -
was gone until the operator navigated back). Bugs 31's resume made the data
survive, but the RO screen still must not move.

Fix (kanban "Fix screen navigation" card, requirements updated 2026-11-03):
REGULAR browser windows in Brave - not --app mode, so tabs work inside every
window (Ctrl+Tab, back/forward). Final design (2026-11-03):
- START.bat / START.ps1 open RO control, Finish Sheet 1 and Finish Sheet 2
  as TABS in ONE NEW Brave window (--new-window with all three URLs; Brave is
  the default browser, Edge is the fallback) - the pages stack as tabs
  instead of floating windows covering each other, and the window gets its
  own taskbar button (the taskbar is the navigator, as in the earlier
  version); drag a tab out to split a station onto a touch screen;
- the Display Board opens in its own SEPARATE window of the same browser
  (Brave) for the outdoor screen;
- the work-page navigation buttons stay removed: the RO page has NO
  navigation links at all (the launchers open every page - the Display Board
  link was removed because it opened a second display next to the launcher's
  own display window); finish sheets have no 'Race Officer Control' back
  button;
- both launchers take a launch lock and check for already-open app windows
  (ALL visible windows, via scripts/check_app_windows.ps1) before launching,
  so a relaunch/double-click never opens a duplicate RO or display page.
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import app as m
m.recording_state['active'] = False
client = m.app.test_client()

LINK_RE = re.compile(r'<a\s[^>]*>', re.IGNORECASE)


def links(html):
    return [t.group(0) for t in LINK_RE.finditer(html)]


# RO control page: NO finish-sheet buttons any more - the RO window must never
# navigate away. The Display Board link may stay (new tab, separate screen).
resp = client.get('/')
assert resp.status_code == 200, f'/ rendered {resp.status_code}'
html = resp.get_data(as_text=True)
assert '/finishsheet' not in html, \
    'RO page still links to a finish sheet - the RO window can be navigated away'
for tag in links(html):
    href = re.search(r'href="([^"]*)"', tag)
    assert not href or not href.group(1).startswith('/'), \
        f'RO page must have no navigation links (the launcher opens every page): {tag.strip()}'
assert 'href="/display"' not in html, \
    'RO page must not link to /display - the launcher opens it in its own window ("display opens twice")'
print('RO page: no navigation links - the launcher opens every page in its own window/tab')

# Both finish sheets: no 'Race Officer Control' back button, no links to /
for station in (1, 2):
    resp = client.get(f'/finishsheet?station={station}')
    assert resp.status_code == 200, f'finish sheet {station} rendered {resp.status_code}'
    html = resp.get_data(as_text=True)
    work_links = [t.strip() for t in links(html)
                  if re.search(r'href="/"\s', t) or 'finishsheet?station=' in t]
    assert not work_links, \
        f'finish sheet {station}: work-page navigation links must not exist: {work_links}'
    for tag in links(html):
        assert 'target=' not in tag, \
            f'finish sheet {station}: new-tab link not allowed: {tag.strip()}'
    print(f'finish sheet {station}: no work-page navigation links')

# Display board: no work-page navigation at all (unchanged)
resp = client.get('/display')
assert resp.status_code == 200
html = resp.get_data(as_text=True)
assert '/finishsheet' not in html and not re.search(r'href="/"', html), \
    'display board must not link back to work pages'
print('display board: no work-page navigation links')

# START.bat is the navigation mechanism (kanban "Fix screen navigation",
# updated 2026-11-03): regular browser windows, not --app mode. RO control,
# Station 1 and Station 2 must start as TABS in ONE NEW Brave window (a single
# --new-window launch line carrying all three URLs) so the pages stack as tabs
# (Ctrl+Tab) instead of floating windows covering each other and the window
# gets its own taskbar button; the Display Board opens in its own SEPARATE
# window of the same browser (Brave). An accidental edit once dropped
# --new-window from the station lines and the pages merged into an existing
# window as tabs.
with open('START.bat', encoding='utf-8', errors='replace') as f:
    bat = f.read()
WORK_URLS = ('http://localhost:5000/"',
             'http://localhost:5000/finishsheet?station=1',
             'http://localhost:5000/finishsheet?station=2')
DISPLAY_URL = 'http://localhost:5000/display'
for url in WORK_URLS + (DISPLAY_URL,):
    assert url in bat, f'START.bat must open {url}'
launch_lines = [l for l in bat.splitlines() if '--new-window' in l and '"%BROWSER%"' in l]
assert len(launch_lines) == 2, \
    f'START.bat must have exactly two "%BROWSER%" --new-window launches (work tabs + display): {launch_lines}'
tabs_line = next((l for l in launch_lines if all(u in l for u in WORK_URLS)), '')
assert tabs_line, \
    'START.bat must open RO + station 1 + station 2 as TABS in ONE --new-window line'
assert any(DISPLAY_URL in l for l in launch_lines), \
    'START.bat must open /display in its own --new-window (separate window, same browser)'
assert 'set "BROWSER=%BRAVE%"' in bat, 'START.bat: browser must be Brave when installed'
assert '--app=' not in bat, 'START.bat must NOT use --app mode (kanban: regular tabs)'
print('START.bat: RO + stations as tabs in one new Brave window, display in its own Brave window')

# Browser preference: Brave for the work pages (default browser on the club
# machines), Edge for the display board; no Chrome launch path any more.
brave_pos = bat.find('BraveSoftware')
edge_pos = bat.find('Microsoft\\Edge')
assert brave_pos != -1, 'START.bat must look for Brave'
assert edge_pos != -1, 'START.bat must look for Edge'
assert brave_pos < edge_pos, 'START.bat must check Brave before Edge'
assert 'chrome.exe' not in bat.lower(), 'START.bat should not launch Chrome any more'
print('START.bat: browser = Brave if installed, else Edge (fallback for all pages)')

# Single-instance guard: relaunching must never start a SECOND server. The
# already-running check (urlopen) must appear BEFORE the server start line.
guard_pos = bat.find('urllib.request.urlopen')
start_pos = bat.find('cmd /k "cd /d')
assert 0 < guard_pos < start_pos, \
    'START.bat must check whether the app is already running BEFORE starting Flask'
assert 'ALREADY RUNNING' in bat and 'goto SERVER_UP' in bat, \
    'START.bat already-running path must reuse the server and open the windows'
print('START.bat: single-instance guard - relaunch reuses the running server')

# START.ps1 must launch the SAME layout as START.bat: RO + stations as TABS
# in ONE new Brave window (--new-window), display in its own separate window
# of the same browser, no --app mode.
with open('START.ps1', encoding='utf-8', errors='replace') as f:
    ps1 = f.read()
WORK_URLS_PS1 = ('"http://localhost:5000/"',
                 'http://localhost:5000/finishsheet?station=1',
                 'http://localhost:5000/finishsheet?station=2')
DISPLAY_URL_PS1 = 'http://localhost:5000/display'
for url in ('http://localhost:5000/',) + WORK_URLS_PS1[1:] + (DISPLAY_URL_PS1,):
    assert url in ps1, f'START.ps1 must open {url}'
launch_lines = [l for l in ps1.splitlines() if '--new-window' in l and '$Browser' in l]
assert len(launch_lines) == 2, \
    f'START.ps1 must have exactly two $Browser --new-window launches (work tabs + display): {launch_lines}'
tabs_line = next((l for l in launch_lines if all(u in l for u in WORK_URLS_PS1)), '')
assert tabs_line, \
    'START.ps1 must open RO + station 1 + station 2 as TABS in ONE --new-window line'
assert any(DISPLAY_URL_PS1 in l for l in launch_lines), \
    'START.ps1 must open /display in its own --new-window (separate window, same browser)'
assert '$Browser = if ($Brave) { $Brave } else { $Edge }' in ps1, \
    'START.ps1: browser must be Brave when installed'
assert '--app=' not in ps1, \
    'START.ps1 must NOT use --app mode (kanban: regular tabs)'
assert 'ALREADY RUNNING' in ps1, 'START.ps1 must reuse an already-running server'
brave_pos = ps1.find('BraveSoftware')
edge_pos = ps1.find('Microsoft\\Edge')
assert brave_pos != -1 and edge_pos != -1 and brave_pos < edge_pos, \
    'START.ps1 must check Brave before Edge'
assert 'chrome.exe' not in ps1.lower(), 'START.ps1 should not launch Chrome any more'
print('START.ps1: RO + stations as tabs in one new Brave window, display in its own Brave window')

# Duplicate-window guard (bug report "RO page opened twice"): both launchers
# must take a launch lock AND check for already-open app windows BEFORE any
# --new-window launch, so a relaunch or a double-click on the shortcut cannot
# open the RO page twice.
TITLE_PAT = 'Race Officer Control|Finish sheet|Outdoor Display'
first_nw_bat = bat.find('--new-window')
assert first_nw_bat != -1
assert 'flagmachine_launch.lock' in bat, 'START.bat must use a launch lock file'
assert 'tasklist /FI "PID eq' in bat, 'START.bat lock must verify the holder PID is alive'
assert 'powershell -NoProfile -File "%APP_DIR%\\scripts\\check_app_windows.ps1"' in bat, \
    'START.bat must call the all-windows app-window check helper (via call :CHECK_WINDOWS)'
with open('scripts/check_app_windows.ps1', encoding='utf-8', errors='replace') as f:
    chk = f.read()
assert TITLE_PAT in chk, 'check_app_windows.ps1 must match the app page window titles'
assert 'EnumWindows' in chk, \
    'check_app_windows.ps1 must enumerate ALL visible windows, not just each process main window'
for call in ('call :CHECK_LOCK', 'call :TAKE_LOCK', 'call :CHECK_WINDOWS'):
    assert call in bat and bat.find(call) < first_nw_bat, \
        f'START.bat must run {call} before launching windows'
assert 'not opening duplicates' in bat
first_nw_ps1 = ps1.find('--new-window')
assert first_nw_ps1 != -1
assert 'FlagMachineLauncher' in ps1 and ps1.find('FlagMachineLauncher') < first_nw_ps1, \
    'START.ps1 must take the launch mutex before launching'
assert TITLE_PAT in ps1 and ps1.find(TITLE_PAT) < first_nw_ps1, \
    'START.ps1 must check for already-open app windows before launching'
assert 'not opening duplicates' in ps1
print('both launchers: launch lock + duplicate-window guard before any --new-window launch')

# Desktop launcher: the shortcut script must exist and point at START.bat,
# and the shortcut icon (app.ico) must be a valid PNG-in-ICO.
assert os.path.exists('scripts/make_desktop_shortcut.bat'), \
    'scripts/make_desktop_shortcut.bat missing (desktop launcher installer)'
ico = open('static/icons/app.ico', 'rb').read()
assert struct.unpack('<HHH', ico[:6]) == (0, 1, 1), 'app.ico header invalid'
w, h, colors, r, planes, bits, size, off = struct.unpack('<BBBBHHII', ico[6:22])
assert ico[off:off + 8] == b'\x89PNG\r\n\x1a\n', 'app.ico must contain a PNG entry'
print('desktop launcher: shortcut installer + app.ico (PNG-in-ICO) valid')

# Taskbar navigator (bug 32/34 follow-up): each window's favicon is its
# taskbar/window icon, so all four pages must carry a DISTINCT icon link
# and the two finish sheets must differ by station.
def favicon_of(html):
    m = re.search(r'<link\s[^>]*rel="icon"[^>]*>', html, re.IGNORECASE)
    assert m, 'page has no favicon link'
    href = re.search(r'href="([^"]*)"', m.group(0))
    assert href, f'favicon link has no href: {m.group(0)}'
    return href.group(1)

ro_html = client.get('/').get_data(as_text=True)
icons = {'/': favicon_of(ro_html)}
for station in (1, 2):
    html = client.get(f'/finishsheet?station={station}').get_data(as_text=True)
    icons[f'/finishsheet?station={station}'] = favicon_of(html)
icons['/display'] = favicon_of(client.get('/display').get_data(as_text=True))
assert len(set(icons.values())) == 4, \
    f'all four windows need DISTINCT taskbar icons, got {icons}'
print('window icons distinct per page:', icons)

# every referenced icon must be a real, served PNG
for href in icons.values():
    filename = href.rsplit('/', 1)[-1]
    path = os.path.join('static', 'icons', filename)
    assert os.path.exists(path), f'icon file missing: {path}'
    with open(path, 'rb') as f:
        assert f.read(8) == b'\x89PNG\r\n\x1a\n', f'not a PNG: {path}'
    resp = client.get(href if href.startswith('/') else '/' + href)
    assert resp.status_code == 200, f'{href} does not serve (HTTP {resp.status_code})'
print('all four icon PNGs exist and serve over HTTP')

print('ALL NAVIGATION CHECKS PASS')
