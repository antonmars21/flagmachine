"""Verify the multi-station finish sheet class split (feature 4, Step 1):

- Default assignment: the first 3 columns on the sheet go to station 1,
  the remainder (including Open Category) to station 2.
- ?station=1 / ?station=2 return only that station's columns; no parameter
  returns all columns (unchanged legacy behaviour).
- Column-header toggle endpoint stores the assignment server-side, bumps
  assignments_version (visible in /api/race-status so other stations
  re-render), and keeps it for the whole day - across a full race cycle
  (class-start -> end-race -> reset-finish-sheet).
- New classes added to the sequence later default by position without
  disturbing stored toggles.
- Validation: bad station / missing class_key rejected.

Runs against a scratch copy of score.db - real DB untouched.
"""
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_stations.db'
shutil.copy('score.db', SCRATCH)

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
# Hermetic: clear any stored station toggles (live DB keeps them for the day)
conn.execute('DELETE FROM class_station_assignments')

def sign_on_class(flag_image, limit=2):
    """Sign on up to `limit` sailors of the class behind a flag image."""
    rows = conn.execute('''
        SELECT s.uid FROM sailors s
        JOIN boat_classes bc ON s.class_id = bc.class_id
        WHERE bc.flag_image = ? ORDER BY s.seed LIMIT ?''',
        (flag_image, limit)).fetchall()
    assert rows, 'no sailors found for flag ' + flag_image
    for (uid,) in rows:
        conn.execute('UPDATE sailors SET racing_today = 1 WHERE uid = ?', (uid,))
    return len(rows)

# Five classes on the course + one open-category sailor (class not in sequence)
n = {}
n['ilca6'] = sign_on_class('ilca6.png')
n['ilca7'] = sign_on_class('ilca7.png')
n['starling'] = sign_on_class('Starling.png')
n['optimist'] = sign_on_class('optimist.png')
n['zephyr'] = sign_on_class('Zephyr.png')
open_row = conn.execute('''
    SELECT s.uid FROM sailors s
    JOIN boat_classes bc ON s.class_id = bc.class_id
    WHERE bc.flag_image IS NULL OR bc.flag_image = ''
    ORDER BY s.seed LIMIT 1''').fetchone()
if not open_row:
    # Fall back to a class that will not be in the sequence (Frostbite flag is NULL)
    open_row = conn.execute('''
        SELECT s.uid FROM sailors s
        JOIN boat_classes bc ON s.class_id = bc.class_id
        WHERE bc.class_name = 'Frostbite' LIMIT 1''').fetchone()
assert open_row, 'no open-category sailor available for the test'
conn.execute('UPDATE sailors SET racing_today = 1 WHERE uid = ?', (open_row[0],))
conn.commit()
conn.close()
print('signed on: %s + 1 open sailor' % n)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# Sequence: Start 1 = Ilca 6 + Ilca 7, Start 2 = Starling + Optimist, Start 3 = Zephyr
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': 'ilca7.png', 'grid_index': 1, 'countdown_minutes': 1},
    {'id': 'r2', 'label': 'Start2', 'flag_image': 'Starling.png',
     'secondary_flag_image': 'optimist.png', 'grid_index': 2, 'countdown_minutes': 1},
    {'id': 'r3', 'label': 'Zephyr', 'flag_image': 'Zephyr.png',
     'grid_index': 3, 'countdown_minutes': 1},
]})

def columns_for(resp):
    data = resp.get_json()
    assert data['status'] == 'success', data
    return data, [c['class_name'] for c in data['columns']]

# --- 1. Default split: first 3 columns -> station 1, rest (incl. Open) -> 2
data, names = columns_for(client.get('/api/sailors-for-onwater'))
assert data['station'] is None, 'no station param must keep station=None'
assert len(data['columns']) == 6, 'expected 6 columns, got %s' % names
assert names[-1] == 'Open Category', 'Open Category must trail, got %s' % names
assign = data['assignments']
assert len(assign) == 6, assign
by_station = {1: set(), 2: set()}
for col in data['columns']:
    by_station[col['station']].add(col['class_name'])
    assert col['station'] == assign[col['class_key']], 'column station must match assignments'
assert by_station[1] == {'Ilca 6', 'Ilca 7', 'Starling'}, by_station[1]
assert by_station[2] == {'Optimist', 'Zephyr', 'Open Category'}, by_station[2]
print('PASS: default split - first 3 classes on station 1, remainder + Open on station 2')

