r"""Shared helper for regression tests: return the results CSV body from an
/api/export-race-csv response. Since the 2026-11-09 fix the endpoint ALWAYS
returns a plain CSV download (never a ZIP - kanban "export to csv failed");
the series template moved to its own /api/export-series-template endpoint.
"""


def get_results_csv(resp):
    return resp.get_data().decode('utf-8')


WEEKDAYS = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def cal_text(d):
    return f'{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {str(d.year)[2:]}'


def build_fixture_xlsx(path, rows):
    """Minimal xlsx writer (zip + XML, no dependency) so tests can build a
    fixture HYC calendar. rows: list of (date_text, time_fraction, event),
    e.g. ('Wed 28 Oct 26', 0.75, 'Test Series club racing') for 18:00."""
    import zipfile
    from xml.sax.saxutils import escape as xml_escape
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
