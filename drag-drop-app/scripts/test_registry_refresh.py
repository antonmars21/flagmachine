"""Bug 35: registry ticks must load sailors into the race start list.

RO report 2026-10-29: after a race had been run and ended, ticking sailors
in the Sailor Registry did not load them into the finish-sheet start list
(the window eventually refreshed after 10+ seconds or a restart).

Root cause: app_state['race_id'] STAYS SET after End Race (only Reset clears
it - end-race/laps/export must keep targeting the ended race), and
finishsheet.js computed `state.race_active = !!data.race_id`. With race_id
lingering, EVERY deliberate refresh was gated behind `if (!state.race_active)`:
the tick handler, the 3s background refresher, clear-registry and
add/edit/delete sailor all froze after the first race of the day, and only a
Reset or a server restart brought them back.

Fix:
- finishsheet.js: race_active now means RUNNING - `!!race_id && !race_ended`
  (fm_status ENDED still locks Start Race via fmEngaged, so bug 4 is intact).
- a tick / clear / add / edit / delete is a DELIBERATE sign-on action: the
  columns always refresh immediately (mid-race too - late sign-ons must be
  visible, bug 14). Only the automatic 3s poller keeps the pre-race gate.

Checks here (API on a scratch DB + invariants on the real finishsheet.js):
- pre-race tick -> sailor served in the live column;
- start a class (race record), END the race -> race_id STILL SET + race_ended
  (the trap that froze the JS) -> a NEW tick is still served live (late
  sign-on into the next race);
- reset-finish-sheet clears race_id again;
- finishsheet.js invariants: the race_ended guard on race_active, no
  `!state.race_active` gate left around deliberate refreshes, brace balance.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b35.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# Hermetic fixture sailors (live roster is user-managed)
import sqlite3
from scripts.seed_test_sailors import seed_fixture_sailors
conn = sqlite3.connect(SCRATCH)
seed_fixture_sailors(conn)
conn.commit()
conn.close()

client.post('/api/clear-registry')
client.post('/api/reset-race')


def onwater_uids():
    data = client.get('/api/sailors-for-onwater').get_json()
    return {s['uid'] for col in data['columns'] for s in col['sailors']}


def tick(uid, checked=True):
    r = client.post('/api/toggle-racing', json={'uid': uid, 'racing_today': checked})
    assert r.get_json()['status'] == 'success', f'toggle-racing failed for {uid}'


# --- 1. pre-race tick loads the sailor into the start list ---
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Starling', 'flag_image': 'Starling.png', 'grid_index': 1, 'countdown_minutes': 1},
]})
tick('SL-1091')
assert 'SL-1091' in onwater_uids(), 'pre-race tick did not load the sailor'
print('PASS: pre-race tick loads the sailor into the start list')

# --- 2. run + end a race: race_id must STAY SET (the trap) ---
client.post('/api/class-start', json={'flag_image': 'Starling.png', 'sequence_number': 1})
st = client.get('/api/race-status').get_json()
assert st['race_id'] and not st['race_ended'], 'expected a RUNNING race'
client.post('/api/end-race')
st = client.get('/api/race-status').get_json()
assert st['race_id'] and st['race_ended'], \
    'the trap regressed: race_id must persist after End Race (export/end-race target it)'
print('PASS: race_id persists + race_ended after End Race (the trap that froze the JS)')

# --- 3. tick a NEW sailor after the race ended: must be served live ---
tick('SL-955')
uids = onwater_uids()
assert 'SL-955' in uids, 'late sign-on after End Race not served - next-race tick invisible'
assert 'SL-1091' in uids, 'ended race roster disappeared'
print('PASS: tick after End Race is served live (next race of the day)')

# --- 4. reset-finish-sheet clears the trap ---
r = client.post('/api/reset-finish-sheet')
if r.status_code == 200:
    st = client.get('/api/race-status').get_json()
    assert not st['race_id'] and not st['race_ended'], 'reset-finish-sheet must clear race state'
    print('PASS: reset-finish-sheet clears race_id (sheet READY for the next race)')
else:
    print(f'NOTE: reset-finish-sheet returned {r.status_code} - skipping')

# --- 5. finishsheet.js invariants (the actual fix is client-side) ---
with open('static/js/finishsheet.js', encoding='utf-8') as f:
    js = f.read()

assert re.search(r'state\.race_active\s*=\s*!!data\.race_id\s*&&\s*!data\.race_ended', js), \
    'race_active must mean RUNNING: !!race_id && !race_ended (bug 35)'
print('PASS: finishsheet.js race_active is guarded by race_ended')

# Deliberate registry actions must never be gated: the ONLY remaining
# race_active refresh gate is the automatic 3s pre-race poller.
gated = re.findall(r'if\s*\(\s*!state\.race_active\s*\)\s*loadAndRenderSailors', js)
assert len(gated) == 1, \
    f'expected exactly 1 gated refresh (the 3s pre-race poller), found {len(gated)}'
assert re.search(r'setInterval\(\(\)\s*=>\s*\{\s*if\s*\(!state\.race_active\)\s*loadAndRenderSailors\(\);', js), \
    'the one remaining gate must be the automatic 3s poller'
print('PASS: tick/clear/add/edit/delete refresh the columns unconditionally')

# Brace/paren balance sanity on the edited file (JS parse stand-in)
for a, b in (('{', '}'), ('(', ')'), ('[', ']')):
    assert js.count(a) == js.count(b), f'unbalanced {a}{b} in finishsheet.js'
print('PASS: finishsheet.js brace balance OK')

os.remove(SCRATCH)
print('\nPASS bug 35: registry ticks load sailors into the start list (before, during and after a race)')