# --- 2. Station filtering
_, st1 = columns_for(client.get('/api/sailors-for-onwater?station=1'))
_, st2 = columns_for(client.get('/api/sailors-for-onwater?station=2'))
assert set(st1) == {'Ilca 6', 'Ilca 7', 'Starling'}, st1
assert set(st2) == {'Optimist', 'Zephyr', 'Open Category'}, st2
print('PASS: ?station=1 / ?station=2 return only their own columns')

# --- 3. Toggle: move Starling to station 2
conn = sqlite3.connect(SCRATCH)
starling_class_id = conn.execute(
    "SELECT class_id FROM boat_classes WHERE flag_image = 'Starling.png'").fetchone()[0]
conn.close()
starling_key = 'c%d' % starling_class_id

r = client.post('/api/assign-class-station',
                json={'class_key': starling_key, 'station': 2})
assert r.get_json()['status'] == 'success', r.get_json()
_, st1 = columns_for(client.get('/api/sailors-for-onwater?station=1'))
_, st2 = columns_for(client.get('/api/sailors-for-onwater?station=2'))
assert set(st1) == {'Ilca 6', 'Ilca 7'}, st1
assert set(st2) == {'Starling', 'Optimist', 'Zephyr', 'Open Category'}, st2

# Version bump so other stations' pollers re-render
rs = client.get('/api/race-status').get_json()
assert rs['sheet_version'] == 2, rs
print('PASS: toggle moves Starling to station 2; assignments_version bumped to 2')

# --- 4. Upsert path: move it back and forth
client.post('/api/assign-class-station', json={'class_key': starling_key, 'station': 1})
client.post('/api/assign-class-station', json={'class_key': starling_key, 'station': 2})
_, st1 = columns_for(client.get('/api/sailors-for-onwater?station=1'))
assert set(st1) == {'Ilca 6', 'Ilca 7'}, st1
print('PASS: re-toggling updates the stored assignment (upsert)')

# --- 5. New class added later defaults by position without disturbing toggles
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': 'ilca7.png', 'grid_index': 1, 'countdown_minutes': 1},
    {'id': 'r2', 'label': 'Start2', 'flag_image': 'Starling.png',
     'secondary_flag_image': 'optimist.png', 'grid_index': 2, 'countdown_minutes': 1},
    {'id': 'r3', 'label': 'Zephyr', 'flag_image': 'Zephyr.png',
     'grid_index': 3, 'countdown_minutes': 1},
    {'id': 'r4', 'label': 'Start4', 'flag_image': 'farr3point7.png',
     'grid_index': 4, 'countdown_minutes': 1},
]})
data, names = columns_for(client.get('/api/sailors-for-onwater'))
assert len(data['columns']) == 7, names
by_station = {1: set(), 2: set()}
for col in data['columns']:
    by_station[col['station']].add(col['class_name'])
assert by_station[1] == {'Ilca 6', 'Ilca 7'}, by_station[1]
assert '3.7' in by_station[2], 'new 6th class must default to station 2'
assert 'Starling' in by_station[2], 'stored toggle must survive a new class appearing'
print('PASS: new class defaults to station 2; stored toggles unaffected')

# --- 6. Assignments kept for the day - across a full race cycle
client.post('/api/class-start', json={
    'flag_images': ['ilca6.png', 'ilca7.png'], 'sequence_number': 1})
assert m.app_state.get('race_id'), 'race should be auto-created'
client.post('/api/end-race')
client.post('/api/reset-finish-sheet')
data, _ = columns_for(client.get('/api/sailors-for-onwater'))
by_station = {1: set(), 2: set()}
for col in data['columns']:
    by_station[col['station']].add(col['class_name'])
assert by_station[1] == {'Ilca 6', 'Ilca 7'}, by_station[1]
assert 'Starling' in by_station[2], 'toggle must persist across the race cycle'
print('PASS: assignments kept for the day across race end + reset-finish-sheet')

# --- 7. Validation
r = client.post('/api/assign-class-station', json={'class_key': starling_key, 'station': 3})
assert r.status_code == 400, 'station 3 must be rejected'
r = client.post('/api/assign-class-station', json={'station': 1})
assert r.status_code == 400, 'missing class_key must be rejected'
r = client.post('/api/assign-class-station', json={'class_key': 'cx', 'station': '2'})
assert r.get_json()['status'] == 'success', 'string station should be accepted'
print('PASS: validation (bad station, missing class_key rejected; string station ok)')

os.remove(SCRATCH)
print()
print('PASS multi-station class split: defaults, filtering, toggle, persistence, validation')
