"""Kanban "Master time clock not working": the RO wants to OPTIONALLY set the
race to start at a fixed time (e.g. 10:45) - the pre-rewrite app.js auto-started
the sequence when the system clock hit the Master Start Time (HH:MM), but the
Session-5 rewrite of app.js dropped that check: updateClock() only painted the
clock and the master-start-input only stored a local value (never even pushed
to the server).

Fix (2026-11-05):
- index.html gains an "Auto-start" checkbox next to the Master Start Time input,
  rendered from app_state['master_start_auto'].
- app.py: app_state['master_start_auto'] + /update-settings accepts
  master_start_time AND master_start_auto so both survive reloads/restarts.
- app.js: the Start button body is extracted into startCountdown() (button and
  auto-start share it); updateClock() (1s tick) fires startCountdown() when
  Auto-start is on, a time is set, the sequence is non-empty, the shared state
  is READY and no countdown is running, and the clock's HH:MM equals the master
  start time - at most once per clock minute (lastAutoStartKey guard).
  Both inputs POST to /update-settings on change.

This test covers the server side end-to-end plus the app.js wiring (the auto
fire itself is client-side clock logic; asserted structurally, as in
test_ro_restore.py).
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import app as m
m.recording_state['active'] = False
client = m.app.test_client()

# --- 1. /update-settings accepts and stores both settings ---
r = client.post('/update-settings', json={'master_start_time': '22:45'})
assert r.status_code == 200, r.get_data(as_text=True)
assert r.get_json()['master_start_time'] == '22:45', r.get_json()
assert m.app_state['master_start_time'] == '22:45'

r = client.post('/update-settings', json={'master_start_auto': True})
assert r.status_code == 200, r.get_data(as_text=True)
assert r.get_json()['master_start_auto'] is True, r.get_json()
assert m.app_state['master_start_auto'] is True

r = client.post('/update-settings', json={'master_start_time': '10:45', 'master_start_auto': True})
assert r.status_code == 200 and r.get_json()['master_start_time'] == '10:45'
print('PASS: /update-settings stores master_start_time + master_start_auto')

# --- 2. the RO page renders the stored time and the auto-start checkbox ---
html = client.get('/').get_data(as_text=True)
assert 'id="master-start-input"' in html
assert 'value="10:45"' in html, 'master start time not rendered from app_state'
assert 'id="master-start-auto"' in html, 'auto-start checkbox missing'
assert re.search(r'id="master-start-auto"[^>]*checked', html), \
    'auto-start checkbox must render checked when master_start_auto is on'
# 2026-11-05 RO feedback: the checkbox sits UNDER the time input (stacked
# grid cell), not inline, to save header space
assert 'class="input-group master-start"' in html, 'master start group must use the stacked layout'
assert 'class="auto-start-cell"' in html, 'auto-start checkbox must be in the under-the-time cell'
with open(os.path.join(ROOT, 'static', 'css', 'style.css'), encoding='utf-8') as f:
    css = f.read()
assert '.input-group.master-start' in css and 'grid-column: 2' in css, \
    'style.css must stack the auto-start cell under the time input'
print('PASS: RO page renders master start time + auto-start checkbox stacked under the time')

# off state renders unchecked
m.app_state['master_start_auto'] = False
html = client.get('/').get_data(as_text=True)
assert not re.search(r'id="master-start-auto"[^>]*checked', html)
m.app_state['master_start_auto'] = True
m.app_state['master_start_time'] = '11:30'
print('PASS: auto-start checkbox reflects off state too')

# --- 3. app.js wiring: shared startCountdown + auto-fire in the 1s clock tick ---
with open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8') as f:
    js = f.read()

assert 'function startCountdown()' in js, 'startCountdown() missing'
assert "addEventListener('click', startCountdown)" in js, \
    'Start button must call startCountdown'
assert "action: 'START', countdown_started_ms: state.raceStartTime" in js, \
    'startCountdown must still report the countdown start (bug 31 resume)'

assert 'function updateClock()' in js
clock = js[js.index('function updateClock()'):]
clock = clock[:clock.index('\n}\n')]
assert 'state.masterStartAuto' in clock, 'clock tick does not check the auto-start flag'
assert 'state.masterStartTime' in clock and '`${hh}:${mm}` === state.masterStartTime' in clock, \
    'clock tick does not compare HH:MM against the master start time'
assert 'lastAutoStartKey' in clock and 'startCountdown();' in clock, \
    'auto-start must fire startCountdown() once per clock minute'
assert 'setInterval(updateClock, 1000)' in js, 'the 1s clock tick must still run'
assert '!state.isRunning && !state.raceStartTime' in clock, \
    'auto-start must not fire while a countdown is running/paused'
assert "lastSyncedStatus === 'READY'" in clock, 'auto-start must only fire in READY state'
print('PASS: app.js updateClock auto-starts via startCountdown() (READY, once/minute)')

# --- 4. the inputs persist to the server on change ---
assert "body: JSON.stringify({ master_start_time: state.masterStartTime })" in js, \
    'time input change must POST /update-settings'
assert "body: JSON.stringify({ master_start_auto: state.masterStartAuto })" in js, \
    'auto checkbox change must POST /update-settings'
assert "masterStartInput.value) state.masterStartTime = masterStartInput.value" in js, \
    'state must initialise from the rendered input, not a hardcoded default'
print('PASS: app.js persists master start time + auto flag via /update-settings')

# --- 5. JS still parses (brace/paren balance, no duplicate const) ---
assert js.count('{') == js.count('}'), 'app.js brace imbalance'
assert js.count('(') == js.count(')'), 'app.js paren imbalance'
# top-level consts only - a duplicate there is a fatal SyntaxError (bug-25 hotfix)
decls = re.findall(r'^const\s+(\w+)', js, re.MULTILINE)
assert len(decls) == len(set(decls)), f'duplicate top-level const declarations: {decls}'
print('PASS: app.js balanced, no duplicate consts')

print('\nPASS kanban "Master time clock": auto-start restored (opt-in), persisted, shared with the Start button')
