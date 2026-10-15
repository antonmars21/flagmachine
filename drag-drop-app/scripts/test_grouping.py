"""Simulate a 3-flag start sequence and verify finish-sheet grouping.

Uses a copy of score.db so the real database is untouched, then checks:
- sailors land in the column matching their class flag
- unmatched sailors land in the Open Category
"""
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Work in a temp copy so the real DB stays untouched
shutil.copy('score.db', 'tempref/score_test.db')
import app as app_module
app_module.DB_PATH = 'tempref/score_test.db'

# Sign on a test set: 2 Starling, 2 Ilca 6, 1 Zephyr (no flag in sequence), 1 Frostbite (no flag image)
test_uids = ['SL-1091', 'SL-955',          # Starling
             'SL-15', 'SL-18789',          # Ilca 6
             'SL-12',                     # Zephyr
             'SL-141']                    # Frostbite
conn = sqlite3.connect('tempref/score_test.db')
c = conn.cursor()
c.execute('UPDATE sailors SET racing_today = 0')
for uid in test_uids:
    c.execute('UPDATE sailors SET racing_today = 1 WHERE uid = ?', (uid,))
conn.commit()
conn.close()

# Simulate the Flag Machine sequence: 3 separate starts with class flags
app_module.app_state['sequence'] = [
    {'label': 'Starling', 'flag_image': 'Starling.png', 'grid_index': 1},
    {'label': 'Ilca 6', 'flag_image': 'ilca6.png', 'grid_index': 2},
    {'label': 'Optimist', 'flag_image': 'optimist.png', 'grid_index': 3},
]

client = app_module.app.test_client()
resp = client.get('/api/sailors-for-onwater')
data = resp.get_json()

print('columns returned:', len(data['columns']))
failures = []
for col in data['columns']:
    sailors = [(s['short_name'], s['boat_class']) for s in col['sailors']]
    print(f"  seq {col['sequence_number']}: {col['class_name']:15} -> {sailors}")

# Assertions - expected grouping is derived from the DB itself (registry gets
# refreshed from Sailwave, so hardcoding names/classes here breaks the test)
conn = sqlite3.connect('tempref/score_test.db')
expected_col_of_uid = {}
for uid in test_uids:
    row = conn.execute('''
        SELECT bc.class_name FROM sailors s
        LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
        WHERE s.uid = ?''', (uid,)).fetchone()
    expected_col_of_uid[uid] = row[0] if row and row[0] else None
conn.close()

sequence_classes = {'Starling', 'Ilca 6', 'Optimist'}
cols = {col['class_name']: col for col in data['columns']}
uid_col = {}
for col_name, col in cols.items():
    for s in col['sailors']:
        uid_col.setdefault(s['uid'], col_name)

for uid in test_uids:
    class_name = expected_col_of_uid[uid]
    want = class_name if class_name in sequence_classes else 'Open Category'
    got = uid_col.get(uid)
    if got != want:
        failures.append(f"{uid} ({class_name or 'no class'}): expected {want}, got {got}")

# Classes in the sequence with no sailors must still show an (empty) column
for col_name in sequence_classes:
    if col_name not in cols:
        failures.append(f"missing column: {col_name}")

if failures:
    print('FAIL:', failures)
    sys.exit(1)
print()
print('PASS: sailors grouped into 3 matching classes; unmatched in Open Category')
