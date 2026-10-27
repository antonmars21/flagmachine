"""Verify the bug 31 fix: the RO page rebuilds its start sequence from the
server after navigating back from a finish sheet or refreshing.

Bug 31 (RO report 2026-10-27, found while human-testing bug 30): navigating
back to Race Officer Control worked (same tab, bug 30) but the page came up
EMPTY - every flag and setting was gone. Root cause: the start sequence
lives in app_state['sequence'] on the SERVER (the finish sheets keep their
class columns from it), but the RO page only ever PUSHED its drags to the
server - nothing rebuilt the grids from the server-rendered state, so any
page load started blank.

Fix: index.html renders window.INITIAL_SEQUENCE from app_state; app.js's
restoreSequenceFromServer() rebuilds the grids/rows (primary + secondary +
tertiary flags, labels, minutes, grid numbers) on DOMContentLoaded when the
page's own sequence is empty.
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b31.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

SEQUENCE = [
    {'id': 'row_1', 'label': 'Ilca6', 'flag_image': 'ilca6.png',
     'secondary_flag_image': 'ilca7.png', 'tertiary_flag_image': None,
     'countdown_minutes': 1, 'status': 'PENDING', 'grid_index': 1,
     'current_remaining_seconds': 60},
    {'id': 'row_2', 'label': 'Pclass', 'flag_image': 'pclass.png',
     'secondary_flag_image': None, 'tertiary_flag_image': None,
     'countdown_minutes': 1, 'status': 'PENDING', 'grid_index': 2,
     'current_remaining_seconds': 60},
]

# --- 1. the page embeds the server's live sequence ---
m.app_state['sequence'] = [dict(item) for item in SEQUENCE]
resp = client.get('/')
assert resp.status_code == 200
html = resp.get_data(as_text=True)
match = re.search(r'window\.INITIAL_SEQUENCE = (\[.*?\]);', html, re.DOTALL)
assert match, 'index.html does not embed window.INITIAL_SEQUENCE'
embedded = json.loads(match.group(1))
assert [it['id'] for it in embedded] == ['row_1', 'row_2'], embedded
assert embedded[0]['secondary_flag_image'] == 'ilca7.png', embedded
assert embedded[1]['grid_index'] == 2, embedded
print('RO page embeds the live server sequence (rows, flags, grids)')

# --- 2. empty sequence embeds [] (restore is a no-op on a fresh session) ---
m.app_state['sequence'] = []
resp = client.get('/')
html = resp.get_data(as_text=True)
match = re.search(r'window\.INITIAL_SEQUENCE = (\[.*?\]);', html, re.DOTALL)
assert match and json.loads(match.group(1)) == [], 'empty sequence must embed []'
print('fresh session embeds [] - restore stays a no-op')

# --- 3. app.js restores the sequence on page load ---
with open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8') as f:
    js = f.read()
assert 'function restoreSequenceFromServer()' in js, 'restore function missing'
assert 'window.INITIAL_SEQUENCE' in js, 'restore does not read the embedded sequence'
assert 'restoreSequenceFromServer();' in js, 'restore function is never called'
dom_ready = js[js.index("document.addEventListener('DOMContentLoaded'"):]
assert 'restoreSequenceFromServer();' in dom_ready.split('\n\n')[0] or \
       dom_ready.index('restoreSequenceFromServer();') < 200, \
    'restore must run at page load, before other setup'
# The restore must rebuild secondary/tertiary flag boxes too (max 3 flags)
assert 'secondary_flag_image' in js[js.index('function restoreSequenceFromServer'):js.index('function restoreSequenceFromServer') + 3000], \
    'restore must repaint the secondary flag box'
assert 'tertiary_flag_image' in js[js.index('function restoreSequenceFromServer'):js.index('function restoreSequenceFromServer') + 3000], \
    'restore must repaint the tertiary flag box'
print('app.js rebuilds grids + rows (+2nd/3rd flags) from the embedded sequence on load')

os.remove(SCRATCH)
print()
print('PASS bug 31: RO page keeps its flags and settings across navigation/refresh'
      ' (browser test: build a sequence, open Finish Sheet 1, click'
      ' "Race Officer Control" - the grids must still be there)')
