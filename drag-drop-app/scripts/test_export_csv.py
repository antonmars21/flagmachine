"""Regression test for /api/export-race-csv use-after-close bug.

Sets up a race with sailors and lap records on a temp copy of score.db,
then exports the CSV and checks it contains the expected rows.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

shutil.copy('score.db', 'tempref/score_test.db')
import app as app_module
app_module.DB_PATH = 'tempref/score_test.db'

conn = sqlite3.connect('tempref/score_test.db')
c = conn.cursor()
# Hermetic: the live registry is user-managed (old sailors get tidied away),
# so seed the sailors this test needs into the scratch copy
from scripts.seed_test_sailors import seed_fixture_sailors
seed_fixture_sailors(conn)
c.execute("INSERT INTO races (start_time, status) VALUES (?, 'RUNNING')", (datetime.now().isoformat(),))
race_id = c.lastrowid

# Two Starling sailors in the race, one with a lap
c.execute("INSERT INTO race_sailors (race_id, uid, lap_count) VALUES (?, 'SL-1091', 1)", (race_id,))
c.execute("INSERT INTO race_sailors (race_id, uid, lap_count) VALUES (?, 'SL-955', 0)", (race_id,))
class_id = c.execute("SELECT class_id FROM boat_classes WHERE class_name = 'Starling'").fetchone()[0]
c.execute("INSERT INTO race_class_starts (race_id, class_id, start_time, sequence_number) VALUES (?, ?, ?, 1)",
          (race_id, class_id, datetime.now().isoformat()))
c.execute("INSERT INTO lap_records (race_id, uid, lap_number, timestamp) VALUES (?, 'SL-1091', 1, ?)",
          (race_id, datetime.now().isoformat()))
conn.commit()
conn.close()

# Expected names come from the DB itself (registry gets refreshed from Sailwave,
# so hardcoding names here breaks the test whenever the fleet data changes).
# The default export is the Sailwave layout, whose HelmName is the FULL name.
conn = sqlite3.connect('tempref/score_test.db')
names = dict(conn.execute("SELECT uid, sailor_name FROM sailors WHERE uid IN ('SL-1091', 'SL-955')"))
conn.close()

app_module.app_state['race_id'] = race_id
app_module.app_state['class_start_times'] = {str(class_id): datetime.now().isoformat()}

client = app_module.app.test_client()
resp = client.get('/api/export-race-csv')
body = resp.get_data(as_text=True)
print('HTTP', resp.status_code)
print(body)

assert resp.status_code == 200, f"export failed: {resp.status_code}"
assert names['SL-1091'] in body, 'sailor missing from CSV'
assert names['SL-955'] in body, 'sailor missing from CSV'
assert 'Starling' in body, 'class missing from CSV'
print('PASS: export-race-csv returns full CSV without closed-database error')
