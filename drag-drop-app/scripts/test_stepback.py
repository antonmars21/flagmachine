"""Verify Step Back (feature 4, Step 2): each station reverses only its OWN
most recent capture, with Restore as the safety net.

- undo-last {station}: reverses that station's latest lap or finish.
- Other stations' captures are never touched.
- restore-last {station}: re-applies the most recently undone capture with
  its ORIGINAL timestamp.
- 2s double-capture guard: same sailor lapped twice within 2s is rejected.
- Superseded finishes refuse to restore/undo (409).
- Validation: station required (1|2), race required.

Runs against a scratch copy of score.db - real DB untouched.
"""
import os
import shutil
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_stepback.db'
shutil.copy('score.db', SCRATCH)

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
conn.execute('DELETE FROM class_station_assignments')
# Sign on 3 Ilca 6 sailors
uids = [r[0] for r in conn.execute('''
    SELECT s.uid FROM sailors s
    JOIN boat_classes bc ON s.class_id = bc.class_id
    WHERE bc.flag_image = 'ilca6.png' ORDER BY s.seed LIMIT 3''').fetchall()]
assert len(uids) == 3, 'need 3 Ilca 6 sailors'
for uid in uids:
    conn.execute('UPDATE sailors SET racing_today = 1 WHERE uid = ?', (uid,))
conn.commit()
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# --- 1. No active race: step back refused
r = client.post('/api/undo-last', json={'station': 1})
assert r.status_code == 400, 'undo without a race must be refused'
print('PASS: step back refused when no race is active')

# Start the race via the class-start POST (auto-creates the race)
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'grid_index': 1, 'countdown_minutes': 1},
]})
client.post('/api/class-start', json={'flag_images': ['ilca6.png'], 'sequence_number': 1})
assert m.app_state.get('race_id'), 'race should be auto-created'
race_id = m.app_state['race_id']

def lap(uid, station):
    return client.post('/api/record-lap', json={'uid': uid, 'station': station})

def laps_of(uid):
    conn = sqlite3.connect(SCRATCH)
    conn.row_factory = sqlite3.Row
    row = conn.execute('''SELECT lap_count, finish_time FROM race_sailors
                          WHERE race_id = ? AND uid = ?''', (race_id, uid)).fetchone()
    conn.close()
    return row['lap_count'], row['finish_time']

# --- 2. Captures are logged per station
r = lap(uids[0], 1)
assert r.get_json()['lap_count'] == 1, r.get_json()
r = lap(uids[0], 2)   # other station lapped same sailor -> needs 2s gap
# (may legitimately hit the double-capture guard if <2s; sleep to be sure it is a real lap)
if r.status_code == 400:
    time.sleep(2.1)
    r = lap(uids[0], 2)
assert r.get_json()['lap_count'] == 2, r.get_json()
print('PASS: laps from both stations logged with their station')

# --- 3. Step Back on station 1 reverses ONLY station 1's lap
r = client.post('/api/undo-last', json={'station': 1})
d = r.get_json()
assert d['status'] == 'success' and d['action'] == 'lap' and d['lap_number'] == 1, d
assert laps_of(uids[0])[0] == 1, 'station 2 lap must remain'
conn = sqlite3.connect(SCRATCH)
rows = conn.execute('''SELECT station, undone FROM capture_actions
                       WHERE race_id = ? ORDER BY id''', (race_id,)).fetchall()
assert rows == [(1, 1), (2, 0)], rows   # stn1 undone, stn2 intact
conn.close()
print('PASS: step back reverses only the acting station\'s capture')

# --- 4. Station 1 has nothing left to step back; station 2 still does
r = client.post('/api/undo-last', json={'station': 1})
assert r.status_code == 404, 'station 1 must be out of actions'
r = client.post('/api/undo-last', json={'station': 2})
assert r.get_json()['status'] == 'success'
assert laps_of(uids[0]) == (0, None)
print('PASS: station isolation - each screen steps back only its own actions')

