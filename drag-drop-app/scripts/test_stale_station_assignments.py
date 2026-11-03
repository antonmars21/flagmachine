"""Regression: stale persisted station assignments must not empty a station
sheet (RO report 2026-11-03: "ticked sailors not added to the station
sheets" - Station 1 showed 'No classes assigned' because class_station_
assignments rows from a PREVIOUS day pinned every current column to
station 2).

Fix: clear_stale_station_assignments() wipes the table at server startup
when no race is RUNNING (fresh day -> default split, first 3 columns on
station 1), and keeps the toggles while a race is RUNNING (mid-day restart
must not reshuffle stations under the scorers).
"""

import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_stale_station.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

from scripts.seed_test_sailors import seed_fixture_sailors
conn = sqlite3.connect(SCRATCH)
seed_fixture_sailors(conn)
conn.commit()

# Simulate stale toggles from a previous day: Ilca 6 + Open pinned to station 2
conn.execute("INSERT OR REPLACE INTO class_station_assignments (class_key, station, updated_at) VALUES ('c1', 2, '2026-10-20 10:00:00')")
conn.execute("INSERT OR REPLACE INTO class_station_assignments (class_key, station, updated_at) VALUES ('open', 2, '2026-10-20 10:00:00')")
# Make sure no race is RUNNING (stale ones from the copied live DB included)
conn.execute("UPDATE races SET status = 'ENDED'")
conn.commit()
conn.close()

for uid in ('SL-1091', 'SL-15', 'SL-12'):
    client.post('/api/toggle-racing', json={'uid': uid, 'racing_today': True})
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca 6', 'flag_image': 'ilca6.png', 'grid_index': 1, 'countdown_minutes': 5},
]})

# --- before the wipe: stale rows pin everything to station 2 --------------
d = client.get('/api/sailors-for-onwater?station=1').get_json()
assert d['columns'] == [], 'expected the stale-assignment bug to reproduce: station 1 empty'
d2 = client.get('/api/sailors-for-onwater?station=2').get_json()
assert {c['class_name'] for c in d2['columns']} == {'Ilca 6', 'Open Category'}
print('reproduced: stale toggles leave station 1 empty ->', d2['assignments'])

# --- startup wipe with no running race: assignments cleared, defaults back -
cleared = m.clear_stale_station_assignments()
assert cleared == 2, f'expected 2 stale rows cleared, got {cleared}'
d = client.get('/api/sailors-for-onwater?station=1').get_json()
names1 = {c['class_name'] for c in d['columns']}
d2 = client.get('/api/sailors-for-onwater?station=2').get_json()
names2 = {c['class_name'] for c in d2['columns']}
print('after wipe: station 1 =', names1, ' station 2 =', names2)
assert 'Ilca 6' in names1, 'default split must put the first columns on station 1 again'
assert names2 == set() or names2 == {'Open Category'} or 'Ilca 6' not in names2
# ticked sailors are now visible on station 1
uids1 = {s['uid'] for c in d['columns'] for s in c['sailors']}
assert 'SL-15' in uids1, 'ticked Ilca 6 sailor must appear on station 1'
print('PASS: fresh day defaults restored, ticked sailors back on station 1')

# --- wipe must NOT happen while a race is RUNNING (mid-day restart) -------
conn = sqlite3.connect(SCRATCH)
conn.execute("INSERT INTO races (status) VALUES ('RUNNING')")
conn.execute("INSERT OR REPLACE INTO class_station_assignments (class_key, station, updated_at) VALUES ('c1', 2, '2026-11-03 09:00:00')")
conn.commit()
conn.close()
cleared = m.clear_stale_station_assignments()
assert cleared == 0, 'assignments must be kept while a race is RUNNING'
conn = sqlite3.connect(SCRATCH)
rows = conn.execute('SELECT class_key, station FROM class_station_assignments').fetchall()
conn.close()
assert ('c1', 2) in rows, 'mid-day toggles must survive the restart'
print('PASS: toggles kept while a race is running (mid-day restart safe)')

os.remove(SCRATCH)
print('\nALL STALE-STATION-ASSIGNMENT CHECKS PASS')
