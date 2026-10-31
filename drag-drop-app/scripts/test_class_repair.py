"""Bugs 33/34: sailors must group into the class their FLAG names, not Open
Category - even when the class row was missing from boat_classes.

RO report 2026-10-29: the Ilca 4 flag (ilca4.png) was visibly in the start
event box, yet Ilca 4 sailors loaded into Open Category. Root cause (data
half): boat_classes had NO 'Ilca 4' row - manually added sailors (add/edit
sailor never created class rows; only the Sailwave import did) carried
class_id NULL. The start-sequence -> column lookup matches boat_classes by
flag_image, so the dragged ilca4.png matched NOTHING: no Ilca 4 column was
created and the sailors grouped into Open Category.

Fix:
- repair_missing_boat_classes() (startup, next to reconcile_class_flag_images):
  every distinct sailors.boat_class without a boat_classes row gets one
  (flag auto-matched from the class flag folder), and NULL sailors.class_id
  values are linked to it.
- ensure_boat_class_id(): add-sailor/edit-sailor get-or-create the class, so
  this can never regress from manual entries again.
- find_class_flag_image(): class flags only - signal flags can never attach
  to a class, and openclass.png can never be a boat class flag (Open
  Category is a virtual column).
"""
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b34.db'
shutil.copy('score.db', SCRATCH)

# Seed stranded sailors: class rows exist for none of these two classes
conn = sqlite3.connect(SCRATCH)
c = conn.cursor()
c.execute("DELETE FROM boat_classes WHERE LOWER(class_name) IN ('ilca 4', 'europe')")
c.execute("DELETE FROM sailors WHERE uid IN ('SL-1004', 'SL-KZ-29', 'SL-NEW1', 'SL-EDIT1')")
c.execute("""INSERT INTO sailors (uid, sailor_name, short_name, sail_no, boat_class,
             handicap, seed, class_id, racing_today, status)
             VALUES ('SL-1004', 'Test Ilca4', 'TestI4', '1004', 'Ilca 4', 1.0, 0, NULL, 1, 'racing')""")
c.execute("""INSERT INTO sailors (uid, sailor_name, short_name, sail_no, boat_class,
             handicap, seed, class_id, racing_today, status)
             VALUES ('SL-KZ-29', 'Test Europe', 'TestEu', 'KZ-29', 'Europe', 1.0, 0, NULL, 1, 'racing')""")
conn.commit()
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
client = m.app.test_client()

# --- 1. the startup repair heals the missing classes + links the sailors ---
m.repair_missing_boat_classes()
conn = sqlite3.connect(SCRATCH)
c = conn.cursor()
ilca4 = c.execute("SELECT class_id, flag_image FROM boat_classes WHERE LOWER(class_name) = 'ilca 4'").fetchone()
assert ilca4 and ilca4[1] and ilca4[1].lower() == 'ilca4.png', \
    f"'Ilca 4' class must be created with the ilca4.png flag, got {ilca4}"
link = c.execute("SELECT class_id FROM sailors WHERE uid = 'SL-1004'").fetchone()
assert link and link[0] == ilca4[0], 'Ilca 4 sailor not linked to the new class'
europe = c.execute("SELECT flag_image FROM boat_classes WHERE LOWER(class_name) = 'europe'").fetchone()
assert europe, "'Europe' class row must exist too"
assert not europe[0], 'Europe has no flag image - flag_image must stay NULL'
conn.close()
print('PASS: repair creates missing classes (Ilca 4 with ilca4.png) and links sailors')

# --- 2. the Ilca 4 flag in the sequence now creates a REAL Ilca 4 column ---
client.post('/update-sequence', json={'sequence': [
    {'id': 'r1', 'label': 'Ilca 4', 'flag_image': 'ilca4.png', 'grid_index': 1, 'countdown_minutes': 1},
]})
cols = {col['class_name']: col for col in
        client.get('/api/sailors-for-onwater').get_json()['columns']}
