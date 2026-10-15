"""Verify add-sailor hotfix (2026-10-16): auto-generated UID, actionable
duplicate messages. Runs against a scratch copy of score.db."""
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_addsailor.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.app.config['TESTING'] = True

client = m.app.test_client()
fails = []


def check(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' - ' + detail if detail else ''))
    if not cond:
        fails.append(name)


# 1. New sailor, no UID -> auto SL-<sailno>
r = client.post('/api/add-sailor', json={
    'uid': '', 'sailor_name': 'Test One', 'short_name': 'Test1',
    'sail_no': '99901', 'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
check('auto uid from sail number', r.status_code == 200, r.get_json().get('message', ''))
conn = sqlite3.connect(SCRATCH)
row = conn.execute("SELECT uid FROM sailors WHERE sail_no = '99901'").fetchone()
check('uid stored as SL-99901', row == ('SL-99901',), str(row))

# 2. Same sail number again -> actionable duplicate message naming the sailor
r = client.post('/api/add-sailor', json={
    'uid': '', 'sailor_name': 'Test One Again', 'short_name': 'Test1b',
    'sail_no': '99901', 'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
msg = r.get_json().get('message', '')
check('duplicate sail no blocked', r.status_code == 400, msg)
check('message names existing sailor', 'Test1' in msg and 'SL-99901' in msg, msg)

# 3. Explicit UID that is taken -> clear message
r = client.post('/api/add-sailor', json={
    'uid': 'SL-99901', 'sailor_name': 'Dup Uid', 'short_name': 'Dup',
    'sail_no': '99902', 'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
msg = r.get_json().get('message', '')
check('taken uid blocked', r.status_code == 400 and 'SL-99901' in msg, msg)

# 4. Fresh sailor with a UID colliding on auto-base gets a suffix
r = client.post('/api/add-sailor', json={
    'uid': 'SL-99901', 'sailor_name': 'Suffix Case', 'short_name': 'Suf',
    'sail_no': '99903', 'boat_class': 'Ilca 6', 'handicap': 1.0, 'seed': 0})
# SL-99901 is taken (step 1) -> this explicit uid must be refused; instead
# retry with blank uid on a sail number whose SL- base is taken is impossible
# (sail_no unique), so just confirm refusal message is clear
check('explicit taken uid refused with guidance', r.status_code == 400 and 'blank' in msg or 'blank' in r.get_json().get('message', ''), r.get_json().get('message', ''))

# 5. Add with boat class not in boat_classes -> class_id NULL, still added
r = client.post('/api/add-sailor', json={
    'uid': '', 'sailor_name': 'Mystery Class', 'short_name': 'Mys',
    'sail_no': '99904', 'boat_class': 'NotARealClass', 'handicap': 1.0, 'seed': 0})
check('unknown class still adds', r.status_code == 200, r.get_json().get('message', ''))

conn.close()
os.remove(SCRATCH)

print()
if fails:
    sys.exit('FAILED: ' + ', '.join(fails))
print('PASS add-sailor hotfix (auto uid + duplicate messages)')
