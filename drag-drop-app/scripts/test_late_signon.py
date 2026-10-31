"""Verify bug 14 fix: a sailor signed on AFTER their class start stays visible
in their own class column, can lap/finish, appears in the CSV export, and never
duplicates once they join race_sailors.

Also verifies the bug 12 business rule: ALL flags in a start event (primary +
secondary, e.g. Ilca 6 and Ilca 7 sharing one start) each get their own column;
only boats with no matching flag route to Open Category.
"""
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b14.db'
shutil.copy('score.db', SCRATCH)

# Start from a clean slate: nobody racing today, no stale class starts
conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
conn.commit()
conn.close()


def uid_of_class(flag_image):
    """First racing-capable sailor uid of the class with this flag image."""
    conn = sqlite3.connect(SCRATCH)
    row = conn.execute('''
        SELECT s.uid FROM sailors s
        JOIN boat_classes bc ON s.class_id = bc.class_id
        WHERE LOWER(bc.flag_image) = LOWER(?)
        ORDER BY s.seed LIMIT 1''', (flag_image,)).fetchone()
    conn.close()
    assert row, f'no sailor found for class flag {flag_image}'
    return row[0]


import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# Look up sailor uids + the P Class flag from the DB itself (flags get
# refreshed/renamed, so never hardcode flag names in this test)
def uid_and_flag_of_class(class_name):
    conn = sqlite3.connect(SCRATCH)
    row = conn.execute('''
        SELECT s.uid, bc.flag_image FROM sailors s
        JOIN boat_classes bc ON s.class_id = bc.class_id
        WHERE bc.class_name = ?
        ORDER BY s.seed LIMIT 1''', (class_name,)).fetchone()
    conn.close()
    assert row, f'no sailor found for class {class_name}'
    return row[0], row[1]

ilca6_uid = uid_of_class('ilca6.png')
ilca7_uid = uid_of_class('ilca7.png')
pclass_uid, pclass_flag = uid_and_flag_of_class('P Class')
zephyr_uid = uid_of_class('Zephyr.png')

# Sequence: Start 1 = Ilca 6 (primary) + Ilca 7 (secondary, shared start),
# Start 2 = P Class. Zephyr is NOT in the sequence -> Open Category.
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': 'ilca7.png', 'grid_index': 1, 'countdown_minutes': 2},
    {'id': 'r2', 'label': 'Pclass', 'flag_image': pclass_flag,
     'secondary_flag_image': None, 'grid_index': 2, 'countdown_minutes': 2},
]})
for uid in (ilca6_uid, ilca7_uid, zephyr_uid):
    client.post('/api/toggle-racing', json={'uid': uid, 'racing_today': True})
# NOTE: pclass_uid is deliberately NOT signed on yet - she signs on late below.

# Start 1 fires: both the primary AND secondary flag trigger class-start
r = client.post('/api/class-start', json={'flag_image': 'ilca6.png', 'sequence_number': 1})
assert r.status_code == 200, 'ilca6 class-start failed'
r = client.post('/api/class-start', json={'flag_image': 'ilca7.png', 'sequence_number': 1})
assert r.status_code == 200, 'ilca7 (secondary flag) class-start failed'
# Start 2 fires: P Class starts WITHOUT its late sailor in the locked roster
r = client.post('/api/class-start', json={'flag_image': pclass_flag, 'sequence_number': 2})
assert r.status_code == 200, 'pclass class-start failed'

# --- BUG 14 REPRO: sailor signs on 23s after her class start (as in recording) ---
client.post('/api/toggle-racing', json={'uid': pclass_uid, 'racing_today': True})

def columns():
    return {c['class_name']: c for c in
            client.get('/api/sailors-for-onwater').get_json()['columns']}

def all_sailor_uids(cols):
    uids = []
    for col in cols.values():
        uids.extend(s['uid'] for s in col['sailors'])
    return uids

cols = columns()

# 1. Late sign-on is visible in her OWN class column, marked class-started
p_col = cols.get('P Class')
assert p_col, 'no P Class column on finish sheet'
p_sailors = [s['uid'] for s in p_col['sailors']]
assert pclass_uid in p_sailors, f'late sign-on {pclass_uid} vanished (bug 14 not fixed)'
late = next(s for s in p_col['sailors'] if s['uid'] == pclass_uid)
assert late['class_started'] is True, 'late sign-on should show as class-started'
assert late['open_category'] is False, 'late sign-on must stay in her own class column'
print('late sign-on visible in own class column:', late['short_name'])

# 2. She appears exactly once across ALL columns (no duplicate)
uids = all_sailor_uids(cols)
assert uids.count(pclass_uid) == 1, f'duplicate entries for {pclass_uid}'

# 3. She can lap and finish immediately
r = client.post('/api/record-lap', json={'uid': pclass_uid})
assert r.status_code == 200, f'late sign-on lap blocked: {r.get_json()}'
r = client.post('/api/mark-finish', json={'uid': pclass_uid})
assert r.status_code == 200, f'late sign-on finish blocked: {r.get_json()}'
print('late sign-on lap + finish accepted')

# 4. After joining the race (first lap), she still appears exactly once
cols = columns()
uids = all_sailor_uids(cols)
assert uids.count(pclass_uid) == 1, 'late sign-on duplicated after joining race_sailors'
late = next(s for s in cols['P Class']['sailors'] if s['uid'] == pclass_uid)
assert late['lap_count'] == 1 and late['finish_time'], 'late sign-on lap/finish not reflected'
print('no duplicate after joining locked roster; lap_count and finish_time persisted')

# 5. She appears in the CSV export
csv_resp = client.get('/api/export-race-csv')
assert csv_resp.status_code == 200
csv_text = csv_resp.get_data(as_text=True)
assert pclass_uid in csv_text or late['short_name'] in csv_text, 'late sign-on missing from CSV export'
print('late sign-on present in CSV export')

# --- BUG 12 RULE: shared start (secondary flag) gets its own column ---
assert 'Ilca 7' in cols, 'secondary-flag class (Ilca 7) has no column'
i7 = next(s for s in cols['Ilca 7']['sailors'] if s['uid'] == ilca7_uid)
assert i7['open_category'] is False, 'secondary-flag sailor wrongly routed to Open Category'
assert i7['class_started'] is True, 'secondary-flag sailor should show class-started'
assert cols['Ilca 7']['sequence_number'] == 1, 'shared start must share the sequence number'
print('secondary flag (Ilca 7) has its own column, sequence 1, started')

# Open category still routes sailors whose class has no flag in any start event
open_col = next((c for c in cols.values() if c['class_name'] == 'Open Category'), None)
assert open_col and zephyr_uid in [s['uid'] for s in open_col['sailors']], \
    'Zephyr (no flag in sequence) should be in Open Category'
print('no-flag class (Zephyr) correctly in Open Category')

print('\nPASS bug 14 + bug 12 rule: late sign-ons stay visible in own class column; '
      'all flags in a start event get their own columns')
os.remove(SCRATCH)