# --- 5. Restore re-applies with the ORIGINAL timestamp
r = client.post('/api/restore-last', json={'station': 2})
d = r.get_json()
assert d['status'] == 'success' and d['lap_number'] == 2, d
assert laps_of(uids[0])[0] == 1, 'restored lap must re-count (was 0 after both undos)'
conn = sqlite3.connect(SCRATCH)
ts = conn.execute('''SELECT timestamp FROM lap_records
                     WHERE race_id = ? AND uid = ? AND lap_number = 2''',
                  (race_id, uids[0])).fetchone()[0]
action_ts = conn.execute('''SELECT timestamp FROM capture_actions
                            WHERE race_id = ? AND uid = ? AND lap_number = 2''',
                         (race_id, uids[0])).fetchone()[0]
conn.close()
assert ts == action_ts, 'restore must keep the ORIGINAL timestamp'
print('PASS: restore re-applies the capture with its original timestamp')

# --- 6. Finish: undo clears it, restore brings it back
r = client.post('/api/mark-finish', json={'uid': uids[1], 'station': 1})
finish_ts = r.get_json()['finish_time']
assert laps_of(uids[1])[1] == finish_ts
r = client.post('/api/undo-last', json={'station': 1})
d = r.get_json()
assert d['status'] == 'success' and d['action'] == 'finish', d
assert laps_of(uids[1])[1] is None, 'finish must be cleared'
r = client.post('/api/restore-last', json={'station': 1})
assert r.get_json()['status'] == 'success'
assert laps_of(uids[1])[1] == finish_ts, 'finish restored with original time'
print('PASS: wrong-boat finish recovery - undo clears, restore brings back')

# --- 7. Superseded finish: undo, re-finish, then restore refused
r = client.post('/api/undo-last', json={'station': 1})
assert r.get_json()['status'] == 'success'
r = client.post('/api/mark-finish', json={'uid': uids[1], 'station': 2})
new_ts = r.get_json()['finish_time']
assert new_ts != finish_ts
r = client.post('/api/restore-last', json={'station': 1})
assert r.status_code == 409, 'restore of a superseded finish must be refused'
r = client.post('/api/undo-last', json={'station': 1})
assert r.status_code == 404, 'station 1 has nothing left (its finish is already undone)'
r = client.post('/api/undo-last', json={'station': 2})
assert r.get_json()['status'] == 'success', 'the LATER finish can be undone'
# Now the original finish can be restored (nothing supersedes it anymore)
r = client.post('/api/restore-last', json={'station': 1})
assert r.get_json()['status'] == 'success'
assert laps_of(uids[1])[1] == finish_ts, 'original finish restored after the later one is undone'
print('PASS: superseded finishes refuse restore (409); later finish undoable')

# --- 8. 2s double-capture guard
time.sleep(2.1)
r = lap(uids[2], 1)
assert r.get_json()['lap_count'] == 1
r = lap(uids[2], 1)   # immediate double tap
assert r.status_code == 400 and '2 seconds' in r.get_json()['message'], r.get_json()
assert laps_of(uids[2])[0] == 1, 'double tap must not count'
print('PASS: 2s double-capture guard blocks accidental double taps')

# --- 9. Validation
r = client.post('/api/undo-last', json={'station': 3})
assert r.status_code == 400
r = client.post('/api/undo-last', json={})
assert r.status_code == 400
# Station 1 still has the lap undone in section 3 - restoring it is valid
r = client.post('/api/restore-last', json={'station': 1})
assert r.get_json()['status'] == 'success' and r.get_json()['lap_number'] == 1
assert laps_of(uids[0])[0] == 2, 'both laps back after the full undo/restore chain'
print('PASS: validation (station required); earlier undone capture restorable')

# --- 10. sheet_version propagates changes to other stations
v = client.get('/api/race-status').get_json()['sheet_version']
assert isinstance(v, int) and v >= 2, v
print('PASS: race-status reports sheet_version for cross-station re-render')

os.remove(SCRATCH)
print()
print('PASS Step Back: per-station undo, restore with original time, guards, validation')
