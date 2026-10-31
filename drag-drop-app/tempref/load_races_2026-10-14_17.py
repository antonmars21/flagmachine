#!/usr/bin/env python3
"""One-off load (2026-10-20): backup score.db, clear all race results,
add Reuben Feist (1878933 Ilca 6), load the 4 corrected races from
14 and 17 October 2026 (as corrected by the RO in
race_results_2026-10-14_and_17.csv + follow-up notes)."""
import sqlite3
import sys

DB = r'C:\Users\anton\flagmachine\drag-drop-app\score.db'
BK = r'C:\Users\anton\flagmachine\drag-drop-app\score.db.pre-clear-20261020'

D = '2026-10-17T'

# (sail_no, [lap timestamps], finish or None)
RACES = [
    {  # 14 Oct - Ilca 6 only
        'label': '2026-10-14 Ilca 6',
        'start': '2026-10-14T18:26:47.824569',
        'end': '2026-10-14T19:05:15.870324',
        'created_utc': '2026-10-14 05:26:47',
        'starts': [('Ilca 6', '2026-10-14T18:26:47.824569', 1)],
        'sailors': [
            ('217619', ['2026-10-14T18:35:36.619536', '2026-10-14T18:43:34.668018', '2026-10-14T18:51:48.560806'], '2026-10-14T18:59:44.085332'),
            ('148917', ['2026-10-14T18:36:16.737241', '2026-10-14T18:44:16.264258', '2026-10-14T18:53:21.136408'], '2026-10-14T19:01:54.864511'),
            ('206424', ['2026-10-14T18:36:23.072432', '2026-10-14T18:44:04.014025', '2026-10-14T18:53:15.803128'], '2026-10-14T19:01:57.067930'),
            ('211516', ['2026-10-14T18:36:25.617138', '2026-10-14T18:44:44.017718', '2026-10-14T18:54:16.910409'], '2026-10-14T19:01:59.745818'),
            ('1878933', ['2026-10-14T18:36:36.207439', '2026-10-14T18:45:54.852436', '2026-10-14T18:55:54.813329'], '2026-10-14T19:04:30.601764'),
        ],
    },
    {  # 17 Oct race 1
        'label': '2026-10-17 R1',
        'start': D + '13:45:14.725094',
        'end': D + '14:40:27.117601',
        'created_utc': '2026-10-17 00:45:14',
        'starts': [
            ('Ilca 6', D + '13:45:14.725094', 1),
            ('Zephyr', D + '13:48:14.698261', 2),
            ('Starling', D + '14:00:42.315380', 3),
            ('P Class', D + '14:01:42.293950', 4),
        ],
        'sailors': [
            ('211516', [D + '14:08:54.266955'], D + '14:26:25.928181'),
            ('148917', [D + '14:09:46.658893'], D + '14:26:43.867220'),
            ('63', [D + '14:10:38.747532'], D + '14:26:51.864449'),
            ('214400', [D + '14:08:43.836271'], D + '14:27:17.646328'),
            ('187893', [D + '14:11:09.330522'], D + '14:28:04.417118'),
            ('191327', [D + '14:13:01.153995'], D + '14:29:09.519330'),
            ('156', [D + '14:20:50.462963'], D + '14:32:21.414083'),
            ('862', [D + '14:20:49.221147'], D + '14:38:05.433622'),
            ('2021', [D + '14:19:17.337278'], D + '14:38:12.162820'),
            ('2057', [D + '14:19:18.315190'], D + '14:39:55.773721'),
        ],
    },
    {  # 17 Oct race 2
        'label': '2026-10-17 R2',
        'start': D + '14:56:59.903923',
        'end': D + '15:41:09.957476',
        'created_utc': '2026-10-17 01:56:59',
        'starts': [
            ('Ilca 6', D + '14:56:59.903923', 1),
            ('Zephyr', D + '14:59:59.898382', 2),
            ('Starling', D + '15:02:59.901905', 3),
            ('P Class', D + '15:02:59.903266', 3),
        ],
        'sailors': [
            ('156', [D + '15:21:19.173430'], D + '15:34:38.146484'),
            ('2021', [D + '15:19:23.242194'], D + '15:36:36.405391'),
            ('2057', [D + '15:19:26.598839'], D + '15:37:10.449330'),
            ('214400', [D + '15:12:14.801493', D + '15:24:24.134888'], D + '15:37:31.696674'),
            ('148917', [D + '15:12:05.557676', D + '15:24:03.264922'], D + '15:37:35.540153'),
            ('211516', [D + '15:12:01.445039', D + '15:24:46.431058'], D + '15:37:39.472126'),
            ('862', [D + '15:21:24.805639'], D + '15:37:45.022611'),
            ('191327', [D + '15:12:16.163654', D + '15:25:24.180090'], D + '15:38:08.277973'),
            ('187893', [D + '15:12:13.554625', D + '15:25:18.175113'], D + '15:38:40.429782'),
            ('63', [D + '15:13:48.209449', D + '15:27:01.089878'], D + '15:41:02.837507'),
        ],
    },
    {  # 17 Oct race 3
        'label': '2026-10-17 R3',
        'start': D + '15:50:14.095799',
        'end': D + '16:32:15.723357',
        'created_utc': '2026-10-17 02:50:14',
        'starts': [
            ('Ilca 6', D + '15:50:14.095799', 1),
            ('Starling', D + '15:53:14.089628', 2),
            ('P Class', D + '15:50:14.095799', 1),
        ],
        'sailors': [
            ('156', [D + '16:11:47.795363'], D + '16:24:50.243224'),
            ('2021', [D + '16:09:18.176051'], D + '16:25:13.765980'),
            ('862', [D + '16:09:01.685485'], D + '16:26:15.469109'),
            ('2057', [D + '16:09:15.895713'], D + '16:27:00.303260'),
            ('214400', [D + '16:02:48.233386', D + '16:15:59.664310'], D + '16:29:16.457427'),
            ('148917', [D + '16:03:45.125138', D + '16:16:02.791739'], D + '16:29:59.976389'),
            ('211516', [D + '16:03:12.817267', D + '16:16:13.207631'], D + '16:30:21.402385'),
            ('187893', [D + '16:04:06.811416', D + '16:16:59.242492'], D + '16:30:48.121270'),
            ('191327', [D + '16:04:29.488479', D + '16:18:10.391531'], D + '16:31:57.018327'),
            ('63', [], None),  # Jack Ninnes DNS - recorded with no times
        ],
    },
]


