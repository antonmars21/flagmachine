"""Verify the bug 31 fix: the RO page rebuilds its start sequence from the
server after navigating back from a finish sheet or refreshing.

Bug 31 (RO report 2026-10-27, found while human-testing bug 30): navigating
back to Race Officer Control worked (same tab, bug 30) but the page came up
EMPTY - every flag and setting was gone. Root cause: the start sequence
lives in app_state['sequence'] on the SERVER (the finish sheets keep their
class columns from it), but the RO page only ever PUSHED its drags to the
server - nothing rebuilt the grids from the server-rendered state, so any
page load started blank.

Fix: index.html renders window.INITIAL_SEQUENCE from app_state; app.js's
restoreSequenceFromServer() rebuilds the grids/rows (primary + secondary +
tertiary flags, labels, minutes, grid numbers) on DOMContentLoaded when the
page's own sequence is empty.
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b31.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

SEQUENCE = [
    {'id': 'row_1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': 'ilca7.png', 'tertiary_flag_image': None,
     'countdown_minutes': 1, 'status': 'PENDING', 'grid_index': 1,
     'current_remaining_seconds': 60},
    {'id': 'row_2', 'label': 'Pclass', 'flag_image': 'pclass.png',
     'secondary_flag_image': None, 'tertiary_flag_image': None,
     'countdown_minutes': 1, 'status': 'PENDING', 'grid_index': 2,
     'current_remaining_seconds': 60},
]

# --- 1. the page embeds the server's live sequence ---
m.app_state['sequence'] = [dict(item) for item in SEQUENCE]
resp = client.get('/')
assert resp.status_code == 200
html = resp.get_data(as_text=True)
match = re.search(r'window\.INITIAL_SEQUENCE = (\[.*?\]);', html, re.DOTALL)
assert match, 'index.html does not embed window.INITIAL_SEQUENCE'
embedded = json.loads(match.group(1))
assert [it['id'] for it in embedded] == ['row_1', 'row_2'], embedded
assert embedded[0]['secondary_flag_image'] == 'ilca7.png', embedded
assert embedded[1]['grid_index'] == 2, embedded
print('RO page embeds the live server sequence (rows, flags, grids)')

# --- 2. empty sequence embeds [] (restore is a no-op on a fresh session) ---
m.app_state['sequence'] = []
resp = client.get('/')
html = resp.get_data(as_text=True)
match = re.search(r'window\.INITIAL_SEQUENCE = (\[.*?\]);', html, re.DOTALL)
assert match and json.loads(match.group(1)) == [], 'empty sequence must embed []'
print('fresh session embeds [] - restore stays a no-op')

# --- 3. app.js restores the sequence on page load ---
with open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8') as f:
    js = f.read()
assert 'function restoreSequenceFromServer()' in js, 'restore function missing'
assert 'window.INITIAL_SEQUENCE' in js, 'restore does not read the embedded sequence'
assert 'restoreSequenceFromServer();' in js, 'restore function is never called'
dom_ready = js[js.index("document.addEventListener('DOMContentLoaded'"):]
assert 'restoreSequenceFromServer();' in dom_ready.split('\n\n')[0] or \
       dom_ready.index('restoreSequenceFromServer();') < 200, \
    'restore must run at page load, before other setup'
# The restore must rebuild secondary/tertiary flag boxes too (max 3 flags)
assert 'secondary_flag_image' in js[js.index('function restoreSequenceFromServer'):js.index('function restoreSequenceFromServer') + 3000], \
    'restore must repaint the secondary flag box'
assert 'tertiary_flag_image' in js[js.index('function restoreSequenceFromServer'):js.index('function restoreSequenceFromServer') + 3000], \
    'restore must repaint the tertiary flag box'
print('app.js rebuilds grids + rows (+2nd/3rd flags) from the embedded sequence on load')

# --- 4. countdown resume: the server remembers when Start was pressed ---
# (RO report: going back to RO control reset the timers and stopped the clock)
import time as _time
started_ms = int(_time.time() * 1000) - 60000  # Start was pressed 60s ago
r = client.post('/execute-control', json={'action': 'START', 'countdown_started_ms': started_ms})
assert r.status_code == 200
data = client.get('/api/race-status').get_json()
assert data['fm_status'] == 'RUNNING'
assert data['fm_countdown_started_ms'] == started_ms, data['fm_countdown_started_ms']
print('execute-control START stores countdown_started_ms; race-status carries it')

# STOP / RESET / END_RACE clear it (nothing to resume afterwards)
for action in ('STOP', 'RESET'):
    client.post('/execute-control', json={'action': action})
    data = client.get('/api/race-status').get_json()
    assert data['fm_countdown_started_ms'] is None, f'{action} must clear the countdown start'
print('STOP + RESET clear the countdown start (no stale resume)')

# --- 5. class starts backdate when catching up (page away at flag-down) ---
client.post('/update-sequence', json={'sequence': [
    {'id': 'row_1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': None, 'grid_index': 1, 'countdown_minutes': 1},
]})
client.post('/api/reset-finish-sheet')  # clean race state for a fresh race
m.app_state['race_id'] = None
m.app_state['class_start_times'] = {}
m.app_state['open_start_time'] = None
m.app_state['status'] = 'RUNNING'
m.app_state['fm_countdown_started_ms'] = started_ms
crossing_ms = started_ms + 30000  # the row was scheduled to end 30s after Start
r = client.post('/api/class-start',
                json={'flag_images': ['ilca6.png'], 'sequence_number': 1,
                      'started_at_ms': crossing_ms})
assert r.status_code == 200, r.get_data(as_text=True)
import sqlite3
from datetime import datetime
conn = sqlite3.connect(SCRATCH)
conn.row_factory = sqlite3.Row
race_id = conn.execute("SELECT MAX(race_id) FROM races").fetchone()[0]
row = conn.execute('''SELECT rcs.start_time FROM race_class_starts rcs
                      JOIN boat_classes bc ON bc.class_id = rcs.class_id
                      WHERE rcs.race_id = ? AND bc.flag_image = 'ilca6.png' ''',
                   (race_id,)).fetchone()
assert row, 'class start not recorded'
recorded = datetime.fromisoformat(row['start_time'])
expected = datetime.fromtimestamp(crossing_ms / 1000)
delta = abs((recorded - expected).total_seconds())
assert delta < 2, f'backdated start time off by {delta:.1f}s (got {row["start_time"]})'
print('class-start backdates to the TRUE crossing time when catching up')
# Idempotent: re-firing with a different time keeps the FIRST start
r = client.post('/api/class-start',
                json={'flag_images': ['ilca6.png'], 'sequence_number': 1,
                      'started_at_ms': crossing_ms + 999999})
row2 = conn.execute('''SELECT rcs.start_time FROM race_class_starts rcs
                       JOIN boat_classes bc ON bc.class_id = rcs.class_id
                       WHERE rcs.race_id = ? AND bc.flag_image = 'ilca6.png' ''',
                    (race_id,)).fetchone()
assert row2['start_time'] == row['start_time'], 're-fired start must not change the recorded time'
conn.close()
print('re-fired class start is ignored (first trigger wins - no duplicates)')

# --- 6. app.js resumes the clock and catches up silently ---
with open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8') as f:
    js = f.read()
assert 'countdown_started_ms: state.raceStartTime' in js, 'Start does not report when it was pressed'
assert 'data.fm_countdown_started_ms' in js and 'state.catchUpTick = true' in js, \
    'poller does not resume the countdown'
assert 'started_at_ms: state.raceStartTime + end * 1000' in js, \
    'class-start POST does not carry the true crossing time'
assert 'if (!catchUp) cueHorn();' in js and 'if (!catchUp) playFlagChangeCue(r, tot);' in js, \
    'catch-up tick must not blast horns/announcements'
assert 'state.catchUpTick = false;' in js, 'catch-up flag never cleared'
print('app.js resumes from the server timestamp, backdates starts, catches up silently')

os.remove(SCRATCH)
print()
print('PASS bug 31: RO page keeps its flags and settings across navigation/refresh'
      ' AND resumes a running countdown from the real elapsed time'
      ' (browser test: Start the countdown, open Finish Sheet 1, click'
      ' "Race Officer Control" - the clock must still be ticking at the right'
      ' remaining time, no reset)')
