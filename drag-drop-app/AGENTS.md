# AGENTS.md — Flag Machine + Finish Sheet

Race-day scoring system for club sailing: a Flask app (`app.py`, port 5000) serving the
Flag Machine (start sequences, `/`) and the Finish Sheet (lap/finish scoring,
`/finishsheet`), backed by one SQLite DB (`score.db`). Runs on the club laptop via
`START.bat`.

## Documentation map (read before acting)

Detailed, changing documentation lives in `AgentReadme/` — do not duplicate its content
anywhere else; this file is the stable summary only.

| File | Contents |
|---|---|
| `AgentReadme/Bug fixes and new features.md` | Bug tracker (resolved / in progress / active) + new feature list. Single source of truth for bug status |
| `AgentReadme/Architecture.md` | System architecture, key files, API routes |
| `AgentReadme/CURRENT_STATE.md` | DB tables, endpoint list, current system state |
| `AgentReadme/Requirements.md` | Functional requirements for Flag Machine + Finish Sheet |
| `AgentReadme/DEPLOYMENT.md` | Deployment on the club laptop |

## Process rules (agreed with the RO, 2026-10-15)

1. A bug only moves to resolved after a confirmed HUMAN browser test. Passing regression
   scripts alone is not enough. Regression scripts run against the API and cannot catch
   frontend bugs.
2. Human tests must hard-refresh first (Ctrl+F5) — the JS is cached.
3. After any fix, update the bug tracker entry in
   `AgentReadme/Bug fixes and new features.md` and run the relevant regression script in
   `scripts/`.

## Users and UI philosophy

The race officer and scorers are retired sailors. Screens must be as simple as possible
with the least noise: large flags and time settings, compact lists sized for 10-20 boats,
default row duration of 1 minute in start events. On the finish sheet, sailors are ordered
by lap count ascending — once a sailor completes a lap they move to the bottom of the list
so the scorer works with lap-completers at the top.

## Domain rules (do not violate)

**Flag semantics:**
- `p.png` is the blue peter PREPARATORY SIGNAL flag (letter P). `pclass.png` is the
  P Class boat class (Sailwave class name 'P Class'). They are two different things —
  never merge them. If a bogus 'P' class row ever reappears in `boat_classes`, delete it
  (the Sailwave import mapping was removed so a refresh cannot recreate it).
- Signal flags in a sequence (`p.png`, `Dflag.png`, postpone, ...) are ignored by the
  server for race-start purposes; they carry no boat class.
- More than one class flag can share one start event (e.g. Ilca 6 + Ilca 7 in Start 1).

**Race start semantics:**
- A start event fires its class-start only when its LAST row completes — the full
  typical sequence is class flag (1 min) → class flag + P (1 min) → D flag (1 min).
  Start times and lap times run on the total sequence clock, not the first flag timer.
- One class-start POST per start event carries ALL the grid's flags; the server holds
  `RACE_STATE_LOCK` so concurrent starts can never create duplicate races.

**Open Category:**
- Sailors whose class has no flag in the start sequence are Open Category.
- If the RO drags the `openclass.png` flag into a start event, Open Category activates
  only when that start event fires; without an open flag it activates with the race's
  first start. Open starts are persisted in `race_open_starts` (race_id UNIQUE,
  start_time, sequence_number) and the CSV export falls back to that table for open
  sailors.

**Reset vs end race:**
- `/api/end-race` stops all timers and ends the race (frozen, not zeroed).
- `/api/reset-finish-sheet` REFUSES while a race is running; after the race is ended it
  clears race state so the sheet is ready for the next race, but keeps all laps,
  finishes and race history in the DB and never touches the Flag Machine sequence.

**Data safety:**
- `score.db` is live race data. Never test against it directly; the replay tool works on
  a scratch copy.

## Development

- Python: `C:\ProgramData\miniconda3\python.exe`. App start: `START.bat`; restart:
  `restart_flask.bat`. `score.db` is created/migrated by `app.py` on startup.
- Regression scripts live in `scripts/` (`test_start_event.py`, `test_open_flag.py`,
  `test_late_signon.py`, `test_open_category.py`, `test_export_csv.py`,
  `test_grouping.py`, `test_import_and_flags.py`). Run the ones relevant to your change.
- Bug reproduction: record a session via
  `http://localhost:5000/api/test/record?action=start` (stop with `action=stop`), click
  through the bug flow, then replay instantly with
  `python scripts/replay_race.py` (options: `--gap 0.2`, `--keep-db`). Recording stops
  if the server restarts (debug auto-reload), so record one bug session at a time after
  the pages are loaded.
- On Windows, `nul` is a reserved device name — a stray `nul` file in the repo root
  breaks git commits (see bug 13 in the tracker). Do not create one.
