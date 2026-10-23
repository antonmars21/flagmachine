"""Regression test for bug 4 - End Race / Start buttons are ONE shared control:

- /api/race-status exposes fm_status (flag machine control state) and
  open_start_time, so every page can sync its Start/End buttons to the
  RO control state (part B: all start buttons obey the RO start button).
- Ending the race from ANY page (finish sheet's /api/end-race or the RO
  control /execute-control END_RACE) flips the status from RUNNING to
  ENDED everywhere: race_ended=true, races.status='ENDED', fm_status ENDED.
- End Race works even when no race record exists yet (RO countdown running,
  first class flag not fired): /execute-control END_RACE still stops the
  flag machine (fm_status ENDED) - that is what the finish sheet sends.
- After a reset, the state is READY again (start buttons re-enable).

Runs against a scratch copy of score.db - real DB untouched.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_sync.db'
shutil.copy('score.db', SCRATCH)
import app as app_module
app_module.DB_PATH = SCRATCH

client = app_module.app.test_client()

# --- race-status exposes the sync fields (bug 4 + bug 15 data) ---
st = client.get('/api/race-status').get_json()
assert 'fm_status' in st, 'fm_status missing from race-status'
assert 'open_start_time' in st, 'open_start_time missing from race-status'
assert 'class_start_times' in st and 'race_ended' in st
print('PASS: /api/race-status exposes fm_status / open_start_time / class_start_times')

# --- RO control START: all other pages must lock out their start buttons ---
r = client.post('/execute-control', json={'action': 'START'}).get_json()
assert r['current_state'] == 'RUNNING'
assert client.get('/api/race-status').get_json()['fm_status'] == 'RUNNING'
print('PASS: RO control START -> fm_status RUNNING (finish-sheet start buttons lock out)')

# --- End Race pressed on a FINISH SHEET before any class start fired ---
# (no race record yet: only /execute-control is sent by finishsheet.js)
r = client.post('/execute-control', json={'action': 'END_RACE'}).get_json()
assert r['current_state'] == 'ENDED'
st = client.get('/api/race-status').get_json()
assert st['fm_status'] == 'ENDED'
print('PASS: End Race with no race record stops the flag machine (fm_status ENDED)')

# --- reset back to READY, then a full race cycle ended from the finish sheet ---
assert client.post('/api/reset-race').get_json()['status'] == 'success'
assert client.get('/api/race-status').get_json()['fm_status'] == 'READY'

conn = sqlite3.connect(SCRATCH)
c = conn.cursor()
c.execute("INSERT INTO races (start_time, status) VALUES (?, 'RUNNING')",
          (datetime.now().isoformat(),))
race_id = c.lastrowid
c.execute("INSERT INTO race_sailors (race_id, uid, lap_count) VALUES (?, 'SL-1091', 0)", (race_id,))
conn.commit()
conn.close()
app_module.app_state['race_id'] = race_id

# --- manual backup: finish-sheet Start Race must set the shared state RUNNING
# (bug 4 regression 2026-10-23: it left fm_status READY, so the RO page showed
# READY while the race was live and the buttons looked out of sync)
r = client.post('/api/start-race', json={'selected_sailors': ['SL-1091']}).get_json()
assert r['status'] == 'success', r
st = client.get('/api/race-status').get_json()
assert st['fm_status'] == 'RUNNING', f'manual backup start must set fm_status RUNNING, got {st["fm_status"]!r}'
assert st['race_id'] == race_id, 'manual backup must reuse the active race'
print('PASS: finish-sheet Start Race (manual backup) -> fm_status RUNNING for every page')

# RO pressed START (flag machine running), race exists
client.post('/execute-control', json={'action': 'START'})
assert client.get('/api/race-status').get_json()['fm_status'] == 'RUNNING'

# ... and the finish sheet ends the race with the SAME two calls the RO page uses
r = client.post('/api/end-race').get_json()
assert r['status'] == 'success', r
st = client.get('/api/race-status').get_json()
assert st['race_ended'] is True, 'race_ended must be true after end-race'
assert st['fm_status'] == 'ENDED', 'fm_status must be ENDED after end-race'

conn = sqlite3.connect(SCRATCH)
row = conn.execute("SELECT status, end_time FROM races WHERE race_id = ?", (race_id,)).fetchone()
conn.close()
assert row[0] == 'ENDED', f'races.status must be ENDED, is {row[0]!r}'
assert row[1], 'races.end_time must be recorded'
print('PASS: End Race from a finish sheet -> RUNNING to ENDED for every page (DB row updated)')

# --- idempotent: ending again does not corrupt anything ---
assert client.post('/api/end-race').get_json()['status'] == 'success'
print('PASS: End Race is idempotent')

# --- reset: ready for the next race, start buttons re-enable ---
client.post('/api/reset-race')
st = client.get('/api/race-status').get_json()
assert st['fm_status'] == 'READY' and st['race_ended'] is False
print('PASS: reset returns the shared control state to READY')

print('ALL BUTTON-SYNC CHECKS PASS')
