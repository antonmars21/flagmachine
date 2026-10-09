"""Verify bug 12 fix: open-category sailors can lap and finish once the race
is active, while sailors of a sequenced-but-not-yet-started class stay blocked."""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b12.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# Sequence: Starling (grid 1) and Ilca 6 (grid 2) only.
# Zephyr sailors are NOT in the sequence -> Open Category.
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Starling', 'flag_image': 'Starling.png', 'grid_index': 1, 'countdown_minutes': 2},
    {'id': 'r2', 'label': 'Ilca6', 'flag_image': 'ilca6.png', 'grid_index': 2, 'countdown_minutes': 2},
]})
client.post('/api/toggle-racing', json={'uid': 'SL-1091', 'racing_today': True})   # Starling
client.post('/api/toggle-racing', json={'uid': 'SL-15', 'racing_today': True})     # Ilca 6
client.post('/api/toggle-racing', json={'uid': 'SL-12', 'racing_today': True})     # Zephyr (open)

# Starling class starts (fires first countdown end); Ilca 6 has NOT started
client.post('/api/class-start', json={'flag_image': 'Starling.png', 'sequence_number': 1})

cols = {c['class_name']: c for c in client.get('/api/sailors-for-onwater').get_json()['columns']}
print('open category sailors:', [(s['short_name'], s['open_category']) for s in cols['Open Category']['sailors']])
print('starling col flags:', [(s['short_name'], s['open_category'], s['class_started'])
                              for s in cols['Starling']['sailors']])

# 1. Open-category sailor CAN lap and finish (was 400 before the fix)
r = client.post('/api/record-lap', json={'uid': 'SL-12'})
print('open cat lap  ->', r.status_code, r.get_json())
assert r.status_code == 200, 'open-category lap still blocked'
r = client.post('/api/mark-finish', json={'uid': 'SL-12'})
print('open cat fins ->', r.status_code, r.get_json())
assert r.status_code == 200, 'open-category finish still blocked'

# 2. Starling sailor (started class) still works
r = client.post('/api/record-lap', json={'uid': 'SL-1091'})
assert r.status_code == 200, 'started-class lap broken'

# 3. Ilca 6 sailor (in sequence, NOT started) must stay blocked
r = client.post('/api/record-lap', json={'uid': 'SL-15'})
print('not-started class lap ->', r.status_code, r.get_json())
assert r.status_code == 400, 'not-yet-started class should stay blocked'
r = client.post('/api/mark-finish', json={'uid': 'SL-15'})
assert r.status_code == 400

print('\nPASS bug 12: open category activates; sequenced-but-unstarted classes remain gated')
os.remove(SCRATCH)
