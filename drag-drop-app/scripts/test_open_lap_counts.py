"""Verify the bug 28 fix: the on-water state endpoint must report REAL lap
counts for open-category sailors.

Bug 28 (seen 24 Oct, Gabrielle Marais sailing a Europe - no class flag, so
Open Category): /api/sailors-for-onwater served open sailors only from the
'live rows' query with a HARDCODED 0 lap_count (the started-classes query
filters on s.class_id, which is NULL for open sailors). Every poll, sheet
re-render and browser refresh therefore reset the on-sheet lap counter to 0,
so scorers re-clicked and recorded duplicate laps seconds apart. Live rows
now LEFT JOIN race_sailors and carry the true lap_count / finish_time.
"""
import json
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b28.db'
shutil.copy('score.db', SCRATCH)

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
# Hermetic open-category fixture (post bugs-33/34 repair): the repair links
# every sailor with a NAMED class to a boat_classes row, so a guaranteed
# open-category sailor is a CLASSLESS one (empty boat_class - the repair
# leaves those alone, and no flag can ever match an unnamed class).
conn.execute("""INSERT OR REPLACE INTO sailors
               (uid, sailor_name, short_name, sail_no, boat_class, handicap,
                seed, class_id, racing_today, status)
               VALUES ('SL-OPEN28', 'Open Test', 'OpenT', 'OP28', '', 1.0, 0,
                       NULL, 0, 'racing')""")
open_uid = 'SL-OPEN28'
# A sequenced class sailor for the start
ilca6_id = conn.execute(
    "SELECT class_id FROM boat_classes WHERE flag_image = 'ilca6.png'").fetchone()[0]
ilca6_uid = conn.execute(
    'SELECT uid FROM sailors WHERE class_id = ? LIMIT 1', (ilca6_id,)).fetchone()[0]
# Clean pre-existing RUNNING races so class-start creates a fresh race
conn.execute("UPDATE races SET status = 'ENDED' WHERE status = 'RUNNING'")
conn.commit()
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': None, 'grid_index': 1, 'countdown_minutes': 3},
]})
for uid in (open_uid, ilca6_uid):
    client.post('/api/toggle-racing', json={'uid': uid, 'racing_today': True})

# Start the race (Ilca 6 fires; open category activates with the race start)
resp = client.post('/api/class-start',
                   json={'flag_images': ['ilca6.png'], 'sequence_number': 1})
assert resp.status_code == 200, resp.get_data(as_text=True)


def open_sailor_state():
    # No station filter: the Open column's station assignment is inherited
    # from the live DB copy and may be station 2
    data = client.get('/api/sailors-for-onwater').get_json()
    for col in data['columns']:
        if col['class_id'] is None or col.get('class_name') == 'Open Category':
            for sailor in col['sailors']:
                if sailor['uid'] == open_uid:
                    return sailor
    return None


# Lap 1 recorded -> the state endpoint must report it (was hardcoded 0)
resp = client.post('/api/record-lap', json={'uid': open_uid, 'station': 1})
assert resp.status_code == 200, resp.get_data(as_text=True)
assert resp.get_json()['lap_count'] == 1
sailor = open_sailor_state()
assert sailor is not None, 'open sailor missing from the Open Category column'
assert sailor['lap_count'] == 1, \
    f"BUG 28: open sailor lap_count in state endpoint is {sailor['lap_count']}, expected 1"
print('lap 1: state endpoint reports open sailor lap_count = 1 (poll keeps it)')

# Lap 2 -> still reported (the old code reset to 0 on every poll)
# (double-capture guard: real boats need minutes per lap, test waits it out)
import time
time.sleep(2.2)
resp = client.post('/api/record-lap', json={'uid': open_uid, 'station': 1})
assert resp.status_code == 200, resp.get_data(as_text=True)
sailor = open_sailor_state()
assert sailor['lap_count'] == 2, \
    f"BUG 28: open sailor lap_count in state endpoint is {sailor['lap_count']}, expected 2"
print('lap 2: state endpoint reports open sailor lap_count = 2 (browser refresh keeps it)')

# Finish -> finish_time flows through the state endpoint (card renders finished)
resp = client.post('/api/mark-finish', json={'uid': open_uid, 'station': 1})
assert resp.status_code == 200, resp.get_data(as_text=True)
sailor = open_sailor_state()
assert sailor['finish_time'], 'open sailor finish_time missing from state endpoint'
print('finish: state endpoint reports open sailor finish_time (card shows Fin)')

# Sanity: sequenced-class sailors still report through the locked roster
client.post('/api/record-lap', json={'uid': ilca6_uid, 'station': 1})
data = client.get('/api/sailors-for-onwater').get_json()
found = None
for col in data['columns']:
    for s in col['sailors']:
        if s['uid'] == ilca6_uid:
            found = s
assert found and found['lap_count'] == 1, 'sequenced class sailor lap_count broken'
print('sequenced class sailor still reports lap_count = 1 through the locked roster')

# No active race -> live rows report 0 (no stale counts from other races)
client.post('/api/end-race')
client.post('/api/reset-finish-sheet')
data = client.get('/api/sailors-for-onwater').get_json()
for col in data['columns']:
    for s in col['sailors']:
        if s['uid'] == open_uid:
            assert s['lap_count'] == 0, \
                f"stale lap_count {s['lap_count']} leaked after reset (expected 0)"
print('after reset: no active race -> live rows report lap_count 0 (no stale leak)')

os.remove(SCRATCH)
print()
print('PASS bug 28: open-category lap counts survive polls and browser refreshes')
