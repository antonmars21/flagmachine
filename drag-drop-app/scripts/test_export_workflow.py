"""Kanban "Bug - export to csv failed" (2026-11-09):

1) Export must keep working AFTER End Race + Reset Finish Sheet - the reset
   clears the in-memory race_id, so /api/export-race-csv now falls back to the
   last recorded race (the endpoint has always been documented as
   "current/last race"; before, it returned 400 "No race to export" and the
   plain-navigation export button showed the RO a raw JSON error page).
2) Exports are NEVER ZIPped anymore: the results CSV is always a plain .csv
   download; the Sailwave series template is its own download via
   /api/export-series-template (previously the two files were ZIPped on
   calendar-matched race days, which broke the RO's import/publish flow).
3) /api/races lists past races (series, date, race number) for the export
   multi-select, and ?race_id=N exports a specific older race.

Regression coverage for the fix; run against a scratch copy of score.db.
"""

import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_export_wf.db'
shutil.copy('score.db', SCRATCH)

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False

from scripts.seed_test_sailors import seed_fixture_sailors
from scripts.export_helper import build_fixture_xlsx, get_results_csv

conn = sqlite3.connect(SCRATCH)
seed_fixture_sailors(conn)
# Hermetic: the live DB accumulates races; start from an empty race history
for table in ('capture_actions', 'lap_records', 'race_sailors',
              'race_class_starts', 'race_open_starts', 'races'):
    conn.execute(f'DELETE FROM {table}')
conn.execute("UPDATE sailors SET racing_today = 0")
starling_id = conn.execute("SELECT class_id FROM boat_classes WHERE class_name='Starling'").fetchone()[0]
uid = conn.execute("SELECT uid FROM sailors WHERE class_id=? LIMIT 1", (starling_id,)).fetchone()[0]


def make_race(start_iso):
    conn.execute("INSERT INTO races (status) VALUES ('ENDED')")
    rid = conn.execute("SELECT MAX(race_id) FROM races").fetchone()[0]
    conn.execute("INSERT INTO race_class_starts (race_id, class_id, start_time, source, sequence_number) "
                 "VALUES (?, ?, ?, 'flag_machine', 1)", (rid, starling_id, start_iso))
    conn.execute("INSERT INTO race_sailors (race_id, uid, lap_count, finish_time) VALUES (?, ?, 1, ?)",
                 (rid, uid, start_iso))
    return rid


# Fixture calendar: two Wednesdays in the same series
tempdir = tempfile.mkdtemp(prefix='exportwf_')
build_fixture_xlsx(os.path.join(tempdir, 'HYC Calendar fixture.xlsx'), [
    ('Wed 21 Oct 26', 0.75, 'Test Series club racing'),
    ('Wed 28 Oct 26', 0.75, 'Test Series club racing'),
])
m.SAILWAVE_DB_FOLDER = tempdir  # force the fixture calendar

race_old = make_race('2026-10-21T18:05:00')      # series R1
race_cal = make_race('2026-10-28T18:05:00')      # series R2
race_plain = make_race(datetime.now().isoformat())  # no calendar event, newest
conn.commit()
conn.close()

client = m.app.test_client()

# --- 1. active race export: plain CSV, never ZIP, series naming ------------
m.app_state['race_id'] = race_cal
m.app_state['race_ended'] = True
resp = client.get('/api/export-race-csv')
assert resp.status_code == 200, resp.get_data(as_text=True)
ct = resp.headers.get('Content-Type', '')
assert 'zip' not in ct and 'text/csv' in ct, f'must be plain CSV, got {ct}'
disp = resp.headers.get('Content-Disposition', '')
fname = re.search(r'filename=([^;]+)', disp).group(1).strip()
assert fname == 'Test Series club racing R2 28-10-2026.csv', fname
body = get_results_csv(resp)
assert body.splitlines()[1].split(',')[6] == 'Race 2', 'series race number'
assert 'Test Series club racing' in body.splitlines()[1], 'Series column filled'
print(f'PASS: active race exports plain CSV (no ZIP): {fname}')

