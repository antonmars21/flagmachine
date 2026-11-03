r"""Shared helper for regression tests: extract the results CSV body from an
/api/export-race-csv response, whether it is a plain CSV or the two-file ZIP
(results CSV + series template) that the export returns when the race date
has a calendar series. Reading the response with get_data(as_text=True)
crashes on the binary ZIP, and the ZIP-vs-CSV switch depends on whether the
machine has a calendar in C:\Users\Public\Documents\Sailwave\... - so tests
must handle both to stay hermetic.
"""


def get_results_csv(resp):
    import io as _io
    import zipfile
    ct = resp.headers.get('Content-Type', '')
    raw = resp.get_data()
    if 'zip' in ct:
        with zipfile.ZipFile(_io.BytesIO(raw)) as zf:
            for name in zf.namelist():
                if name.endswith('.csv') and 'series_template' not in name:
                    return zf.read(name).decode('utf-8')
            return zf.read(zf.namelist()[0]).decode('utf-8')
    return raw.decode('utf-8')
