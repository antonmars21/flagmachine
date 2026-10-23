"""Regression test for the HYC race calendar lookup (feature 6, bug doc item 6).

get_calendar_event_for_date() matches a date to its racing event:
- Wednesday rule: only the Twilight race (from 6pm) is returned, never the
  earlier training/coaching session of the same day.
- Non-racing rows (coaching, committee, learn-to-sail...) are never matched.
- Empty date cells inherit the previous row's date (Excel merged rows).

A fixture xlsx is built from scratch (stdlib zipfile - no openpyxl needed)
mimicking the real calendar layout, and the REAL calendar file is also
checked when it is present on this machine.
"""
import os
import sys
import zipfile
from xml.sax.saxutils import escape as xml_escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import app as app_module
from datetime import date

FIXTURE = os.path.join(ROOT, 'tempref', 'calendar_fixture.xlsx')


def build_xlsx(path, rows):
    """rows: list of (date_text, time_cell, event) - time_cell is a float
    fraction of a day (Excel) or a string."""
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
    sheet = f'<?xml version="1.0"?><worksheet xmlns="{M}"><sheetData>{"".join(body)}</sheetData></worksheet>'
    sst = (f'<?xml version="1.0"?><sst xmlns="{M}" count="{len(strings)}" '
           f'uniqueCount="{len(strings)}">'
           + ''.join(f'<si><t>{xml_escape(s)}</t></si>' for s in strings) + '</sst>')
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('xl/worksheets/sheet1.xml', sheet)
        z.writestr('xl/sharedStrings.xml', sst)


# Wednesday with BOTH a coaching session (16:30) and Twilight (0.75 = 18:00),
# a Saturday series race, a regatta day, and non-racing rows.
build_xlsx(FIXTURE, [
    ('Date', 'Time', 'Event'),                       # header row (no date -> ignored)
    ('Wed 21 Oct 26', '16:30-19:30', 'Green Fleet Coaching & race'),
    ('Wed 21 Oct 26', 0.75, 'Twilight Series club racing'),
    ('Sat 17 Oct 26', 0.5625, 'A Series (1, 2, 3) club racing'),
    ('Sat 12 Dec 26', 0.375, 'HYC XMAS REGATTS & DINNER'),
    ('Tues 8 Dec 26', 0.8125, 'HYC Committee Meeting'),
    ('Sat 24 Oct 26', 0.5625, 'Points Races club sailing'),
])

# --- date parsing ---
assert app_module._parse_calendar_date('Wed 14 Oct 26') == date(2026, 10, 14)
assert app_module._parse_calendar_date('Tues 8 Sept 26') == date(2026, 9, 8)
assert app_module._parse_calendar_date('Mon 25 - Fri 29 Jan 27') is None  # range
assert app_module._parse_calendar_date('TBC ') is None
assert app_module._parse_calendar_date('') is None
print('PASS: date parsing (incl. Sept, ranges and TBC rejected)')

# --- time parsing ---
assert app_module._parse_calendar_time('0.75') == (18, 0)
assert app_module._parse_calendar_time('0.5625') == (13, 30)
assert app_module._parse_calendar_time('16:30-19:30') == (16, 30)
assert app_module._parse_calendar_time('TBC') is None
assert app_module._parse_calendar_time('') is None
print('PASS: time parsing (Excel fraction + text ranges)')

# --- event matching on the fixture ---
wed = app_module.get_calendar_event_for_date(date(2026, 10, 21), FIXTURE)
assert wed == 'Twilight Series club racing', f'Wednesday rule broken: {wed!r}'
print('PASS: Wednesday lookup returns ONLY the Twilight race (from 6pm)')

sat = app_module.get_calendar_event_for_date(date(2026, 10, 17), FIXTURE)
assert sat == 'A Series (1, 2, 3) club racing', f'Saturday lookup broken: {sat!r}'
reg = app_module.get_calendar_event_for_date(date(2026, 12, 12), FIXTURE)
assert reg == 'HYC XMAS REGATTS & DINNER', f'Regatta lookup broken: {reg!r}'
none_day = app_module.get_calendar_event_for_date(date(2026, 12, 8), FIXTURE)
assert none_day is None, f'Committee meeting must not match: {none_day!r}'
no_event = app_module.get_calendar_event_for_date(date(2026, 10, 20), FIXTURE)
assert no_event is None
print('PASS: Saturday series, regatta day, non-racing days')

# --- the real club calendar, when present on this machine ---
real = app_module.find_calendar_file()
if real and os.path.exists(real):
    checks = [
        (date(2026, 10, 21), 'Twilight Series club racing'),   # Wednesday
        (date(2026, 10, 17), 'A Series (1, 2, 3) club racing'),  # Saturday
        (date(2026, 12, 12), 'HYC XMAS REGATTS & DINNER'),
    ]
    for d, expected in checks:
        got = app_module.get_calendar_event_for_date(d)
        print(f'  real calendar {d}: {got!r}')
        assert got == expected, f'{d}: expected {expected!r}, got {got!r}'
    print('PASS: real HYC calendar matches (Wednesday Twilight rule included)')

# --- endpoint shape ---
app_module.DB_PATH = 'tempref/score_test.db'
client = app_module.app.test_client()
resp = client.get('/api/race-calendar-event?date=2026-10-21').get_json()
assert resp['status'] == 'success' and resp['event'], resp
r2 = client.get('/api/race-calendar-event?date=notadate')
assert r2.status_code == 400
print('PASS: /api/race-calendar-event endpoint')

print('ALL CALENDAR CHECKS PASS')
