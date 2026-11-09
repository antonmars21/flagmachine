"""Kanban "check sailor editing" (Dell): one sailor's details could be edited,
but a second edit to a DIFFERENT sailor could not be made - the RO wanted to set
John (Ilca 6) to sail number 224440, which John's other boat (Ilca 7) already
carries. One sail number across Ilca 4/6/7 is normal (same sailor, several
boats).

Root causes:
1. DATA/SCHEMA: sailors.sail_no was TEXT UNIQUE, so the second edit died with an
   uncaught sqlite3.IntegrityError -> HTTP 500 HTML page.
2. FRONTEND: the edit modal did `await response.json()` unconditionally - on a
   500 the parse threw, the catch only console.error'd, so the modal stayed open
   with NO message and blocked any further edit ("a second edit could not be
   made").

Fix (2026-11-05):
- migrate_sail_no_shared_across_classes() (app startup): rebuilds the sailors
  table without the UNIQUE constraint on sail_no (all rows/columns preserved).
  Uniqueness is now PER CLASS, enforced by add/edit-sailor with a friendly 400.
- /api/add-sailor + /api/edit-sailor: duplicate = same sail_no AND same class
  (case-insensitive); the same number in a different class is allowed.
  edit-sailor also catches IntegrityError -> 400 JSON.
- finishsheet.js: the save handler checks response.ok and always alerts the
  server's message (a 500 can never silently stick the modal again); modal
  field values are HTML-attribute-escaped.
- import_sailwave.py: fresh-DB schema matches (no UNIQUE on sail_no) and its
  duplicate check is class-aware too.
"""

import os
import re
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_sailno.db'
shutil.copy('score.db', SCRATCH)

# Recreate the OLD schema (sail_no TEXT UNIQUE) in the scratch copy, keeping all
# rows, so the migration itself is exercised deterministically whatever the
# live DB looks like.
conn = sqlite3.connect(SCRATCH)
c = conn.cursor()
c.execute('ALTER TABLE sailors RENAME TO sailors_keep')
cols = c.execute('PRAGMA table_info(sailors_keep)').fetchall()
defs = []
for col in cols:
    d = '"%s" %s' % (col[1], col[2] or 'TEXT')
    if col[1] == 'sail_no':
        d += ' UNIQUE'  # the legacy constraint
    if col[3]:
        d += ' NOT NULL'
    if col[4] is not None:
        d += ' DEFAULT %s' % col[4]
    if col[5]:
        d += ' PRIMARY KEY'
    defs.append(d)
c.execute('CREATE TABLE sailors (%s)' % ', '.join(defs))
c.execute('INSERT INTO sailors SELECT * FROM sailors_keep')
c.execute('DROP TABLE sailors_keep')
conn.commit()
before = c.execute('SELECT COUNT(*) FROM sailors').fetchone()[0]
# sanity: the legacy unique index really is there
uidx = [r[1] for r in c.execute('PRAGMA index_list(sailors)').fetchall() if r[2]]
legacy_unique_sailno = any(
    [r[2] for r in c.execute('PRAGMA index_info("%s")' % name).fetchall()] == ['sail_no']
    for name in uidx)
assert legacy_unique_sailno, 'scratch DB must start with the legacy UNIQUE(sail_no)'
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False

# --- 1. the migration rebuilds the table and drops UNIQUE(sail_no) ---
changed = m.migrate_sail_no_shared_across_classes()
assert changed is True, 'migration must report it rebuilt the legacy table'
conn = sqlite3.connect(SCRATCH)
c = conn.cursor()
after = c.execute('SELECT COUNT(*) FROM sailors').fetchone()[0]
assert after == before, f'rows lost in migration: {before} -> {after}'
uidx = [(r[1], r[2]) for r in c.execute('PRAGMA index_list(sailors)').fetchall() if r[2]]
assert not any([r[2] for r in c.execute('PRAGMA index_info("%s")' % name).fetchall()] == ['sail_no']
               for name, _ in uidx), 'UNIQUE index on sail_no alone must be gone'
assert any([r[2] for r in c.execute('PRAGMA index_info("%s")' % name).fetchall()] == ['uid']
           for name, _ in uidx), 'uid PRIMARY KEY must survive'
conn.close()
# idempotent
assert m.migrate_sail_no_shared_across_classes() is False, 'second run must be a no-op'
print('PASS: migration drops UNIQUE(sail_no), keeps uid PK + all rows, idempotent')