def main():
    # 1. Backup (sqlite backup API - consistent snapshot even with server running)
    src = sqlite3.connect(DB)
    dst = sqlite3.connect(BK)
    src.backup(dst)
    dst.close()
    print(f'backup written: {BK}')

    cur = src.cursor()
    cur.execute('BEGIN')
    try:
        # 2. Clear all race results (sailors, boat_classes, station assignments kept)
        for t in ('race_sailors', 'lap_records', 'race_class_starts',
                  'race_open_starts', 'capture_actions', 'races'):
            n = cur.execute(f'DELETE FROM {t}').rowcount
            print(f'cleared {t}: {n} rows')

        # 3. Add Reuben Feist (1878933, Ilca 6) if not present
        cur.execute("SELECT uid FROM sailors WHERE sail_no = '1878933'")
        row = cur.fetchone()
        if row:
            print(f'Reuben Feist 1878933 already present: {row[0]}')
        else:
            cur.execute(
                "INSERT INTO sailors (uid, sailor_name, short_name, sail_no, boat_class, "
                "handicap, seed, class_id, racing_today, status) "
                "VALUES ('SL-1878933', 'Reuben Feist', 'Reuben', '1878933', 'Ilca 6', 1.0, 0, "
                "(SELECT class_id FROM boat_classes WHERE class_name = 'Ilca 6'), 0, 'racing')")
            print('added sailor: Reuben Feist, 1878933, Ilca 6')

        # sanity: the other corrections should already hold in this registry
        for name, sno in (('John Barnard', '214400'), ('Melissa Dentice', '2021'),
                          ('Scott Dawson', '156')):
            cur.execute("SELECT sail_no, class_id FROM sailors WHERE sailor_name = ?", (name,))
            r = cur.fetchone()
            print(f'registry check {name}: sail_no={r[0]} class_id={r[1]}')

        uid_by_sail = dict(cur.execute('SELECT sail_no, uid FROM sailors'))
        class_id = dict(cur.execute('SELECT class_name, class_id FROM boat_classes'))

        # 4. Load the four races
        for race in RACES:
            cur.execute(
                'INSERT INTO races (start_time, status, class_groups, created_at, end_time) '
                'VALUES (?, ?, NULL, ?, ?)',
                (race['start'], 'ENDED', race['created_utc'], race['end']))
            race_id = cur.lastrowid
            for cls_name, st, seq in race['starts']:
                cur.execute(
                    'INSERT INTO race_class_starts (race_id, class_id, start_time, source, sequence_number) '
                    "VALUES (?, ?, ?, 'flag_machine', ?)",
                    (race_id, class_id[cls_name], st, seq))
            for sail_no, laps, finish in race['sailors']:
                uid = uid_by_sail[sail_no]
                cur.execute(
                    'INSERT INTO race_sailors (race_id, uid, lap_count, finish_time, placement) '
                    'VALUES (?, ?, ?, ?, NULL)',
                    (race_id, uid, len(laps), finish))
                for i, t in enumerate(laps, start=1):
                    cur.execute(
                        'INSERT INTO lap_records (race_id, uid, lap_number, timestamp) '
                        'VALUES (?, ?, ?, ?)', (race_id, uid, i, t))
                    lap_id = cur.lastrowid
                    cur.execute(
                        "INSERT INTO capture_actions (race_id, uid, action, station, timestamp, "
                        "lap_number, ref_id, undone) VALUES (?, ?, 'lap', NULL, ?, ?, ?, 0)",
                        (race_id, uid, t, i, lap_id))
                if finish:
                    cur.execute(
                        "INSERT INTO capture_actions (race_id, uid, action, station, timestamp, "
                        "lap_number, ref_id, undone) VALUES (?, ?, 'finish', NULL, ?, NULL, NULL, 0)",
                        (race_id, uid, finish))
            n_sail = len(race['sailors'])
            n_laps = sum(len(s[1]) for s in race['sailors'])
            print(f"loaded {race['label']}: race_id={race_id}, {n_sail} sailors, {n_laps} laps")

        src.commit()
        print('committed')
    except Exception:
        src.rollback()
        print('ERROR - rolled back, no changes made', file=sys.stderr)
        raise
    finally:
        src.close()


if __name__ == '__main__':
    main()
