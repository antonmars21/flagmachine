"""Verify the export naming fix (bug 29 + series race numbering).

The Sailwave CSV export names the file by the series matched from the HYC
race calendar and fills the Series column. Gaps found after the
24 Oct Dell results:
- the Dell had no calendar in its Sailwave folder, so every export silently
  fell back to race_<id>_results.csv with an empty Series column (the
  calendar now also ships in the app folder as a fallback);
- the Race column used the DB race id, but Sailwave needs the race number
  WITHIN the series, incremental across the whole season (Twilight Series
  runs R1, R2, ... every Wednesday over the weeks), not per day and not the
  DB id. The filename R-suffix uses the same series race number, so the
  day's races never overwrite each other either.
"""
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SCRATCH = 'tempref/score_b29.db'
WEEKDAYS = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def cal_text(d):
    return f'{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {str(d.year)[2:]}'


def build_xlsx(path, rows):
    """rows: list of (date_text, time_text, event)."""
    M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    strings = []

    def enc(val):
        if val is None:
            return ''
        if isinstance(val, (int, float)):
            return ('n', val)
        if val not in strings:
            strings.append(val)
        return ('s', strings.index(val))

    body = []
    for r, (d, t, ev) in enumerate(rows, start=1):
        cells = ''
        for col, val in zip('ABC', (d, t, ev)):
            kind, v = enc(val)
            if kind == 'n':
                cells += f'<c r="{col}{r}"><v>{v}</v></c>'
            elif kind == 's':
                cells += f'<c r="{col}{r}" t="s"><v>{v}</v></c>'
        body.append(f'<row r="{r}">{cells}</row>')
    shared = ''.join(f'<si><t>{xml_escape(s)}</t></si>' for s in strings)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml',
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                    '<Default Extension="xml" ContentType="application/xml"/>'
                    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
                    '</Types>')
        z.writestr('_rels/.rels',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr('xl/workbook.xml',
                   f'<workbook xmlns="{M}"><sheets><sheet name="Cal" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
                   '</Relationships>')
        z.writestr('xl/sharedStrings.xml', f'<sst xmlns="{M}" count="{len(strings)}">{shared}</sst>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{M}"><sheetData>{"".join(body)}</sheetData></worksheet>')


shutil.copy('score.db', SCRATCH)
now = datetime.now()
week_ago = now - timedelta(days=7)

# Fixture calendar: the SAME series races last week AND today (cross-week
# incremental numbering, like Twilight every Wednesday); two days ago has no
# event (fallback path)
tempdir = tempfile.mkdtemp(prefix='b29cal_')
cal = os.path.join(tempdir, 'HYC Calendar fixture.xlsx')
build_xlsx(cal, [
    (cal_text(week_ago.date()), 0.75, 'Test Series club racing'),
    (cal_text(now.date()), 0.75, 'Test Series club racing'),
    ('Sat 3 Jan 26', 0.75, 'Old Series club racing'),
])

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
conn.execute("UPDATE races SET status = 'ENDED' WHERE status = 'RUNNING'")
ilca6_id = conn.execute(
    "SELECT class_id FROM boat_classes WHERE flag_image = 'ilca6.png'").fetchone()[0]
ilca6_uid = conn.execute(
    'SELECT uid FROM sailors WHERE class_id = ? LIMIT 1', (ilca6_id,)).fetchone()[0]

# 1 race last week, 3 races today, 1 race two days ago (no calendar event)
race_ids = {}
for days_ago, n in ((7, 1), (0, 3), (2, 1)):
    start = (now - timedelta(days=days_ago)).isoformat()
    for _ in range(n):
        conn.execute("INSERT INTO races (status) VALUES ('ENDED')")
        rid = conn.execute("SELECT MAX(race_id) FROM races").fetchone()[0]
        conn.execute("INSERT INTO race_class_starts (race_id, class_id, start_time, source, sequence_number) "
                     "VALUES (?, ?, ?, 'flag_machine', 1)", (rid, ilca6_id, start))
        conn.execute("INSERT INTO race_sailors (race_id, uid, lap_count, placement) VALUES (?, ?, 0, NULL)",
                     (rid, ilca6_uid))
        race_ids.setdefault(days_ago, []).append(rid)
conn.commit()
conn.close()

import app as m
m.DB_PATH = SCRATCH
m.recording_state['active'] = False
m.SAILWAVE_DB_FOLDER = tempdir  # fixture calendar (app-folder fallback not needed here)
client = m.app.test_client()


def export(rid):
    m.app_state['race_id'] = rid
    m.app_state['race_ended'] = True
    resp = client.get('/api/export-race-csv')
    assert resp.status_code == 200, resp.get_data(as_text=True)
    disp = resp.headers.get('Content-Disposition', '')
    fname = re.search(r'filename=([^;]+)', disp).group(1).strip()
    body = resp.get_data(as_text=True)
    race_cell = body.splitlines()[1].split(',')[6]
    return fname, race_cell, body


week_race = race_ids[7][0]
today_races = race_ids[0]
no_event_race = race_ids[2][0]

# Last week's race: first of the series -> R1, no filename suffix
fname, race_cell, _ = export(week_race)
assert fname == f'Test Series club racing {week_ago.strftime("%d-%m-%Y")}.csv', fname
assert race_cell == 'Race 1', race_cell
print(f'series R1 (last week)  -> {fname} | Race column: {race_cell}')

# Today's races: R2, R3, R4 of the series - incremental across the weeks
for expect, rid in zip((2, 3, 4), today_races):
    fname, race_cell, body = export(rid)
    assert fname == f'Test Series club racing R{expect} {now.strftime("%d-%m-%Y")}.csv', fname
    assert race_cell == f'Race {expect}', race_cell
    if expect == 2:
        assert 'Test Series club racing' in body.splitlines()[1], 'Series column not filled'
    print(f'series R{expect} (today)  -> {fname} | Race column: {race_cell}')

# Date with no racing event in the calendar: fallback filename, empty Series,
# Race column falls back to the race-of-day number
fname, race_cell, body = export(no_event_race)
assert fname == f'race_{no_event_race}_results.csv', fname
assert race_cell == 'Race 1', race_cell
row = body.splitlines()[1].split(',')
assert row[5] == '', 'Series column should be empty without a calendar event'
print(f'no calendar event      -> {fname} | Race column: {race_cell} (Series empty, as before)')

# Dell scenario: no calendar in the Sailwave folder -> app-folder fallback
# (the calendar ships with the app now)
m.SAILWAVE_DB_FOLDER = os.path.join(tempdir, 'no-such-folder')
found = m.find_calendar_file()
assert found and found.startswith(ROOT), f'app-folder fallback broken: {found}'
print('no Sailwave folder -> calendar found in the app folder (Dell scenario fixed)')

shutil.rmtree(tempdir)
os.remove(SCRATCH)
print()
print('PASS: series+date filename, incremental series race number (R1..R4 across weeks),'
      ' empty-Series fallback, app-folder calendar fallback')