client = m.app.test_client()

# --- 2. add: same sail number in a DIFFERENT class is allowed ---
r = client.post('/api/add-sailor', json={
    'sailor_name': 'John Barnard', 'short_name': 'John', 'sail_no': '224440',
    'boat_class': 'Ilca 7', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, r.get_json()
r = client.post('/api/add-sailor', json={
    'sailor_name': 'John Barnard', 'short_name': 'JB', 'sail_no': '224440',
    'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, f'second class with the SAME sail_no must be allowed: {r.get_json()}'
conn = sqlite3.connect(SCRATCH)
rows = conn.execute("SELECT uid, sail_no, boat_class FROM sailors WHERE sail_no = '224440' ORDER BY uid").fetchall()
assert len(rows) == 2 and {r[2] for r in rows} == {'Ilca 7', 'Ilca 6'}, rows
assert rows[0][0] == 'SL-224440' and rows[1][0].startswith('SL-224440-'), \
    f'uid auto-suffix must keep uids unique: {rows}'
conn.close()
print('PASS: same sail number allowed across classes (uids stay unique: SL-224440, SL-224440-2)')

# --- 3. add: same sail number in the SAME class is still rejected, friendly ---
r = client.post('/api/add-sailor', json={
    'sailor_name': 'Copy Cat', 'short_name': 'Copy', 'sail_no': '224440',
    'boat_class': 'ilca 6', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 400, f'same-class duplicate must be rejected: {r.status_code} {r.get_json()}'
assert 'already in the registry' in r.get_json()['message']
print('PASS: same sail_no in the same class (any case) -> friendly 400')

# --- 4. edit: set John Ilca 6 to the shared number (the kanban case) ---
r = client.put('/api/edit-sailor/SL-224440-2', json={
    'sailor_name': 'John Barnard', 'short_name': 'JB', 'sail_no': '224440',
    'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 200, f'edit to the shared number must succeed: {r.get_json()}'
# a second edit to a DIFFERENT sailor right after must also work
r = client.put('/api/edit-sailor/SL-224440', json={
    'sailor_name': 'John Barnard', 'short_name': 'John', 'sail_no': '224440',
    'boat_class': 'Ilca 7', 'handicap': 1.0, 'seed': 5})
assert r.status_code == 200, f'second edit to a different sailor must succeed: {r.get_json()}'
conn = sqlite3.connect(SCRATCH)
seed = conn.execute("SELECT seed FROM sailors WHERE uid = 'SL-224440'").fetchone()[0]
assert seed == 5, 'edit must have been applied'
conn.close()
print('PASS: back-to-back edits to different sailors both succeed (shared number kept)')

# --- 5. edit: moving a sailor into a class where the number is taken -> 400, no change ---
r = client.put('/api/edit-sailor/SL-224440-2', json={
    'sailor_name': 'John Barnard', 'short_name': 'JB', 'sail_no': '224440',
    'boat_class': 'Ilca 7', 'handicap': 1.0, 'seed': 0})
assert r.status_code == 400, f'same-class collision on edit must be a friendly 400: {r.status_code}'
assert 'already used by' in r.get_json()['message']
conn = sqlite3.connect(SCRATCH)
cls = conn.execute("SELECT boat_class FROM sailors WHERE uid = 'SL-224440-2'").fetchone()[0]
assert cls == 'Ilca 6', f'rejected edit must not change the row (still Ilca 6, got {cls})'
conn.close()
print('PASS: edit colliding within one class -> friendly 400, row unchanged')

# --- 6. frontend: a failed save must alert, never stick the modal silently ---
with open(os.path.join(ROOT, 'static', 'js', 'finishsheet.js'), encoding='utf-8') as f:
    js = f.read()
save = js[js.index("overlay.querySelector('#modal-save')"):]
save = save[:save.index("overlay.querySelector('#modal-delete')")]
assert 'response.ok' in save, 'edit save must check response.ok before trusting the JSON'
assert 'alert(' in save, 'edit save failure must alert the user'
assert 'escAttr(' in js and 'value="${escAttr(sailor.sail_no)}"' in js, \
    'modal field values must be attribute-escaped'
assert js.count('{') == js.count('}'), 'finishsheet.js brace imbalance'
print('PASS: finishsheet.js edit modal alerts on any failure and escapes values')

os.remove(SCRATCH)
print('\nPASS kanban "check sailor editing": sail numbers shareable across classes, per-class uniqueness enforced with clear errors')
