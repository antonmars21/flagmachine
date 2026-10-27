"""Regression test for the Sailwave CSV export (features 6 + 7, bug doc items
6 and 7).

- Default export is a direct-Sailwave-import CSV: header named with the
  club's Sailwave conventions (Fleet, Class, SailNo, HelmName, Handicap)
  plus result columns (Race, StartTime, FinishTime, Elapsed, Laps).
- Elapsed is mm:ss.s (club convention) computed from finish - class start.
- Filename is named by the regatta/series matched from the HYC race
  calendar by the race date (monkeypatched here for determinism);
  no calendar match falls back to race_<id>_results.csv.
- ?format=detailed keeps the legacy human-readable layout.

Runs against a scratch copy of score.db - real DB untouched.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_sailwave.db'
shutil.copy('score.db', SCRATCH)
import app as app_module
app_module.DB_PATH = SCRATCH

conn = sqlite3.connect(SCRATCH)
c = conn.cursor()
c.execute("INSERT INTO races (start_time, status) VALUES (?, 'RUNNING')",
          (datetime.now().isoformat(),))
race_id = c.lastrowid

# Two sailors: one finished with laps, one not finished
c.execute("INSERT INTO race_sailors (race_id, uid, lap_count) VALUES (?, 'SL-1091', 1)", (race_id,))
c.execute("INSERT INTO race_sailors (race_id, uid, lap_count) VALUES (?, 'SL-955', 0)", (race_id,))
start_iso = datetime.now().isoformat()
finish_iso = (datetime.now() + timedelta(minutes=32, seconds=56.3)).isoformat()
class_row = c.execute("SELECT class_id FROM boat_classes WHERE class_name LIKE '%Starling%'").fetchone()
if not class_row:
    class_row = c.execute("SELECT class_id FROM boat_classes LIMIT 1").fetchone()
class_id = class_row[0]
c.execute("INSERT INTO race_class_starts (race_id, class_id, start_time, sequence_number) VALUES (?, ?, ?, 1)",
          (race_id, class_id, start_iso))
c.execute("UPDATE race_sailors SET finish_time = ? WHERE race_id = ? AND uid = 'SL-1091'",
          (finish_iso, race_id))
c.execute("INSERT INTO lap_records (race_id, uid, lap_number, timestamp) VALUES (?, 'SL-1091', 1, ?)",
          (race_id, start_iso))
conn.commit()
conn.close()

app_module.app_state['race_id'] = race_id
app_module.app_state['class_start_times'] = {str(class_id): start_iso}

conn = sqlite3.connect(SCRATCH)
meta = dict(conn.execute("SELECT uid, sailor_name FROM sailors WHERE uid IN ('SL-1091','SL-955')").fetchall())
cls = conn.execute("SELECT class_name FROM boat_classes WHERE class_id = ?", (class_id,)).fetchone()[0]
conn.close()

# Deterministic regatta name (calendar lookup itself is covered by
# test_calendar.py). Both lookup paths are patched: the Race column now
# carries the race number WITHIN the series (incremental across the season),
# not the DB race id.
_today = datetime.now().date()
app_module.get_calendar_event_for_date = lambda d, calendar_path=None: 'Twilight Series club racing'
app_module._calendar_events_by_date = lambda calendar_path=None: {_today: 'Twilight Series club racing'}

client = app_module.app.test_client()
resp = client.get('/api/export-race-csv')
body = resp.get_data(as_text=True)
disposition = resp.headers.get('Content-Disposition', '')
print('HTTP', resp.status_code)
print('Content-Disposition:', disposition)
print(body)

# --- Sailwave import format (feature 7) ---
assert resp.status_code == 200
assert 'Twilight%20Series%20club%20racing' in disposition or 'Twilight Series club racing' in disposition, \
    f'filename not regatta-named: {disposition}'
lines = body.strip().splitlines()
header = lines[0]
for col in ('Fleet', 'Class', 'SailNo', 'HelmName', 'Handicap', 'Series', 'Race',
            'StartTime', 'FinishTime', 'Elapsed', 'Laps', 'LapTimes'):
    assert col in header, f'missing Sailwave column {col!r} in {header!r}'
assert 'Twilight Series club racing' in body, 'series name missing from the Series column'
row1 = next(l for l in lines[1:] if meta['SL-1091'] in l)
assert meta['SL-1091'] in row1, 'finished sailor missing (HelmName must be the full sailor name)'
assert '32:56' in row1, f'elapsed mm:ss.s missing from: {row1}'
assert ',Race 1,' in row1, f'series race number missing from: {row1}'
lap_clock = datetime.fromisoformat(start_iso).strftime('%H:%M:%S')
assert lap_clock in row1, f'lap time {lap_clock} missing from LapTimes column: {row1}'
assert cls in body, 'class missing from CSV'
assert len(lines) == 3, f'expected header + 2 sailors, got {len(lines)} lines'
print('PASS: Sailwave import CSV (columns, HelmName, elapsed, Series, race id, lap times)')

# --- filename fallback without a calendar match ---
app_module.get_calendar_event_for_date = lambda d, calendar_path=None: None
resp = client.get('/api/export-race-csv')
assert f'race_{race_id}_results.csv' in resp.headers.get('Content-Disposition', ''), resp.headers
print('PASS: filename falls back to race_<id>_results.csv without a calendar match')

# --- legacy detailed layout still available ---
resp = client.get('/api/export-race-csv?format=detailed')
body = resp.get_data(as_text=True)
assert 'Sequence' in body and 'Lap Times' in body, 'legacy detailed export broken'
conn = sqlite3.connect(SCRATCH)
short = dict(conn.execute("SELECT uid, short_name FROM sailors WHERE uid IN ('SL-1091','SL-955')").fetchall())
conn.close()
assert short['SL-1091'] in body, 'sailor missing from detailed export (legacy uses short_name)'
print('PASS: ?format=detailed keeps the legacy human-readable layout')

print('ALL SAILWAVE EXPORT CHECKS PASS')
