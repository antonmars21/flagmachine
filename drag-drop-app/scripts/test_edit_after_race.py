"""Kanban "record to get edit" (sailor edits must stick after a race):

Full reported flow over the API on a scratch DB: load Rob + some Ilca
sailors, sign them on, start the race, score (lap + finish), end the race,
reset the finish sheet - then edit Rob's sail number from the Sailor
Registry (PUT /api/edit-sailor) and verify it STICKS (registry GET + raw
DB row). Plus the cross-class rule: one sailor may carry the SAME sail
number in several classes (Ilca 4/6/7), same-class collisions still get a
friendly 400, and back-to-back edits to different sailors all succeed.
Also checks the export still works after all of that (the two kanban bugs
were suspected linked).
"""

import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_edit_after_race.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
m.app_state['race_id'] = None
m.app_state['race_start_timestamp'] = None
m.app_state['class_start_times'] = {}
m.app_state['open_start_time'] = None
m.app_state['race_ended'] = False
m.app_state['race_end_timestamp'] = None
m.app_state['status'] = 'READY'
m.app_state['sequence'] = []

client = m.app.test_client()

conn = sqlite3.connect(SCRATCH)
conn.execute("DELETE FROM sailors WHERE sailor_name LIKE 'Repro %'")
for table in ('capture_actions', 'lap_records', 'race_sailors',
              'race_class_starts', 'race_open_starts'):
    conn.execute(f'DELETE FROM {table}')
conn.execute("UPDATE races SET status='ENDED'")
conn.commit()
conn.close()


def add(name, short, no, cls):
    r = client.post('/api/add-sailor', json={
        'sailor_name': name, 'short_name': short, 'sail_no': no,
        'boat_class': cls, 'handicap': 1.0, 'seed': 0})
    assert r.status_code == 200, r.get_json()


add('Repro Rob', 'Rob', 'R001', 'Ilca 6')
add('Repro Anna', 'Anna', 'R002', 'Ilca 6')
add('Repro Ben', 'Ben', 'R003', 'Ilca 6')

conn = sqlite3.connect(SCRATCH)
uids = {r[1]: r[0] for r in conn.execute(
    "SELECT uid, short_name FROM sailors WHERE sailor_name LIKE 'Repro %'").fetchall()}
conn.close()
rob_uid = uids['Rob']

for uid in uids.values():
    r = client.post('/api/toggle-racing', json={'uid': uid, 'racing_today': True})
    assert r.status_code == 200

# start the race, score (lap + finish for Rob), end the race, reset the sheet
assert client.post('/api/start-race', json={}).status_code == 200
assert client.post('/api/record-lap', json={'uid': rob_uid, 'station': 1}).status_code == 200
assert client.post('/api/mark-finish', json={'uid': rob_uid, 'station': 1}).status_code == 200
assert client.post('/api/end-race').status_code == 200
assert client.post('/api/reset-finish-sheet').status_code == 200
print('PASS: race flow (start -> lap -> finish -> end -> reset) completed')


def sail_no_of(uid):
    conn = sqlite3.connect(SCRATCH)
    row = conn.execute('SELECT sail_no FROM sailors WHERE uid=?', (uid,)).fetchone()
    conn.close()
    return row[0]


# --- edit Rob's sail number after the race: must stick ----------------------
r = client.put(f'/api/edit-sailor/{rob_uid}', json={
    'sailor_name': 'Repro Rob', 'short_name': 'Rob', 'sail_no': 'R999',
    'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, f'edit after race must succeed: {r.get_json()}'
reg = [s for s in client.get('/api/sailors-registry').get_json()['sailors'] if s['uid'] == rob_uid]
assert reg and reg[0]['sail_no'] == 'R999', f'registry must show the new number: {reg}'
assert sail_no_of(rob_uid) == 'R999', 'DB row must hold the new number'
print('PASS: sail-no edit after a full race flow sticks (registry + DB)')

# --- back-to-back edits to different sailors all succeed --------------------
r = client.put(f"/api/edit-sailor/{uids['Anna']}", json={
    'sailor_name': 'Repro Anna', 'short_name': 'Anna', 'sail_no': 'R888',
    'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, f'second edit must succeed: {r.get_json()}'
r = client.put(f"/api/edit-sailor/{uids['Ben']}", json={
    'sailor_name': 'Repro Ben', 'short_name': 'Ben', 'sail_no': 'R777',
    'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, f'third edit must succeed: {r.get_json()}'
assert sail_no_of(uids['Anna']) == 'R888' and sail_no_of(uids['Ben']) == 'R777'
print('PASS: following edits (Anna, Ben) also stick - no edit lock')

# --- same sail number shared across DIFFERENT classes is allowed ------------
r = client.post('/api/add-sailor', json={
    'sailor_name': 'Repro Rob', 'short_name': 'Rob7', 'sail_no': 'R999',
    'boat_class': 'Ilca 7', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, f'cross-class share must be allowed: {r.get_json()}'
r = client.put(f'/api/edit-sailor/{rob_uid}', json={
    'sailor_name': 'Repro Rob', 'short_name': 'Rob', 'sail_no': 'R999',
    'boat_class': 'Ilca 7', 'handicap': 1.0, 'seed': 0})
# moving Rob to Ilca 7 with R999 while his Ilca 7 row holds R999 -> same-class collision
assert r.status_code == 400 and 'already used by' in r.get_json()['message'], r.get_json()
assert sail_no_of(rob_uid) == 'R999'
# but editing the Ilca 7 row itself to the shared number is fine (same uid excluded)
conn = sqlite3.connect(SCRATCH)
rob7_uid = conn.execute("SELECT uid FROM sailors WHERE short_name='Rob7'").fetchone()[0]
conn.close()
r = client.put(f'/api/edit-sailor/{rob7_uid}', json={
    'sailor_name': 'Repro Rob', 'short_name': 'Rob7', 'sail_no': 'R999',
    'boat_class': 'Ilca 7', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, r.get_json()
# and Rob Ilca 6 may keep the same number (different class)
r = client.put(f'/api/edit-sailor/{rob_uid}', json={
    'sailor_name': 'Repro Rob', 'short_name': 'Rob', 'sail_no': 'R999',
    'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, f'cross-class share on edit must succeed: {r.get_json()}'
print('PASS: same sail number across Ilca 6 + Ilca 7 allowed; same-class collision -> friendly 400, row unchanged')

# --- the export still works after all of the above (bugs may be linked) -----
r = client.get('/api/export-race-csv')
assert r.status_code == 200 and 'text/csv' in r.headers.get('Content-Type', ''), \
    f'export after race+edits must still work: {r.status_code}'
print('PASS: export after race + edits still returns a plain CSV')

os.remove(SCRATCH)
print('\nPASS kanban "record to get edit": edits stick after a race; cross-class sail numbers shared; per-class uniqueness enforced')
