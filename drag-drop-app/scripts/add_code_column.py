#!/usr/bin/env python3
"""Add a `code` column to race_sailors and repopulate it with the Sailwave
result code (DNS / DNF / blank) per AgentReadme/Race_code_rules.md:

  - No start time (class never started, no open start)  -> DNS
  - 1+ laps recorded, no finish time                     -> DNF
  - Otherwise                                            -> ''

Usage:
  python scripts/add_code_column.py              # live score.db (with backup)
  python scripts/add_code_column.py --db <path>  # specific db file
  python scripts/add_code_column.py --dry-run    # show what would change

The live score.db is always backed up first as score.db.backup-<YYYYMMDD-HHMMSS>
before any ALTER or UPDATE. The migration is idempotent (safe to re-run).
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_DB = os.path.join(APP_DIR, 'score.db')


def compute_code(start_iso, lap_count, finish_iso):
    """Sailwave result code per Race_code_rules.md."""
    if not start_iso:
        return 'DNS'
    if lap_count and lap_count > 0 and not finish_iso:
        return 'DNF'
    return ''


def migrate(db_path, dry_run=False):
    if not os.path.exists(db_path):
        print(f'ERROR: {db_path} not found')
        return 1

    # Back up before any change
    if not dry_run:
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup = f'{db_path}.backup-{stamp}'
        shutil.copy2(db_path, backup)
        print(f'Backed up {db_path} -> {os.path.basename(backup)}')

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Add code column if missing
    c.execute('PRAGMA table_info(race_sailors)')
    cols = [row[1] for row in c.fetchall()]
    if 'code' not in cols:
        if dry_run:
            print('Would: ALTER TABLE race_sailors ADD COLUMN code TEXT')
        else:
            c.execute('ALTER TABLE race_sailors ADD COLUMN code TEXT')
            print('Added column race_sailors.code')
    else:
        print('Column race_sailors.code already exists')

    # 2. Repopulate codes for every race_sailors row
    #    Start time = the sailor's class start (race_class_starts) or the
    #    open start (race_open_starts) for open-category sailors.
    c.execute('''
        SELECT rs.id, rs.race_id, rs.uid, rs.lap_count, rs.finish_time,
               s.class_id,
               rcs.start_time AS class_start,
               ros.start_time AS open_start
        FROM race_sailors rs
        JOIN sailors s ON rs.uid = s.uid
        LEFT JOIN race_class_starts rcs
               ON rcs.race_id = rs.race_id AND rcs.class_id = s.class_id
        LEFT JOIN race_open_starts ros ON ros.race_id = rs.race_id
    ''')
    rows = c.fetchall()
    updated = 0
    for row in rows:
        start = row['class_start'] or row['open_start'] or ''
        code = compute_code(start, row['lap_count'], row['finish_time'])
        if dry_run:
            if code:
                print(f'  Would set code={code!r} for race={row["race_id"]} uid={row["uid"]} '
                      f'(laps={row["lap_count"]}, finish={row["finish_time"]}, start={start[:19] if start else "none"})')
        else:
            c.execute('UPDATE race_sailors SET code = ? WHERE id = ?', (code, row['id']))
        updated += 1

    if not dry_run:
        conn.commit()
        # Coalesce any stragglers (e.g. orphaned race_sailors rows) to ''
        c.execute("UPDATE race_sailors SET code = '' WHERE code IS NULL")
        conn.commit()
        print(f'Repopulated code for {updated} race_sailors row(s)')
    else:
        print(f'Would update {updated} row(s) (dry run)')

    # 3. Summary
    if not dry_run:
        c.execute('SELECT code, COUNT(*) AS n FROM race_sailors GROUP BY code ORDER BY n DESC')
        print('\nCode distribution:')
        for r in c.fetchall():
            label = r['code'] or '(blank)'
            print(f'  {label}: {r["n"]}')

    conn.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description='Add code column to race_sailors and repopulate DNS/DNF')
    ap.add_argument('--db', default=DEFAULT_DB, help='Path to score.db (default: app folder)')
    ap.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    args = ap.parse_args()
    return migrate(args.db, dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
