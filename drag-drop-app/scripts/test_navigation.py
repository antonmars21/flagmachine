"""Verify the bug 30 fix: page navigation goes to exactly ONE destination -
the current tab - so stations never spawn duplicate browser sessions.

Bug 30 (RO report 2026-10-27): the Finish Sheet 1 / Finish Sheet 2 buttons on
the RO control page used target="_blank", so every click opened a NEW browser
tab - a fresh, blank finish-sheet session (the station id lives per tab in
sessionStorage) that then fought the real stations over lap/finish captures.
Combined with the finish sheet's Race Officer Control button, the RO kept
landing in new sessions instead of returning to the one real control page.

Rules now checked on every rendered page:
- the station buttons (RO page) have NO target attribute -> same tab;
- the Race Officer Control button (finish sheets) has NO target attribute;
- the Display Board link is the ONLY allowed new-tab link (it exists to run
  on the separate outdoor screen - it is not navigation between work pages).
"""
import re
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import app as m
m.recording_state['active'] = False
client = m.app.test_client()

LINK_RE = re.compile(r'<a\s[^>]*>', re.IGNORECASE)


def links(html):
    return [m.group(0) for m in LINK_RE.finditer(html)]


def check_page(path, allow_new_tabs):
    resp = client.get(path)
    assert resp.status_code == 200, f'{path} rendered {resp.status_code}'
    html = resp.get_data(as_text=True)
    bad = []
    for tag in links(html):
        href = re.search(r'href="([^"]*)"', tag)
        if not href:
            continue
        if 'target="_blank"' in tag:
            # new-tab links are only allowed on the allowlist (per page)
            if href.group(1) not in allow_new_tabs:
                bad.append(tag.strip())
    assert not bad, f'{path}: navigation links must stay in the same tab: {bad}'
    return html


# RO control page: station buttons navigate THIS tab; Display Board may open
# a new tab (separate outdoor screen - documented feature, not navigation)
html = check_page('/', {'/display'})
assert '/finishsheet?station=1' in html and '/finishsheet?station=2' in html
station_links = [t for t in links(html) if 'finishsheet?station=' in t]
assert len(station_links) == 2, f'expected the 2 station buttons, got {station_links}'
for tag in station_links:
    assert 'target=' not in tag, f'station button still opens a new tab: {tag.strip()}'
print('RO page: Finish Sheet 1 + 2 buttons navigate this tab (no new-tab sessions)')

# Both finish sheets: the Race Officer Control button navigates THIS tab back
# to the control page - one destination, no extra sessions
for station in (1, 2):
    html = check_page(f'/finishsheet?station={station}', set())
    ro_links = [t for t in links(html) if re.search(r'href="/[^f]', t)]
    assert ro_links, f'finish sheet {station}: Race Officer Control link missing'
    for tag in ro_links:
        assert 'target=' not in tag, f'RO control link opens a new tab: {tag.strip()}'
    print(f'finish sheet {station}: Race Officer Control navigates this tab')

# Display board: no work-page navigation at all (no links to / or /finishsheet)
resp = client.get('/display')
assert resp.status_code == 200
html = resp.get_data(as_text=True)
assert '/finishsheet' not in html and not re.search(r'href="/"', html), \
    'display board must not link back to work pages'
print('display board: no work-page navigation links')

print()
print('PASS bug 30: one button, one destination - station + RO navigation stay in the tab')
