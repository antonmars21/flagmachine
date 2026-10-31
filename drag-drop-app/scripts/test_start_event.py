"""Verify bug 21 + 22 fixes:

Bug 21a - race auto-creation race condition: simultaneous class-start POSTs
(multi-flag start event, or two tabs) must create exactly ONE race, with all
class start times and rosters recorded against that single race.

Bug 21b - signal flags (p.png, Dflag...) sent with a start event are ignored,
not errors.

Bug 22 - reset-finish-sheet: refuses while the race is running; after the race
is ended it clears the race state (ready for the next race of the day) while
keeping recorded data in the DB and NEVER touching the Flag Machine sequence.
"""
import os
import shutil
import sqlite3
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b21_22.db'
shutil.copy('score.db', SCRATCH)

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
conn.commit()
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# Sequence: Start 1 = Ilca 6 primary + Ilca 7 secondary, Start 2 = pclass
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': 'ilca7.png', 'grid_index': 1, 'countdown_minutes': 3},
    {'id': 'r2', 'label': 'Pclass', 'flag_image': 'pclass.png',
     'secondary_flag_image': None, 'grid_index': 2, 'countdown_minutes': 3},
]})
sequence_snapshot = [dict(item) for item in m.app_state['sequence']]

conn = sqlite3.connect(SCRATCH)
ilca6_uid = conn.execute('''
    SELECT s.uid FROM sailors s JOIN boat_classes bc ON s.class_id = bc.class_id
    WHERE bc.flag_image = 'ilca6.png' ORDER BY s.seed LIMIT 1''').fetchone()[0]
ilca7_uid = conn.execute('''
    SELECT s.uid FROM sailors s JOIN boat_classes bc ON s.class_id = bc.class_id
    WHERE bc.flag_image = 'ilca7.png' ORDER BY s.seed LIMIT 1''').fetchone()[0]
pclass_uid = conn.execute('''
    SELECT s.uid FROM sailors s JOIN boat_classes bc ON s.class_id = bc.class_id
    WHERE bc.flag_image = 'pclass.png' ORDER BY s.seed LIMIT 1''').fetchone()[0]
conn.close()
for uid in (ilca6_uid, ilca7_uid, pclass_uid):
    client.post('/api/toggle-racing', json={'uid': uid, 'racing_today': True})


def count_races():
    conn = sqlite3.connect(SCRATCH)
    n = conn.execute('SELECT COUNT(*) FROM races').fetchone()[0]
    conn.close()
    return n


def class_starts(race_id):
    conn = sqlite3.connect(SCRATCH)
    rows = {r[0]: r[1] for r in conn.execute(
        '''SELECT bc.class_name, rcs.start_time FROM race_class_starts rcs
           LEFT JOIN boat_classes bc ON bc.class_id = rcs.class_id
           WHERE rcs.race_id = ?''', (race_id,))}
    conn.close()
    return rows


# --- 1. Bug 21a: single multi-flag POST (new frontend behaviour) ---
n0 = count_races()
r = client.post('/api/class-start', json={
    'flag_images': ['ilca6.png', 'ilca7.png', 'p.png', 'Dflag.png'],
    'sequence_number': 1})
assert r.status_code == 200, r.get_json()
starts = {s.get('class_name') or s.get('flag_image'): s for s in r.get_json()['starts']}
assert 'Ilca 6' in starts and 'Ilca 7' in starts, starts
# p.png is the blue peter SIGNAL flag (preparatory) - must be skipped, never a class start
assert starts.get('p.png', {}).get('skipped') is True, 'signal flag p.png must be skipped'
assert starts.get('Dflag.png', {}).get('skipped') is True, 'signal flag Dflag must be skipped'
assert count_races() == n0 + 1, 'multi-flag POST must create exactly ONE race'
race_id = r.get_json()['race_id']
assert set(class_starts(race_id)) == {'Ilca 6', 'Ilca 7'}, class_starts(race_id)
print('multi-flag POST: one race, both classes started, signal flags ignored')

