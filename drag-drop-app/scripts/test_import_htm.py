"""Verify the 'Import Sailwave sailors' source: the button reads the Sailwave
boat_master.htm HTML export (preferred) with Boats_Master.xml as fallback.

- parse_sailwave_htm reads the competitor table (Fleet, Class, Boat, SailNo,
  HelmName, Handicap) and produces the same boat shape as the XML parser.
- import_sailwave_data imports an HTM source into a scratch DB.
- find_sailwave_source prefers boat_master.htm over Boats_Master.xml.

Runs against a scratch copy of score.db - real DB untouched.
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
os.chdir(ROOT)

HTM = 'tempref/boat_master.htm'
assert os.path.exists(HTM), 'tempref/boat_master.htm is needed for this test'

from import_sailwave import parse_sailwave_htm, extract_boat_info, import_sailwave_data

# --- 1. Parse the HTM competitor table
boats, classes = parse_sailwave_htm(HTM)
assert boats and len(boats) >= 50, 'expected 50+ competitors, got %s' % len(boats)
assert classes == []
by_sail = {b['compsailno']: b for b in boats}
assert '244' in by_sail, 'sail 244 (3.7) expected in the export'
b244 = by_sail['244']
assert b244['comphelmname'] == 'Lucas Hennig', b244
assert b244['compclass'] == '3.7', b244
b15 = by_sail['15']
assert b15['comphelmname'] == 'George Lane' and b15['compclass'] == 'ILCA 6', b15
print('PASS: boat_master.htm parsed - %d competitors, spot checks OK' % len(boats))

# --- 2. extract_boat_info maps HTM fields exactly like the XML fields
info = extract_boat_info(b15)
assert info['uid'] == 'SL-15', info
assert info['short_name'] == 'George', info
assert info['boat_class'] == 'ILCA 6', info
assert info['sail_no'] == '15', info
print('PASS: extract_boat_info maps HTM fields (uid, short_name, class, sail_no)')

# --- 3. Full import into a scratch DB
SCRATCH = 'tempref/score_htm_test.db'
shutil.copy('score.db', SCRATCH)
ok = import_sailwave_data(HTM, SCRATCH)
assert ok is True, 'import from HTM failed'

import sqlite3
conn = sqlite3.connect(SCRATCH)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT uid, short_name, boat_class FROM sailors WHERE uid = 'SL-15'").fetchone()
assert row and row['short_name'] == 'George', dict(row) if row else 'SL-15 missing'
count = conn.execute('SELECT COUNT(*) FROM sailors').fetchone()[0]
conn.close()
os.remove(SCRATCH)
print('PASS: import from boat_master.htm into scratch DB - %d sailors in DB' % count)

# --- 4. find_sailwave_source prefers the HTM over the XML
import app as m
src = m.find_sailwave_source()
assert src is not None, 'no Sailwave source found'
assert src.lower().endswith(('.htm', '.html')), \
    'boat_master.htm must be preferred, got %s' % src
print('PASS: find_sailwave_source prefers boat_master.htm (%s)' % src)

print()
print('PASS Import Sailwave sailors: boat_master.htm is the import source')
