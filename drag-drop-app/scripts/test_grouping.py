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

# Assertions
cols = {col['class_name']: col for col in data['columns']}
starling = {s['short_name'] for s in cols.get('Starling', {}).get('sailors', [])}
ilca6 = {s['short_name'] for s in cols.get('Ilca 6', {}).get('sailors', [])}
optimist = {s['short_name'] for s in cols.get('Optimist', {}).get('sailors', [])}
open_cat = {s['short_name'] for s in cols.get('Open Category', {}).get('sailors', [])}

if starling != {'E. Harris', 'R. Feist'}:
    failures.append(f"Starling column wrong: {starling}")
if ilca6 != {'George', 'A. Coley'}:
    failures.append(f"Ilca 6 column wrong: {ilca6}")
if optimist:
    failures.append(f"Optimist column should be empty: {optimist}")
if open_cat != {'B. Smith', 'T. Liew'}:
    failures.append(f"Open Category wrong: {open_cat}")

if failures:
    print('FAIL:', failures)
    sys.exit(1)
print()
print('PASS: sailors grouped into 3 matching classes; unmatched in Open Category')
