"""Regression: open-flag-only start sequence (RO report 2026-11-03).

Bug: when the ONLY flag in a start event was the open-class flag
(openclass.png), every racing sailor still showed in their INDIVIDUAL class
column (per the registry) instead of defaulting to Open Category - and when
the start sequence hit 0, only the open start fired (class_start_times stays
empty), so no station card ever activated (lap/finish buttons stayed
disabled).

Expected after the fix (app.py sailors_for_onwater):
- a sequence with flags but no class flag (open-only or signal-only) puts ALL
  racing sailors into the single Open Category column;
- when that start event fires, open_started becomes true, every Open Category
  sailor reports class_started=true and can lap/finish (stations activate);
- a class flag + open flag in the SAME start event still split correctly
  (class sailors in the class column, everyone else Open);
- a completely EMPTY sequence keeps the pre-race setup view (all classes
  grouped individually, no Open Category column).
"""

import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_openflag.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

from scripts.seed_test_sailors import seed_fixture_sailors
conn = sqlite3.connect(SCRATCH)
seed_fixture_sailors(conn)
conn.commit()
conn.close()

# Fixture sailors racing today: Starling x2, Ilca 6 x2, Zephyr, Frostbite
for uid in ('SL-1091', 'SL-955', 'SL-15', 'SL-18789', 'SL-12', 'SL-141'):
    client.post('/api/toggle-racing', json={'uid': uid, 'racing_today': True})


def columns():
    data = client.get('/api/sailors-for-onwater').get_json()
    assert data['status'] == 'success'
    return data['columns']


def by_name(cols):
    return {c['class_name']: c for c in cols}


# --- 1. open-flag-only sequence: everyone defaults to Open Category --------
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Open', 'flag_image': 'openclass.png',
     'grid_index': 1, 'countdown_minutes': 1},
]})
cols = columns()
names = [c['class_name'] for c in cols]
print('open-only sequence columns:', names)
assert names == ['Open Category'], \
    f'open-only sequence must produce ONLY the Open Category column, got {names}'
open_sailors = cols[0]['sailors']
assert all(s['open_category'] for s in open_sailors)
assert all(not s['class_started'] for s in open_sailors), 'nothing started yet'
print('PASS: open-flag-only sequence defaults all sailors to Open Category')

# --- 2. start sequence hits 0: open start fires, stations activate ---------
r = client.post('/api/class-start', json={'flag_images': ['openclass.png'],
                                           'sequence_number': 1})
assert r.status_code == 200 and r.get_json().get('open_start'), r.get_json()
rs = client.get('/api/race-status').get_json()
assert rs['open_started'] is True, 'open_started must be true after the open flag fires'
assert rs['class_start_times'] == {}, 'no class start should be recorded for openclass.png'

cols = columns()
assert [c['class_name'] for c in cols] == ['Open Category']
assert all(s['class_started'] for s in cols[0]['sailors']), \
    'every Open Category sailor must activate (class_started) when the open start fires'
print('PASS: sequence hitting 0 activates the Open Category station')

r = client.post('/api/record-lap', json={'uid': 'SL-12'})
assert r.status_code == 200, f'open-category lap must be allowed after open start: {r.get_json()}'
r = client.post('/api/mark-finish', json={'uid': 'SL-12'})
assert r.status_code == 200, 'open-category finish must be allowed after open start'
print('PASS: activated open sailors can lap and finish')

# --- 3. class flag + open flag in the SAME start event split correctly -----
client.post('/api/reset-race', json={})
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Starling', 'flag_image': 'Starling.png',
     'secondary_flag_image': 'openclass.png', 'grid_index': 1, 'countdown_minutes': 1},
]})
cols = by_name(columns())
assert set(cols) == {'Starling', 'Open Category'}, f'got {sorted(cols)}'
starling = {s['short_name'] for s in cols['Starling']['sailors']}
openc = {s['short_name'] for s in cols['Open Category']['sailors']}
print('class+open columns:', starling, '/', openc)
assert starling == {'TestOne', 'TestTwo'}, starling
assert 'TestThree' in openc and 'TestFive' in openc and 'TestSix' in openc, openc
assert all(not s['open_category'] for s in cols['Starling']['sailors'])
assert all(s['open_category'] for s in cols['Open Category']['sailors'])
print('PASS: class flag + open flag in one start event split correctly')

# --- 4. empty sequence keeps the pre-race setup view ------------------------
client.post('/api/reset-race', json={})
client.post('/update-sequence', json={'sequence': []})
cols = columns()
names = {c['class_name'] for c in cols}
print('empty-sequence columns:', sorted(names))
assert 'Starling' in names and 'Zephyr' in names, 'empty sequence must group by individual class'
assert 'Open Category' not in names, 'no Open Category column without any flag in the sequence'
print('PASS: empty sequence keeps the pre-race per-class setup view')

os.remove(SCRATCH)
print('\nALL OPEN-FLAG-ONLY CHECKS PASS')
