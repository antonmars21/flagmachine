# CURRENT_STATE - Flag Machine + Finish Sheet

Snapshot at **v0.99** (2026-10-29, field beta). Architecture detail lives in
`Architecture.md`; this file is the quick "what exists right now" map.

## Version

- **v0.99** - field beta. All tracker items closed as of 2026-10-29 were
  human-tested on the machine/on the water. Next: in-field beta with the
  club, then 1.0.
- Live board: `FlagMachine.kanban.md` (repo root, git-ignored - local file).
- Fix history/changelog: `Bug fixes and new features.md`.

## Runtime shape

- Flask app (`app.py`), port 5000, SQLite `score.db`, miniconda Python.
- Launch: desktop shortcut **Flag Machine** -> `START.bat`
  (single-instance guarded: a relaunch reuses the running server and just
  reopens the windows).
- Four Chrome/Edge `--app` windows, one per work page, unique taskbar icons:
  RO control `/`, Finish Sheet 1 `/finishsheet?station=1`,
  Finish Sheet 2 `/finishsheet?station=2`, Display Board `/display`.
  No page-to-page navigation buttons - the taskbar is the navigator.

## Database tables (score.db)

| Table | Purpose |
|---|---|
| `sailors` | Registry. `uid` (SL-\<sail_no\>) is the PRIMARY KEY; `racing_today` = sign-on tick; `class_id` links to boat_classes |
| `boat_classes` | Class rows with `flag_image`; a class with no flag image keeps its sailors in Open Category. Self-heals at startup (`repair_missing_boat_classes`) |
| `races` | One row per race; status RUNNING/ENDED |
| `race_sailors` | Locked roster per race: lap_count, finish_time, placement |
| `race_class_starts` | Per-race per-class start times (flag machine) |
| `race_open_starts` | Per-race Open Category start |
| `lap_records` | Every lap with timestamp |
| `class_station_assignments` | Class-column -> station (kept across races/restarts) |
| `capture_actions` | Step-back/undo log: every lap/finish with station, undone flags |

Startup repairs (run at app start): `recover_running_race()` (bug 27 -
adopt a recent RUNNING race after a crash, close stale ones),
`reconcile_class_flag_images()` + `repair_missing_boat_classes()` (bugs
33/34).

## Endpoints (34 routes)

- Control: `/`, `/display`, `/finishsheet`, `/update-sequence`,
  `/update-settings`, `/update-status`, `/execute-control`,
  `/set-display-mode`, `/update-live-timer`
- Live data: `/api/sailors-for-onwater` (dynamic columns + station filter),
  `/api/sailors-registry`, `/api/race-status`, `/api/display-state`,
  `/api/get-elapsed-time`, `/api/lap-times/<uid>`,
  `/api/race-calendar-event`
- Registry: `/api/toggle-racing`, `/api/add-sailor`,
  `/api/edit-sailor/<uid>`, `/api/delete-sailor/<uid>`, `/api/clear-registry`
- Race flow: `/api/start-race`, `/api/class-start`, `/api/record-lap`,
  `/api/mark-finish`, `/api/end-race`, `/api/reset-race`,
  `/api/reset-finish-sheet`
- Stations/undo: `/api/assign-class-station`, `/api/undo-last`,
  `/api/restore-last`
- Export/import: `/api/export-race-csv` (Sailwave layout; `?format=detailed`
  legacy), `/api/refresh-sailwave`, `/api/refresh-sailwave-status`
- Test tooling: `/api/test/record` (record/replay - see the changelog how-to)

## Regression suite

`scripts/test_*.py` - 20 scripts, all hermetic (scratch DB copies; fixture
sailors from `scripts/seed_test_sailors.py`). Run:
`for %f in (scripts\\test_*.py) do python %f`. Plus `scripts/replay_race.py`
for recorded sessions.

## Data state at v0.99

- 53 sailors (tidied roster, current Sailwave import), 28 races recorded,
  Ilca 4 + Europe classes exist (Ilca 4 = ilca4.png; Europe awaits a flag
  image - see kanban D1).
- Exported results in `Sailing Results 14-17 Oct 2026/`,
  `Sailing Results 24-10-26/`, `Sailing Results 28-10-26/`.
