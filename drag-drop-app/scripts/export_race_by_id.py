"""Re-export any recorded race as the Sailwave-import CSV with the correct
series name and filename (feature 5: results check from score.db, to go back
and re-Export). Works on a scratch COPY of the database - the live score.db
is never opened for writing and never modified.

Usage:
    python scripts/export_race_by_id.py --race 65
    python scripts/export_race_by_id.py --race 61 --db "Sailing Results 24-10-26/Sailing Results Dell/score_dell241026.db" --out "Sailing Results 24-10-26"

The filename and Series column come from the app's own export logic: series
matched from the HYC race calendar by the race date, plus the race-of-day
number (R2, R3...) so the day's races never overwrite each other.
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def main():
    parser = argparse.ArgumentParser(description='Re-export a recorded race as the Sailwave CSV')
    parser.add_argument('--race', type=int, required=True, help='race_id to export')
    parser.add_argument('--db', default='score.db', help='database to read (default: score.db)')
    parser.add_argument('--out', default='.', help='output folder (default: current folder)')
    args = parser.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f'Database not found: {args.db}')

    # Scratch copy - never touch the live/original database
    scratch = os.path.join('tempref', 'score_reexport.db')
    shutil.copy(args.db, scratch)

    import app as m
    m.DB_PATH = scratch
    m.recording_state['active'] = False
    client = m.app.test_client()

    # Point the in-memory race state at the historic race, then run the real
    # export endpoint (same code path as the Export CSV button)
    m.app_state['race_id'] = args.race
    m.app_state['race_ended'] = True
    resp = client.get('/api/export-race-csv')
    if resp.status_code != 200:
        sys.exit(f'Export failed ({resp.status_code}): {resp.get_data(as_text=True)[:200]}')

    filename = None
    for part in resp.headers.get('Content-Disposition', '').split(';'):
        part = part.strip()
        if part.lower().startswith('filename='):
            filename = part.split('=', 1)[1].strip()
    if not filename:
        sys.exit('Export returned no filename')
    filename = os.path.basename(filename)

    os.makedirs(args.out, exist_ok=True)
    dest = os.path.join(args.out, filename)
    with open(dest, 'wb') as f:
        f.write(resp.get_data())
    os.remove(scratch)
    print(f'exported race {args.race} -> {dest}')


if __name__ == '__main__':
    main()
