"""Verify the bug 32/34 fix: NO page-to-page navigation buttons at all.

Bug 32 + 34 (RO report 2026-10-28): navigating from RO control to a finish
station replaced the RO page (the bug-30 same-tab fix moved the RO window onto
the station page, so the RO control - and its countdown, horn and voice -
was gone until the operator navigated back). Bugs 31's resume made the data
survive, but the RO screen still must not move.

Fix (agreed direction): each page opens in its OWN application window via
START.bat (Chrome/Edge --app mode: no tabs, no back/forward buttons), and the
work-page navigation buttons are removed entirely:
- RO page: no Finish Sheet 1/2 buttons (only the Display Board link, which
  opens a new tab BY DESIGN for the separate outdoor screen);
- finish sheets: no 'Race Officer Control' back button;
- START.bat itself opens all four pages as separate app windows once the
  server answers.
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
    if not href:
        continue
    if 'target="_blank"' in tag:
        assert href.group(1) == '/display', \
            f'RO page: unexpected new-tab link: {tag.strip()}'
print('RO page: no station buttons - the RO window cannot navigate away')

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

# START.bat is now the navigation mechanism: it must open all four pages as
# separate application windows (--app mode) after the server is up.
with open('START.bat', encoding='utf-8', errors='replace') as f:
    bat = f.read()
for url in ('http://localhost:5000/"',
            'http://localhost:5000/finishsheet?station=1',
            'http://localhost:5000/finishsheet?station=2',
            'http://localhost:5000/display'):
    assert f'--app="{url}' in bat or f'--app={url}' in bat, \
        f'START.bat must open {url} as an application window'
assert '--app' in bat, 'START.bat must use --app (application windows, not browser tabs)'
print('START.bat: opens RO control + both finish sheets + display board as app windows')

# Single-instance guard: relaunching must never start a SECOND server. The
# already-running check (urlopen) must appear BEFORE the server start line.
guard_pos = bat.find('urllib.request.urlopen')
start_pos = bat.find('cmd /k "cd /d')
assert 0 < guard_pos < start_pos, \
    'START.bat must check whether the app is already running BEFORE starting Flask'
assert 'ALREADY RUNNING' in bat and 'goto SERVER_UP' in bat, \
    'START.bat already-running path must reuse the server and open the windows'
print('START.bat: single-instance guard - relaunch reuses the running server')

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
