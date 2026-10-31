"""
Replay a recorded UI session instantly - no countdown waits.

Records every API call produced by your button clicks (enabled via
http://localhost:5000/api/test/record?action=start) and replays them
against a scratch copy of score.db, so bugs can be reproduced without
sitting through the race countdowns.

Usage:
    python scripts/replay_race.py                # replay tempref/recording.jsonl
    python scripts/replay_race.py --gap 0.2     # small pause between steps
    python scripts/replay_race.py --keep-db     # keep scratch DB for inspection
"""
import argparse
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

RECORDING_PATH = os.path.join('tempref', 'recording.jsonl')
SCRATCH_DB = os.path.join('tempref', 'score_replay.db')
# Countdown pollers recorded before the noise filter existed; harmless to skip
POLLERS = ('/update-status', '/update-live-timer')


def main():
    parser = argparse.ArgumentParser(
        description='Replay a recorded session against a scratch DB (live data untouched)')
    parser.add_argument('--recording', default=RECORDING_PATH,
                        help=f'Path to recording file (default: {RECORDING_PATH})')
    parser.add_argument('--gap', type=float, default=0.0,
                        help='Seconds to pause between steps (default: 0 = instant)')
    parser.add_argument('--keep-db', action='store_true',
                        help='Keep the scratch DB afterwards for inspection')
    args = parser.parse_args()

    if not os.path.exists(args.recording):
        sys.exit(f'Recording not found: {args.recording}\n'
                 f'Enable recording first: http://localhost:5000/api/test/record?action=start')

    with open(args.recording, encoding='utf-8') as f:
        steps = []
        skipped = 0
        for line in f:
            if not line.strip():
                continue
            try:
                steps.append(json.loads(line))
            except json.JSONDecodeError:
                skipped += 1  # tolerate corrupt lines (e.g. interleaved writes)
        if skipped:
            print(f'(skipped {skipped} corrupt recording line(s))')

    if not steps:
        sys.exit(f'Recording is empty: {args.recording}')

    # Fresh scratch DB so the live one is untouched
    shutil.copy('score.db', SCRATCH_DB)

    import app as app_module
    app_module.DB_PATH = SCRATCH_DB
    app_module.recording_state['active'] = False  # never record the replay itself
    client = app_module.app.test_client()

    print(f'Replaying {len(steps)} steps from {args.recording} (instant, no countdown waits)\n')
    steps = [s for s in steps if s['path'] not in POLLERS]
    failures = []
    for i, step in enumerate(steps, 1):
        if args.gap:
            time.sleep(args.gap)
        label = f"{step['method']:6} {step['path']}"
        try:
            resp = client.open(
                step['path'],
                method=step['method'],
                data=(step['body'] or None),
                content_type='application/json',
            )
            status = resp.status_code
        except Exception as e:  # noqa: BLE001 - report the step, keep replaying
            status = f'EXCEPTION ({e.__class__.__name__}: {e})'

        ok = isinstance(status, int) and status < 400
        marker = 'OK ' if ok else 'FAIL'
        print(f'{i:3}. [{marker}] {label} -> {status}')
        if not ok:
            print(f'     body: {step["body"]}')
            failures.append(step)

    print()
    if failures:
        print(f'{len(failures)} of {len(steps)} steps FAILED - these are the repro steps for the bug.')
    else:
        print(f'All {len(steps)} steps replayed successfully (HTTP < 400).')

    # Report final race state so outcomes are visible without opening the DB
    if args.keep_db:
        print(f'\nScratch DB kept for inspection: {SCRATCH_DB}')
    elif os.path.exists(SCRATCH_DB):
        os.remove(SCRATCH_DB)

    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
