"""Verify the bug 27 fix: race state recovery after a mid-race restart.

Bug 27: race state (race_id, class_start_times, open_start_time) lives only in
app_state, so a mid-race server restart orphaned the RUNNING race in the DB -
the finish sheet's manual Start Race then created a DUPLICATE race (24 Oct:
race 67 stayed RUNNING while duplicate race 68 was started and ended), and the
real race could never be ended or exported.

recover_running_race() runs at app start:
- a RUNNING race with activity in the last 12h is ADOPTED back into app_state
  (end-race / laps / export then target the live race), and
- older RUNNING races (abandoned crash, nobody pressed End Race) are closed
  as ENDED so they stop blocking the new session.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b27.db'
shutil.copy('score.db', SCRATCH)

now = datetime.now()
recent_iso = now.isoformat()
stale_iso = (now - timedelta(days=2)).isoformat()

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
# A class id to start (Ilca 6)
ilca6_id = conn.execute(
    "SELECT class_id FROM boat_classes WHERE flag_image = 'ilca6.png'").fetchone()
if ilca6_id:
    ilca6_id = ilca6_id[0]
    conn.execute("UPDATE sailors SET racing_today = 1 WHERE class_id = ?", (ilca6_id,))
ilca6_uid = conn.execute(
    "SELECT uid FROM sailors WHERE class_id = ? LIMIT 1", (ilca6_id,)).fetchone()[0]
# Clean any pre-existing RUNNING races so the test controls the scenario
conn.execute("UPDATE races SET status = 'ENDED' WHERE status = 'RUNNING'")
# Recent RUNNING race (mid-race restart scenario): started minutes ago, 1 lap
conn.execute("INSERT INTO races (status, created_at) VALUES ('RUNNING', ?)",
             (recent_iso,))
recent_race = conn.execute("SELECT MAX(race_id) FROM races").fetchone()[0]
conn.execute("INSERT INTO race_class_starts (race_id, class_id, start_time, source, sequence_number) "
             "VALUES (?, ?, ?, 'flag_machine', 1)", (recent_race, ilca6_id, recent_iso))
conn.execute("INSERT INTO race_sailors (race_id, uid, lap_count, placement) VALUES (?, ?, 1, NULL)",
             (recent_race, ilca6_uid))
conn.execute("INSERT INTO lap_records (race_id, uid, lap_number, timestamp) VALUES (?, ?, 1, ?)",
             (recent_race, ilca6_uid, recent_iso))
# Stale RUNNING race (abandoned days ago, e.g. Saturday's orphan)
conn.execute("INSERT INTO races (status, created_at) VALUES ('RUNNING', ?)",
             (stale_iso,))
stale_race = conn.execute("SELECT MAX(race_id) FROM races").fetchone()[0]
conn.execute("INSERT INTO race_class_starts (race_id, class_id, start_time, source, sequence_number) "
              "VALUES (?, ?, ?, 'flag_machine', 1)", (stale_race, ilca6_id, stale_iso))
conn.commit()
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False

# --- 1. recovery adopts the recent race and closes the stale one ---
adopted = m.recover_running_race()
assert adopted == recent_race, f"expected recent race {recent_race} adopted, got {adopted}"
assert m.app_state['race_id'] == recent_race, "app_state race_id not recovered"
assert str(ilca6_id) in m.app_state['class_start_times'], "class start times not recovered"
assert m.app_state['race_ended'] is False
assert m.app_state['status'] == 'RUNNING'
print("recent RUNNING race adopted into app_state (race_id + class starts)")

conn = sqlite3.connect(SCRATCH)
status = conn.execute("SELECT status, end_time FROM races WHERE race_id = ?", (stale_race,)).fetchone()
assert status[0] == 'ENDED', f"stale race should be ENDED, got {status}"
assert status[1] == stale_iso, f"stale race end_time should freeze at last activity, got {status[1]}"
still_running = conn.execute("SELECT COUNT(*) FROM races WHERE status = 'RUNNING'").fetchone()[0]
assert still_running == 1, f"expected exactly 1 RUNNING race left, got {still_running}"
conn.close()
print("stale RUNNING race (2 days old) closed as ENDED at its last activity time")

# --- 2. end-race works on the recovered race (no duplicate race created) ---
client = m.app.test_client()
resp = client.post('/api/end-race')
assert resp.status_code == 200, resp.get_data(as_text=True)
conn = sqlite3.connect(SCRATCH)
row = conn.execute("SELECT status FROM races WHERE race_id = ?", (recent_race,)).fetchone()
assert row[0] == 'ENDED', "recovered race was not ended by /api/end-race"
conn.close()
print("end-race ends the recovered race directly (no duplicate race needed)")

# --- 3. reset-finish-sheet is unblocked after ending the recovered race ---
resp = client.post('/api/reset-finish-sheet')
assert resp.status_code == 200, resp.get_data(as_text=True)
print("reset-finish-sheet works after the recovered race is ended")

# --- 4. with no RUNNING races, recovery is a no-op ---
m.app_state['race_id'] = None
m.app_state['class_start_times'] = {}
assert m.recover_running_race() is None
assert m.app_state['race_id'] is None
print("no RUNNING races in DB -> recovery is a no-op (fresh session starts clean)")

os.remove(SCRATCH)
print()
print("PASS bug 27: mid-race restart recovers the RUNNING race; stale orphans are closed")