assert 'Ilca 4' in cols, f"no Ilca 4 column - got {list(cols)}"
assert 'SL-1004' in [s['uid'] for s in cols['Ilca 4']['sailors']], 'Ilca 4 sailor missing from the Ilca 4 column'
open_uids = [s['uid'] for s in cols.get('Open Category', {}).get('sailors', [])]
assert 'SL-1004' not in open_uids, 'Ilca 4 sailor still in Open Category'
assert 'SL-KZ-29' in open_uids, 'flagless-class sailor (Europe) must stay Open Category'
print('PASS: ilca4.png flag -> Ilca 4 column; Ilca 4 sailors in it, Europe stays Open')

# --- 3. class-start fires for the new class like any other ---
r = client.post('/api/class-start', json={'flag_image': 'ilca4.png', 'sequence_number': 1})
assert r.status_code == 200, f'class-start rejected for the created class: {r.get_json()}'
conn = sqlite3.connect(SCRATCH)
starts = conn.execute("""SELECT bc.class_name FROM race_class_starts rcs
                         JOIN boat_classes bc ON bc.class_id = rcs.class_id""").fetchall()
conn.close()
assert ('Ilca 4',) in starts, 'class start not recorded for Ilca 4'
print('PASS: class-start works for the repaired Ilca 4 class')

# --- 4. add/edit sailor now get-or-create the class (no more stranded sailors) ---
r = client.post('/api/add-sailor', json={
    'sailor_name': 'Brand New', 'short_name': 'NewB', 'sail_no': '9999',
    'boat_class': 'Zephyr X'})
assert r.status_code == 200, r.get_json()
conn = sqlite3.connect(SCRATCH)
row = conn.execute("""SELECT bc.class_id, bc.flag_image FROM sailors s
                      JOIN boat_classes bc ON bc.class_id = s.class_id
                      WHERE s.uid = 'SL-9999'""").fetchone()
conn.close()
assert row, 'add-sailor must create the class AND link the sailor (bugs 33/34)'
assert row[1] is None, 'Zephyr X has no flag image on disk - flag must be NULL'
print('PASS: add-sailor creates a missing class and links the sailor')

r = client.put('/api/edit-sailor/SL-1004', json={
    'sailor_name': 'Test Ilca4', 'short_name': 'TestI4', 'sail_no': '1004',
    'boat_class': 'Ilca 7', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, r.get_json()
conn = sqlite3.connect(SCRATCH)
row = conn.execute("""SELECT bc.class_name FROM sailors s
                      JOIN boat_classes bc ON bc.class_id = s.class_id
                      WHERE s.uid = 'SL-1004'""").fetchone()
conn.close()
assert row and row[0] == 'Ilca 7', 'edit-sailor must re-link to the target class'
print('PASS: edit-sailor re-links the sailor (existing class)')

# --- 5. guards: openclass.png is never a class flag; P vs P Class intact ---
conn = sqlite3.connect(SCRATCH)
bad = conn.execute("SELECT class_name FROM boat_classes WHERE LOWER(flag_image) = 'openclass.png'").fetchall()
assert not bad, f'openclass.png must never attach to a boat class: {bad}'
pclass = conn.execute("SELECT flag_image FROM boat_classes WHERE class_name = 'P Class'").fetchone()
assert pclass and pclass[0].lower() == 'pclass.png', 'P Class flag regressed'
sig = conn.execute("SELECT class_name FROM boat_classes WHERE LOWER(flag_image) IN ('p.png', 'dflag.png')").fetchall()
assert not sig, f'signal flag attached to a boat class: {sig}'
conn.close()
print('PASS: openclass.png never a class flag; P Class = pclass.png; signal flags clean')

# idempotent: a second repair run must be a no-op
m.repair_missing_boat_classes()
print('PASS: repair is idempotent (second run is a no-op)')

os.remove(SCRATCH)
print('\nPASS bugs 33/34: missing classes self-heal, flag in the start box = proper class column')
