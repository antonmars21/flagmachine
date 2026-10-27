"""Verify the export naming fix (bug 29 + multi-race filenames).

The Sailwave CSV export names the file by the series matched from the HYC
race calendar and fills the Series column. Two gaps found after the
24 Oct Dell results:
- the Dell had no calendar in its Sailwave folder, so every export silently
  fell back to race_<id>_results.csv with an empty Series column (the
  calendar now also ships in the app folder as a fallback);
- on multi-race days the series+date filename collided - the three Saturday
  races would overwrite each other. Races after the first now append their
  race-of-day number (R2, R3...).
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

# Fixture calendar: racing TODAY (so the calendar match must succeed) and an
# event far in the past for the fallback case
tempdir = tempfile.mkdtemp(prefix='b29cal_')
cal = os.path.join(tempdir, 'HYC Calendar fixture.xlsx')
today_text = f'{["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"][now.weekday()]} {now.day} ' \
    f'{["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][now.month - 1]} {str(now.year)[2:]}'
build_xlsx(cal, [
    (today_text, 0.75, 'Test Series club racing'),
    ('Sat 3 Jan 26', 0.75, 'Old Series club racing'),
])

conn = sqlite3.connect(SCRATCH)
conn.execute('UPDATE sailors SET racing_today = 0')
conn.execute("UPDATE races SET status = 'ENDED' WHERE status = 'RUNNING'")
ilca6_id = conn.execute(
    "SELECT class_id FROM boat_classes WHERE flag_image = 'ilca6.png'").fetchone()[0]
ilca6_uid = conn.execute(
    'SELECT uid FROM sailors WHERE class_id = ? LIMIT 1', (ilca6_id,)).fetchone()[0]

# Three races today (multi-race day) + one on the old calendar date
race_ids = {}
for days_ago, n in ((0, 3), (2, 1)):
    start = (now - timedelta(days=days_ago)).isoformat()
    for i in range(n):
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
    return fname, resp.get_data(as_text=True)


today = race_ids[0]
old = race_ids[2][0]

# Race 1 of the day: series + date, no suffix
fname, body = export(today[0])
assert fname == f'Test Series club racing {now.strftime("%d-%m-%Y")}.csv', fname
assert 'Test Series club racing' in body.splitlines()[1], 'Series column not filled'
print(f'race 1 of day -> {fname} (Series column filled)')

# Races 2 and 3 of the day: R2 / R3 suffix so they cannot overwrite race 1
fname2, _ = export(today[1])
fname3, _ = export(today[2])
assert fname2 == f'Test Series club racing R2 {now.strftime("%d-%m-%Y")}.csv', fname2
assert fname3 == f'Test Series club racing R3 {now.strftime("%d-%m-%Y")}.csv', fname3
print(f'race 2 of day -> {fname2}')
print(f'race 3 of day -> {fname3}')

# Date with no racing event in the calendar: fallback filename, empty Series
fname, body = export(old)
assert fname == f'race_{old}_results.csv', fname
row = body.splitlines()[1].split(',')
assert row[5] == '', 'Series column should be empty without a calendar event'
print(f'no calendar event -> {fname} (Series empty, as before)')

# Dell scenario: no calendar in the Sailwave folder -> app-folder fallback
# (the calendar ships with the app now)
m.SAILWAVE_DB_FOLDER = os.path.join(tempdir, 'no-such-folder')
found = m.find_calendar_file()
assert found and found.startswith(ROOT), f'app-folder fallback broken: {found}'
print('no Sailwave folder -> calendar found in the app folder (Dell scenario fixed)')

shutil.rmtree(tempdir)
os.remove(SCRATCH)
print()
print('PASS bug 29: calendar fallback + series/date filename + R2/R3 multi-race suffix')