# --- 2. after Reset Finish Sheet (race_id cleared) export still works ------
m.app_state['race_id'] = None
resp = client.get('/api/export-race-csv')
assert resp.status_code == 200, f'export after reset must fall back to last race, got {resp.status_code} {resp.get_data(as_text=True)}'
assert 'text/csv' in resp.headers.get('Content-Type', '')
fname = re.search(r'filename=([^;]+)', resp.headers.get('Content-Disposition', '')).group(1).strip()
assert fname == f'race_{race_plain}_results.csv', fname  # newest race
print(f'PASS: after reset, export falls back to the last race: {fname}')

# --- 3. ?race_id= exports an older race (amendment flow) -------------------
resp = client.get(f'/api/export-race-csv?race_id={race_old}')
assert resp.status_code == 200
fname = re.search(r'filename=([^;]+)', resp.headers.get('Content-Disposition', '')).group(1).strip()
assert fname == 'Test Series club racing 21-10-2026.csv', fname
assert get_results_csv(resp).splitlines()[1].split(',')[6] == 'Race 1'
resp = client.get('/api/export-race-csv?race_id=999999')
assert resp.status_code == 400, 'unknown race_id must 400'
print(f'PASS: ?race_id= exports older races ({fname}); unknown id -> 400')

# --- 4. series template is its own download --------------------------------
resp = client.get(f'/api/export-series-template?race_id={race_cal}')
assert resp.status_code == 200 and 'text/csv' in resp.headers.get('Content-Type', '')
assert 'RaceNo' in resp.get_data(as_text=True)
assert 'Test Series club racing' in resp.get_data(as_text=True)
resp = client.get(f'/api/export-series-template?race_id={race_plain}')
assert resp.status_code == 404, 'no series on a non-calendar date -> 404'
print('PASS: /api/export-series-template returns the template CSV alone (404 without a series)')

# --- 5. /api/races lists past races for the multi-select --------------------
resp = client.get('/api/races')
data = resp.get_json()
assert data['status'] == 'success'
labels = {r['race_id']: r for r in data['races']}
assert set(labels) >= {race_old, race_cal, race_plain}
assert labels[race_cal]['series'] == 'Test Series club racing'
assert labels[race_cal]['race_number'] == 2
assert labels[race_plain]['series'] == ''
assert '#' in labels[race_old]['label'] and '21-10-2026' in labels[race_old]['label']
print('PASS: /api/races lists races with series/date/race number labels:', labels[race_cal]['label'])

# --- 6. no races at all -> friendly 400 JSON (not an HTML error page) -------
conn = sqlite3.connect(SCRATCH)
for table in ('capture_actions', 'lap_records', 'race_sailors',
              'race_class_starts', 'race_open_starts', 'races'):
    conn.execute(f'DELETE FROM {table}')
conn.commit()
conn.close()
m.app_state['race_id'] = None
resp = client.get('/api/export-race-csv')
assert resp.status_code == 400 and resp.get_json()['message'] == 'No race to export'
print('PASS: empty race history -> 400 JSON "No race to export"')

# --- 7. frontend wiring ------------------------------------------------------
with open(os.path.join(ROOT, 'static', 'js', 'finishsheet.js'), encoding='utf-8') as f:
    fs = f.read()
assert "fetch('/api/races')" in fs, 'export modal must load the race list'
assert 'downloadBlob' in fs and '/api/export-race-csv?race_id=' in fs, 'export must download per selected race'
assert "window.location.href = '/api/export-race-csv'" not in fs, 'no more plain navigation export'
end = fs[fs.index('async function endRace'):]
end = end[:end.index('\n}\n')]
assert '/api/export-race-csv?race_id=' in end and '/api/export-series-template?race_id=' in end, \
    'End Race must auto-download both files'
assert fs.count('{') == fs.count('}'), 'finishsheet.js brace imbalance'
with open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8') as f:
    ajs = f.read()
assert 'downloadBlob' in ajs and '/api/export-series-template?race_id=' in ajs, 'RO End Race must auto-download'
assert ajs.count('{') == ajs.count('}'), 'app.js brace imbalance'
print('PASS: finishsheet.js + app.js wiring (multi-select export, End Race auto-download, no ZIP path)')

shutil.rmtree(tempdir)
os.remove(SCRATCH)
print('\nPASS kanban "export to csv failed": export works after reset, plain CSV only, template separate, past-race select')