# --- 2. Bug 21a: two CONCURRENT single-flag POSTs must still be one race ---
client.post('/api/reset-race')
n0 = count_races()
barrier = threading.Barrier(2)
outcomes = []

def fire(flag):
    barrier.wait()
    outcomes.append(client.post('/api/class-start',
                                json={'flag_image': flag, 'sequence_number': 1}))

t1 = threading.Thread(target=fire, args=('ilca6.png',))
t2 = threading.Thread(target=fire, args=('ilca7.png',))
t1.start(); t2.start(); t1.join(); t2.join()
for o in outcomes:
    assert o.status_code == 200, o.get_json()
assert count_races() == n0 + 1, \
    f'concurrent class-starts created {count_races() - n0} races - race condition not fixed'
race_id = outcomes[0].get_json()['race_id']
assert set(class_starts(race_id)) == {'Ilca 6', 'Ilca 7'}, class_starts(race_id)
print('concurrent class-start POSTs: exactly one race created (bug 21 fixed)')

# --- 3. CSV start times now present for every started-class sailor ---
r = client.post('/api/record-lap', json={'uid': ilca6_uid})
assert r.status_code == 200
r = client.post('/api/record-lap', json={'uid': ilca7_uid})
assert r.status_code == 200
csv_text = client.get('/api/export-race-csv').get_data(as_text=True)
assert starts['Ilca 6']['start_time'][:16] in csv_text, 'Ilca 6 start time missing from CSV'
assert starts['Ilca 7']['start_time'][:16] in csv_text, 'Ilca 7 start time missing from CSV'
print('CSV export contains start times for both classes')

# --- 4. Bug 22: reset-finish-sheet refuses while the race is running ---
r = client.post('/api/reset-finish-sheet')
assert r.status_code == 400, 'reset-finish-sheet must refuse while race is running'
assert 'end the race' in r.get_json()['message']
print('reset-finish-sheet refused while race running')

# --- 5. Bug 22: after END RACE, reset clears state, keeps data + sequence ---
conn = sqlite3.connect(SCRATCH)
ended_before = conn.execute("SELECT COUNT(*) FROM races WHERE status = 'ENDED'").fetchone()[0]
conn.close()
client.post('/api/end-race')
conn = sqlite3.connect(SCRATCH)
laps_before = conn.execute('SELECT COUNT(*) FROM lap_records').fetchone()[0]
conn.close()
r = client.post('/api/reset-finish-sheet')
assert r.status_code == 200, r.get_json()
status = client.get('/api/race-status').get_json()
assert status['race_id'] is None and status['race_ended'] is False, 'race state not cleared'
assert status['class_start_times'] == {}, 'class start times not cleared'
# Data preserved for the completed race
conn = sqlite3.connect(SCRATCH)
laps_after = conn.execute('SELECT COUNT(*) FROM lap_records').fetchone()[0]
ended_after = conn.execute("SELECT COUNT(*) FROM races WHERE status = 'ENDED'").fetchone()[0]
conn.close()
assert laps_before == laps_after and laps_before > 0, 'recorded laps were deleted by reset'
assert ended_after == ended_before + 1, 'completed race history must be kept'
# Sequence untouched (Q3: never touch the running sequence)
assert m.app_state['sequence'] and \
       [i['id'] for i in m.app_state['sequence']] == [i['id'] for i in sequence_snapshot], \
       'reset-finish-sheet must NOT wipe the Flag Machine sequence'
print('reset after end: race state cleared, laps + race history kept, sequence untouched')

# --- 6. Finish sheet renders READY state for the next race ---
data = client.get('/api/sailors-for-onwater').get_json()
for col in data['columns']:
    for s in col['sailors']:
        assert s['class_started'] is False and s['lap_count'] == 0, \
            'finish sheet must show a clean READY sheet after reset'
print('finish sheet back to READY (no active classes, zero laps)')

print('\nPASS bug 21 (single race + signal flags) and bug 22 (safe reset, ready for next race)')
os.remove(SCRATCH)
