"""Verify the open-class flag rule (bug 12/19):

When the RO places an openclass flag in a start event, the Open Category
activates only when THAT start fires - not with the race's first start.
Without an open flag in the sequence, Open Category activates with the
race's first start (covered by test_open_category.py).
"""
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b12open.db'
shutil.copy('score.db', SCRATCH)

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
conn.commit()
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# Start 1 = Starling, Start 2 = OPEN CLASS flag (the RO controls when open starts)
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Starling', 'flag_image': 'Starling.png',
     'secondary_flag_image': None, 'grid_index': 1, 'countdown_minutes': 2},
    {'id': 'r2', 'label': 'Openclass', 'flag_image': 'openclass.png',
     'secondary_flag_image': None, 'grid_index': 2, 'countdown_minutes': 2},
]})

conn = sqlite3.connect(SCRATCH)
starling_uid = conn.execute('''
    SELECT s.uid FROM sailors s JOIN boat_classes bc ON s.class_id = bc.class_id
    WHERE bc.flag_image = 'Starling.png' ORDER BY s.seed LIMIT 1''').fetchone()[0]
zephyr_uid = conn.execute('''
    SELECT s.uid FROM sailors s JOIN boat_classes bc ON s.class_id = bc.class_id
    WHERE bc.flag_image = 'Zephyr.png' ORDER BY s.seed LIMIT 1''').fetchone()[0]
conn.close()
client.post('/api/toggle-racing', json={'uid': starling_uid, 'racing_today': True})
client.post('/api/toggle-racing', json={'uid': zephyr_uid, 'racing_today': True})   # open category

# 1. Start 1 fires (Starling) - race is now running, but the open flag has NOT fired
r = client.post('/api/class-start', json={'flag_image': 'Starling.png', 'sequence_number': 1})
assert r.status_code == 200

status = client.get('/api/race-status').get_json()
assert status['race_id'], 'race should be auto-created by first class start'
assert status['open_flag_in_sequence'] is True, 'open flag is in the sequence'
assert status['open_started'] is False, 'open must NOT be started before its flag fires'
print('race running, open flag in sequence, open not yet started')

# 2. Open-category sailor is visible but NOT activated, and laps are blocked server-side
cols = {c['class_name']: c for c in client.get('/api/sailors-for-onwater').get_json()['columns']}
open_sailors = {s['uid']: s for s in cols['Open Category']['sailors']}
assert zephyr_uid in open_sailors, 'Zephyr sailor should be in Open Category'
assert open_sailors[zephyr_uid]['class_started'] is False, 'open sailor activated too early'
r = client.post('/api/record-lap', json={'uid': zephyr_uid})
assert r.status_code == 400 and 'Open class' in r.get_json()['message'], \
    'open sailor should be blocked before the open flag fires'
r = client.post('/api/mark-finish', json={'uid': zephyr_uid})
assert r.status_code == 400, 'open finish should be blocked before the open flag fires'
print('open sailor visible but gated before open flag fires')

# 3. Starling sailor (started class) can still lap - the gate only affects open category
r = client.post('/api/record-lap', json={'uid': starling_uid})
assert r.status_code == 200, 'started-class sailor should not be affected'

# 4. Start 2 fires: the OPEN CLASS flag - open category activates
r = client.post('/api/class-start', json={'flag_image': 'openclass.png', 'sequence_number': 2})
assert r.status_code == 200 and r.get_json().get('open_start'), f'open flag class-start failed: {r.get_json()}'
status = client.get('/api/race-status').get_json()
assert status['open_started'] is True, 'open should be started after its flag fires'

cols = {c['class_name']: c for c in client.get('/api/sailors-for-onwater').get_json()['columns']}
open_s = next(s for s in cols['Open Category']['sailors'] if s['uid'] == zephyr_uid)
assert open_s['class_started'] is True, 'open sailor should be activated after open flag fires'
r = client.post('/api/record-lap', json={'uid': zephyr_uid})
assert r.status_code == 200, f'open lap still blocked: {r.get_json()}'
r = client.post('/api/mark-finish', json={'uid': zephyr_uid})
assert r.status_code == 200, f'open finish still blocked: {r.get_json()}'
print('open flag fired: open sailor activated, lap + finish accepted')

# 4b. The open start must be PERSISTED (class_id NULL) and appear in the CSV
conn = sqlite3.connect(SCRATCH)
open_rows = list(conn.execute(
    'SELECT start_time, sequence_number FROM race_open_starts WHERE race_id = ?',
    (status['race_id'],)))
conn.close()
assert len(open_rows) == 1 and open_rows[0][1] == 2, f'open start row wrong: {open_rows}'
open_start_time, open_seq = open_rows[0]
csv_text = client.get('/api/export-race-csv').get_data(as_text=True)
zephyr_line = next(l for l in csv_text.splitlines() if 'Zephyr' in l or zephyr_uid in l)
assert open_start_time in zephyr_line, f'open start time missing from CSV: {zephyr_line}'
# Sailwave import format: the open start time is the sailor's StartTime; the
# legacy layout (?format=detailed) still carries the open sequence number
# (2nd column - the 1st is the calendar Series name)
detailed = client.get('/api/export-race-csv?format=detailed').get_data(as_text=True)
zephyr_detailed = next(l for l in detailed.splitlines() if 'Zephyr' in l or zephyr_uid in l)
assert zephyr_detailed.split(',')[1] == str(open_seq), f'open sequence number missing from detailed CSV: {zephyr_detailed}'
print('open start persisted and exported: start time in Sailwave CSV + sequence in detailed CSV')

# 5. Reset clears the open start state too
client.post('/api/reset-race')
status = client.get('/api/race-status').get_json()
assert status['open_started'] is False and status['race_id'] is None, 'reset did not clear open start state'
print('reset-race clears open start state')

print('\nPASS open-class flag rule: open activates when the openclass flag fires, '
      'not with the first start')
os.remove(SCRATCH)
