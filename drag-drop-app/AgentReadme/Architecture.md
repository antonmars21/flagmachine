# Flag Machine + Finish Sheet — Session 5 Architecture

**Status**: Session 5 complete - Dynamic Start Sequences implemented. See `SESSION5_COMPLETED.md` for full details.

---

## OVERVIEW

Single Flask app (`app.py`, port 5000, debug=True) serving both Flag Machine (`/`) and Finish Sheet (`/finishsheet`), backed by one SQLite DB (`score.db`).

### New in Session 5

- **`boat_classes` table**: `class_id, class_name, flag_image, color_hex`. Single source of truth mapping class name to flag image (case-insensitive lookups) and UI color. `sailors.class_id` FK added (boat_class TEXT kept for compat).
- **`race_class_starts` table**: `race_id, class_id, start_time, source`. Records when each class's countdown hit 00:00 (or manual backup start).
- **Event-driven race start**: Flag Machine POSTs `/api/class-start {flag_image}` when a countdown row hits 00:00. Auto-creates a race on first trigger; locks in the roster (from `sailors.racing_today`) ONLY for that class — other not-yet-started classes stay live/editable via the registry sidebar.
- **Sequential grid timing**: Start 1 and Start 2 share ONE cumulative clock — Start 2 begins only after Start 1 fully completes. Secondary flag (same slot) fires its own class-start too.
- **Server-truth timers**: `/api/get-elapsed-time` (earliest class start → now, frozen at `race_end_timestamp` once ended) is polled by BOTH Flag Machine's RACE DURATION and Finish Sheet's Elapsed Time — no more client-only drift/reset-on-navigation.
- **End Race vs Reset**: `/api/end-race` freezes the timer + records `races.end_time`, does NOT zero it. Only `/api/reset-race` (Flag Machine's Reset button) zeroes state back to READY.
- **Dynamic Finish Sheet columns**: `/api/sailors-for-onwater` builds one column per boat class currently in the Flag Machine's Start Sequence (ordered by sailor count desc), plus a trailing "Open Category" column for everyone else. Only `racing_today=1` sailors are included.
- **Sailor registry sidebar** (reinstated from old score.py/score.html): slide-out panel on `/finishsheet` — search, racing-today checkbox (sign-on for today), add/edit/delete. Endpoints: `/api/sailors-registry`, `/api/toggle-racing`, `/api/add-sailor`, `/api/edit-sailor/<uid>`, `/api/delete-sailor/<uid>`.
- **Sailor card behavior**: lap/finish controls disabled until that sailor's class has started (enforced server-side in `/api/record-lap` and `/api/mark-finish`, not just UI); amber glow (`class-started`) matches Flag Machine's active countdown color. Auto-sort by lap_count desc/seed asc; finishing always drops a sailor to the bottom (by finish time), overriding manual drag placement.
- **CSV export**: `/api/export-race-csv` downloads Class, Sailor, SailNo, StartTime, Laps, FinishTime, RaceEndTime for the current/last race.
- **Dynamic start sequences**: `/api/class-start` now accepts `sequence_number` parameter, stored in `race_class_starts.sequence_number` for grouping results by start sequence.
- **Enhanced CSV export**: Now includes Sequence and Lap Times columns with full timestamp data.
- **Lap times API**: `/api/lap-times/<uid>` endpoint to retrieve individual lap timestamps.
- **Sequence-aware finish sheet**: `/api/sailors-for-onwater` groups sailors by (class_id + sequence_number) to create separate columns for each start sequence.

### Deprecated
`score.py` (port 5001) front-end fully decommissioned; its registry UI/UX was ported into the Finish Sheet sidebar (see above). `score.db` schema preserved.

---

## KEY FILES

```
app.py                     Flask app - all routes, DB schema init, app_state (in-memory)
score.db                   SQLite DB (sailors, boat_classes, races, race_sailors,
                           race_class_starts, lap_records)
migrate_boat_classes.py    One-off migration script (safe to delete once stable)

templates/
  index.html               Flag Machine control panel (dynamic N grids via "+" button)
  display.html             Outdoor display board
  finishsheet.html         Finish Sheet UI + registry sidebar markup (dynamic columns)

static/js/
  app.js                   Flag Machine engine (sequential countdown, class-start POST, dynamic grid management)
  finishsheet.js           Finish Sheet engine (dynamic columns, registry sidebar, sequence display,
                           sort/finish-drop, polling)
static/css/
  style.css                Flag Machine + shared styles
  registry.css              Registry sidebar styles
```

## KEY API ROUTES (Session 5 additions)

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/class-start` | Flag Machine notifies a class's countdown hit 00:00 |
| GET | `/api/race-status` | Poll: race_id, class_start_times, race_ended |
| POST | `/api/end-race` | Freeze timer, record end_time (idempotent) |
| POST | `/api/reset-race` | Zero all race/timer state back to READY |
| GET | `/api/export-race-csv` | Download race results CSV |
| GET | `/api/sailors-for-onwater` | Dynamic columns for Finish Sheet (sequence-aware) |
| GET | `/api/sailors-registry` | Full fleet list w/ racing_today |
| GET | `/api/lap-times/<uid>` | Get lap timestamps for a sailor |
| POST | `/api/class-start` | Class start with sequence_number |
| POST | `/api/toggle-racing` | Sign a sailor on/off for today |
| POST/PUT/DELETE | `/api/add-sailor`, `/api/edit-sailor/<uid>`, `/api/delete-sailor/<uid>` | Registry management |

---

## NEXT STEPS
See `AgentReadme/SESSION6_PLAN.md` for full handoff notes, known minor bugs, and Session 6 priorities.


---

## PART 1: FLAG MACHINE (Sessions 1–3)

### Overview
Web-based race officer control panel for managing sailing race flag sequences and countdowns. Unchanged from previous sessions.

### Frontend
- `templates/index.html` — Control panel (drag-drop cards, countdown timers)
- `templates/display.html` — Outdoor display board (live flag + elapsed time)
- `static/js/app.js` — Main engine (drag-drop, countdown loop, state management)
- `static/css/style.css` — 4-column layout, dark theme, neon amber countdowns

### Backend
- `app.py` — Flask app, port 5000
- Routes: `/`, `/display`, `/update-sequence`, `/update-settings`, `/update-status`, `/execute-control`, `/api/display-state`, `/update-live-timer`
- State: in-memory Python dict (`app_state`)

### Countdown Flow
1. Race officer sets `master_start_time` and drag-drops flag cards
2. START clicked → status = RUNNING, stores `race_start_timestamp`
3. `updateCountdown()` (client-side, 100ms interval) updates card timers and states
4. Display board (`/display`) polls `/api/display-state` (500ms) → shows active flag + elapsed time

---

## PART 2: FINISH SHEET v1.1 (Sessions 3–4)

### Overview
Dual-operator touch UI for recording sailor lap counts and finish times on water. Replaces the Sailor Scorer front-end (score.py). Runs integrated with Flag Machine on the same Flask app.

```
URL:      http://localhost:5000/finishsheet
Backend:  app.py (Flask, port 5000)
Database: score.db (SQLite, merged schema)
Templates:
  finishsheet.html  — UI with banner, 4-column sailor display, controls
Styles:
  static/css/style.css (shared with Flag Machine)
Scripts:
  static/js/finishsheet.js — sailor loading, lap recording, finish marking, D&D reordering
```

### Component Map

```
app.py                           ← Flask app + all routes + DB init
  ├── /finishsheet               ← Render UI
  ├── /api/sailors-for-onwater   ← Get sailors grouped by class (4 columns)
  ├── /api/start-race            ← Create race, add sailors
  ├── /api/record-lap            ← Increment lap count + timestamp
  ├── /api/mark-finish           ← Set finish time
  ├── /api/get-elapsed-time      ← Elapsed since race start
  └── /api/reorder-sailors       ← Manual placement reordering

score.db                         ← SQLite database (merged schema)
  ├── sailors                    ← Fleet registry (27 sailors in testing)
  ├── races                      ← Race sessions
  ├── race_sailors               ← Join table: sailors in each race
  ├── lap_records                ← Audit trail: each lap + timestamp
  └── (Session 2 legacy cols)    ← racing_today, status, finish_order, finish_time

templates/finishsheet.html       ← HTML structure
static/js/finishsheet.js         ← Client logic
```

### Database Schema (Session 3 Merge)

**Session 2 sailors table (preserved) + Session 3 race tracking:**

```sql
-- Session 2 legacy (preserved for registry + backward compat)
CREATE TABLE sailors (
    uid              TEXT PRIMARY KEY,
    sailor_name      TEXT,
    short_name       TEXT,
    sail_no          TEXT UNIQUE,
    boat_class       TEXT,
    handicap         REAL,
    seed             INTEGER,
    --- Legacy cols (Session 2, not used in Finish Sheet) ---
    racing_today     INTEGER DEFAULT 0,
    status           TEXT DEFAULT 'racing',
    finish_order     INTEGER DEFAULT NULL,
    finish_time      TEXT DEFAULT NULL
);

-- Session 3 new: track which sailors in which race
CREATE TABLE races (
    race_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time       TEXT,
    status           TEXT DEFAULT 'READY',
    class_groups     TEXT,  -- JSON list of class names
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session 3: join table for race participation
CREATE TABLE race_sailors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id          INTEGER,
    uid              TEXT,
    lap_count        INTEGER DEFAULT 0,
    finish_time      TEXT,
    placement        INTEGER,
    FOREIGN KEY(race_id) REFERENCES races(race_id),
    FOREIGN KEY(uid) REFERENCES sailors(uid)
);

-- Session 3: audit trail for lap recording
CREATE TABLE lap_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id          INTEGER,
    uid              TEXT,
    lap_number       INTEGER,
    timestamp        TEXT,  -- ISO format
    FOREIGN KEY(race_id) REFERENCES races(race_id),
    FOREIGN KEY(uid) REFERENCES sailors(uid)
);
```

**Status**: Session 4 testing confirms all 27 sailors load correctly from `sailors` table.

### Data Flow

#### 1. Page Load (GET `/finishsheet`)
```
User opens http://localhost:5000/finishsheet
  ↓
finishsheet.html renders with banner, 4-column grid (empty), Start/End buttons
  ↓
finishsheet.js initializes:
  - Fetch /api/sailors-for-onwater
  - Query: SELECT * FROM sailors ORDER BY boat_class, seed
  - Group by boat_class, sort descending by count
  - Layout: Col 1-3 = top 3 classes, Col 4 = "Open" (remainder)
  - Render sailor cards: sail_no, short_name, boat_class, lap counter, finish checkbox
```

**Result**: 27 sailors displayed as:
- Column 1 (Ilca 6): 14 sailors
- Column 2 (Starling): 4 sailors
- Column 3 (Optimist): 3 sailors
- Column 4 (Open): 6 sailors (Ilca 7, P, Zephyr)

#### 2. Start Race (Click "▶ Start Race" button)
```
finishsheet.js: startRace()
  ↓
POST /api/start-race { selected_sailors: [uid, uid, ...] }
  ↓
app.py: create races record, insert race_sailors for each uid with lap_count=0
  ↓
app_state['race_id'] set, app_state['race_start_timestamp'] set
  ↓
Button states: Start disabled, End enabled, elapsed-time timer starts polling
```

#### 3. Record Lap (Click "+ Lap" on sailor card)
```
User clicks + Lap button on sailor card
  ↓
finishsheet.js: recordLap(uid, card)
  ↓
POST /api/record-lap { uid }
  ↓
app.py:
  - UPDATE race_sailors SET lap_count = lap_count + 1
  - INSERT INTO lap_records (race_id, uid, lap_number, timestamp)
  ↓
Return { status: success, lap_count: N }
  ↓
finishsheet.js: Update card UI with new lap count
```

#### 4. Mark Finish (Check "finished" checkbox on sailor card)
```
User clicks finish checkbox
  ↓
finishsheet.js: markFinish(uid, is_checked, card)
  ↓
POST /api/mark-finish { uid }
  ↓
app.py:
  - UPDATE race_sailors SET finish_time = NOW()
  ↓
finishsheet.js:
  - Add .finished class (green tint)
  - Disable checkbox
  - Card moves to top visually (optional future: sort)
```

#### 5. End Race (Click "⏹ End Race" button)
```
finishsheet.js: endRace()
  ↓
app_state['race_active'] = false
  ↓
All lap + finish buttons disabled
  ↓
Page ready for manual placement reordering via drag-drop
```

### REST API Routes

| Method | Route | Body | Response |
|--------|-------|------|----------|
| GET | `/finishsheet` | — | HTML page |
| GET | `/api/sailors-for-onwater` | — | `{ status, columns: {1: [...], 2: [...], 3: [...], 4: [...]}, class_groups: [...] }` |
| POST | `/api/start-race` | `{ selected_sailors: [uid, ...] }` | `{ status, race_id }` |
| POST | `/api/record-lap` | `{ uid }` | `{ status, lap_count }` |
| POST | `/api/mark-finish` | `{ uid }` | `{ status, finish_time }` |
| GET | `/api/get-elapsed-time` | — | `{ status, elapsed_seconds, formatted: "MM:SS" }` |
| POST | `/api/reorder-sailors` | `{ placements: [{uid, placement}, ...] }` | `{ status }` |

### Sailor Card UI

```
┌─────────────────────────────┐
│  123        Ilca 6          │ ← sail_no, boat_class
│  Werner                     │ ← short_name
│  [+ Lap] [0]  [☑ Finished] │ ← lap counter, finish checkbox
└─────────────────────────────┘
```

**Styling:**
- Default: dark blue background, white text, amber sail number
- Finished: green tint, sail number amber, checkbox checked + disabled
- Hover: slight lift + border highlight

### Frontend Architecture (finishsheet.js)

**Initialization:**
```javascript
document.addEventListener('DOMContentLoaded', initFinishSheet)
  ↓
  1. loadAndRenderSailors()
  2. Set up event listeners (Start, End buttons)
  3. Start elapsed time polling (1s interval)
```

**Sailor loading & rendering:**
```javascript
loadAndRenderSailors()
  → fetch /api/sailors-for-onwater
  → state.sailors_by_column = data.columns
  → renderColumns(columns, class_groups)
    → for col 1-4: create column-div, header, sailors-list
    → for each sailor: createSailorCard()
```

**Sailor card interactions:**
- **Lap button**: `recordLap(uid, card)` → POST → update UI
- **Finish checkbox**: `markFinish(uid, checked, card)` → POST → add .finished class
- **Drag & drop** (future): swap positions within/across columns

**Elapsed time display:**
```javascript
updateElapsedTime()  // Called every 1s
  → if race_active: fetch /api/get-elapsed-time
  → Update #elapsed-time textContent with formatted time
```

### Key Design Decisions (Session 3)

| Decision | Rationale |
|----------|-----------|
| Unified app.py (no separate score.py) | Simplifies deployment; Flag Machine + Finish Sheet share same process |
| 4-column layout (not fluid) | Touch-friendly on tablet; fixed columns for two operators side-by-side |
| Sailors loaded from `sailors` table (not race pre-selection) | v1.1 displays all 27; race participation determined at start |
| Lap count + timestamp separate records | Audit trail per lap for future analysis (PY adjustments, penalties) |
| Finish checkbox (not drag to zone) | Faster on touch; two operators tap their sailor when they cross finish line |
| Manual reordering via drag-drop (post-finish) | Fixes photo finishes, handling disputes in real-time |

---

## DEPRECATION NOTICE: score.py (Session 2)

**Status**: ACTIVE (front-end decommissioned, back-end functions absorbed into Finish Sheet)

**What's deprecated:**
- `score.py` front-end (port 5001, `/score` route)
- `templates/score.html` UI (kanban board, Sailor Scorer v1.0)
- `static/js/score.js` drag-drop logic (lane reordering)

**What's preserved:**
- `score.db` database + `sailors` table
- Sailor registry (27 sailors with uid, sail_no, boat_class, seed)
- Legacy columns (`racing_today`, `status`, `finish_order`, `finish_time`) — NOT used in Finish Sheet, maintained for backward compatibility

**Migration plan:**
1. Session 4: Test Finish Sheet v1.1 fully (lap recording, finish marking, elapsed time)
2. Post-Session 4: Remove `score.py`, `seed_sailors.py` from active codebase
3. Archive to `SessionDocs/Session2_Scorer_Archive/`

---

## CURRENT SYSTEM STATE (Session 4)

### Running Components

| Component | Location | Port | Status |
|-----------|----------|------|--------|
| Flag Machine + Finish Sheet | app.py | 5000 | ACTIVE (debug=True) |
| score.py (old Scorer) | score.py | 5001 | INACTIVE (for decommissioning) |
| Database | score.db | — | ACTIVE (merged schema) |

### Verified (Session 4 Testing)

- [x] `/finishsheet` page loads with banner + Start/End buttons
- [x] 27 sailors load in 4 columns (14 Ilca 6, 4 Starling, 3 Optimist, 6 Open)
- [x] Sailor cards display sail_no, short_name, boat_class
- [x] `/api/start-race` creates race, inserts race_sailors
- [x] `/api/record-lap` increments lap count + timestamps
- [x] `/api/mark-finish` sets finish_time
- [x] `/api/get-elapsed-time` returns elapsed MM:SS since race start

### Known Issues / TODO

- [ ] JavaScript column rendering: verify string keys ('1', '2', '3', '4') handled correctly
- [ ] Elapsed time: verify updates every 1s without lag
- [ ] Finish checkbox: test visual feedback (green tint, disabled state)
- [ ] Drag-drop reordering: test within columns and across columns
- [ ] End race flow: test disabling all buttons, preserving data
- [ ] Race data export: CSV export (future feature)

---

## File Structure (Session 4)

```
app.py                          ← Main Flask app (Flag Machine + Finish Sheet)
score.db                        ← SQLite database (merged schema)
score.py                        ← DEPRECATED (old Sailor Scorer, port 5001)
seed_sailors.py                 ← Registry seed script

templates/
  index.html                    ← Flag Machine control panel
  display.html                  ← Flag Machine outdoor display
  finishsheet.html              ← Finish Sheet v1.1 UI

static/
  js/
    app.js                      ← Flag Machine engine
    finishsheet.js              ← Finish Sheet engine
  css/
    style.css                   ← Shared styling

AgentReadme/
  Architecture.md               ← This file (Session 4)
  Requirements.md               ← v1.1 spec (Session 3, updated)
  SESSION3_IMPLEMENTATION.md    ← Session 3 build notes
  [...other session docs]
```

---

## Next Steps (Post-Session 4)

1. Complete manual testing (lap recording, finish marking, drag-drop)
2. Test race data persistence (query race_sailors + lap_records)
3. Implement CSV export for race results
4. Decommission score.py (remove front-end, archive code)
5. Deploy to production (Raspberry Pi or cloud)

---

## SESSION 6 (2026-10-16) — Multi-Station Finish Sheet + Flag Split + Sailwave HTM Import

### New in Session 6 (all human-test passed 2026-10-16)

- **Flag folder split (F0)**: flags live in `static/flags/classflags/` + `static/flags/signalflags/`.
  The RO picker shows CLASS FLAGS + SIGNAL FLAGS groups. `flag_url(filename)` resolves every
  flag image to its subfolder (RO picker, start event rows, secondary/tertiary slots, display
  board); bare filenames stay in `boat_classes` and the sequence, so class matching, CSV and
  recorded sessions are unaffected. The startup repair scans classflags/ only.
- **Stations**: `/finishsheet?station=1|2`; the route passes the station to the template for
  the tab title; `getStationFromUrl()` in finishsheet.js (URL authoritative, sessionStorage
  per tab, default 1); station badge in the banner.
- **Class-to-station split**: table `class_station_assignments` (class_key `c<class_id>` or
  `open`, station 1|2, kept for the whole day). `get_station_assignments()`: stored toggles
  win, default by sheet position (first 3 columns -> station 1). Column-header toggle button
  POSTs `/api/assign-class-station`.
- **Undo (per screen)**: table `capture_actions` — every lap/finish logged with its station
  and ORIGINAL timestamp (laps reference `lap_records.id` via ref_id; undone rows kept for
  Restore). `/api/record-lap` and `/api/mark-finish` accept a `station` field; a 2s
  double-capture lap guard rejects the same sailor lapped twice within 2 seconds.
  `POST /api/undo-last {station}` reverses that station's latest non-undone capture;
  `POST /api/restore-last {station}` re-applies the most recently undone action with its
  ORIGINAL timestamp. Superseded finishes refuse with 409. Toast with Restore on the acting
  station; nothing is hard-deleted.
- **sheet_version re-render**: `/api/race-status` reports `app_state['sheet_version']`;
  column toggle, undo and restore bump it; every station's 500ms poller re-renders when it
  changes (~0.5s convergence).
- **Sailwave import**: source is `boat_master.htm` (the Sailwave HTML competitor list;
  Boats_master.htm in the Sailwave folder preferred) with `Boats_Master.xml` fallback.
  `parse_sailwave_htm()` in scripts/import_sailwave.py maps the table (Fleet, Class, Boat,
  SailNo, HelmName, Handicap) onto the same boat shape as the XML parser. The
  'Import Sailwave sailors' button is identical on all pages.
- **UI**: unified .btn spec across pages; RO bottom bar has Display Board + Finish Sheet 1/2
  links (all new tab); two-line sailor cards (name + complete sail number, class under);
  light scrollbars.

### New/changed API routes (Session 6)

| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/assign-class-station` | Move a class column to the other station |
| POST | `/api/undo-last` | Reverse this station's most recent capture |
| POST | `/api/restore-last` | Restore the most recently undone capture (original time) |
| GET | `/api/sailors-for-onwater?station=N` | Station-filtered columns + assignments map |
| GET | `/finishsheet?station=N` | Per-station page (tab title "Finish sheet N") |

`/api/race-status` now also reports `sheet_version`. `/api/record-lap` and `/api/mark-finish`
accept (and log) a `station` field.

### Regression scripts added (Session 6)

- `scripts/test_stations.py` — class split: defaults, filtering, toggle, upsert,
  new-class default, persistence across a race cycle, validation.
- `scripts/test_stepback.py` — undo/restore with original timestamps, station isolation,
  2s guard, superseded-finish 409s, validation.
- `scripts/test_import_htm.py` — boat_master.htm parse + scratch-DB import + source preference.

Full 10-script regression suite passes.

### Known gaps (planned feature 4 remainder)

- Captures do not yet propagate between stations sub-second during a race (SSE planned —
  add the SSE endpoint to RECORD_NOISE when built).
- Manual drag order is still tab-local (`race_sailors.placement` still never written).
- Optional: double-capture dimming ("Station N capturing" while a card is touched).

---

## SESSION 7 (2026-10-20 → 2026-10-27) — Sailwave Series Export + Race-Day Robustness

All changes regression-tested (17-script suite in `scripts/`); bugs 28 + 30
human-test PASSED, 27 + 29 + 31 coded and awaiting/under human test (see
`Bug fixes and new features.md` bugs 27-31).

### 1. HYC race calendar integration (bugs 29 + series naming)

- `find_calendar_file()` locates `HYC Calendar*.xlsx` in the Sailwave database
  folder (`C:\Users\Public\Documents\Sailwave\Flagmachine_database`) FIRST, then
  **falls back to the app folder** — the calendar now SHIPS WITH THE APP
  (`drag-drop-app/HYC Calendar 2026-2027.xlsx`), so every machine running a
  current checkout names exports correctly (the Dell had no calendar and every
  export silently fell back to `race_<id>_results.csv` with an empty Series).
- `_calendar_events_by_date()` parses the xlsx ONCE into a `{date: event}` map
  (same rules as before: non-racing rows skipped, latest start-time row of a
  day wins — the Wednesday Twilight rule). `get_calendar_event_for_date()` is
  now a dict lookup on it.

### 2. Sailwave CSV export: series naming + series race numbers

`/api/export-race-csv` (Sailwave import format):
- **Series column** = the calendar event matched by the race's earliest
  recorded start (`_race_date`).
- **Race column** = `Race <n>` where n is `_series_race_number(race_id)`:
  the race's position WITHIN its series, incremental across the whole season
  (Twilight Series runs R1, R2, R3… every Wednesday), ordered by earliest
  recorded start; EVERY started race of the series counts (numbers stay
  stable). Without a calendar series it falls back to `_race_ordinal_of_day()`
  (race-of-day number).
- **Filename** = `<Series> <DD-MM-YYYY>.csv`, with ` R<n>` appended for races
  after the first of the series (so the day's races never overwrite each
  other); fallback `race_<id>_results.csv` when no calendar match.
- `scripts/export_race_by_id.py` re-exports ANY recorded race from ANY
  score.db copy (always via a scratch copy — feature 5 "results review +
  re-Export" groundwork).

### 3. Race state recovery after a mid-race restart (bug 27)

`recover_running_race()` runs at app start, in `if __name__ == '__main__'`
ONLY — never at import, because regression scripts swap `DB_PATH` after
importing:
- a RUNNING race with activity in the last 12h is ADOPTED back into
  `app_state` (race_id, class_start_times from `race_class_starts`,
  open_start_time from `race_open_starts`) so End Race / laps / export all
  target the live race;
- older RUNNING races are abandoned crash orphans — closed ENDED at their
  last activity time so they stop blocking the new session.
Root cause (24 Oct): race state is memory-only; a mid-race Flask restart
orphaned the RUNNING race, the finish sheet's manual Start Race then created
a DUPLICATE race, and the real race could never be ended or exported.

### 4. True lap counts for open-category sailors + late sign-ons (bug 28)

`/api/sailors-for-onwater`'s "live rows" query (the ONLY source of
open-category sailors — the started-classes query filters on `s.class_id`,
NULL for open sailors) now LEFT JOINs `race_sailors` and returns the REAL
`lap_count`/`finish_time`. Previously it hardcoded `0`, resetting the
on-sheet lap counter on every poll/re-render/browser refresh, so scorers
re-clicked and recorded duplicate laps seconds apart (24 Oct: Gabrielle
Marais, Europe/Open). PASSED human test 2026-10-27.

### 5. One-destination navigation (bug 30)

The station buttons on the RO page and the Race Officer Control button on
the finish sheets all navigate the CURRENT tab (no `target="_blank"`).
Station identity lives per browser tab (sessionStorage) — new tabs were
fresh, blank sessions that fought the real stations over captures. The
Display Board link keeps its new-tab behaviour BY DESIGN (it runs on the
separate outdoor screen). PASSED human test 2026-10-27.

### 6. RO page restores its sequence and resumes a running countdown (bug 31)

- `templates/index.html` embeds `window.INITIAL_SEQUENCE` from
  `app_state['sequence']`; `app.js restoreSequenceFromServer()` rebuilds
  every grid + row (primary/secondary/tertiary flags, labels, minutes,
  grid numbers) on page load when the page's own sequence is empty.
- Countdown resume: Start POSTs `countdown_started_ms` (epoch ms) via
  `/execute-control` START → stored as `app_state['fm_countdown_started_ms']`
  → carried by `/api/race-status` → the RO page's 500ms poller RESUMES the
  countdown from the real elapsed time when fm is RUNNING with a stored
  start. STOP / RESET / END_RACE clear it.
- `/api/class-start` accepts optional `started_at_ms` (PAST values only):
  when the RO page catches up on rows that completed while it was away, the
  start is recorded BACKDATED to its true crossing time. Re-fires are
  ignored (`INSERT OR IGNORE` — first trigger wins, no duplicates).
- The first tick after a resume catches up SILENTLY
  (`state.catchUpTick`): no horn blast / announcement pile-up for flags
  that went up/down while the page was away.

### New/changed endpoints + fields (Session 7)

| Where | Change |
|---|---|
| `/api/race-status` | + `fm_countdown_started_ms` |
| `/execute-control` | START stores `countdown_started_ms`; STOP/RESET/END_RACE clear it |
| `/api/class-start` | + optional `started_at_ms` (backdating, past only) |
| `/api/sailors-for-onwater` | live rows carry REAL lap_count/finish_time |
| `/api/export-race-csv` | Series column, `Race <n>`, series+date filename with `R<n>` |
| `/` (index.html) | + `window.INITIAL_SEQUENCE` |

### Regression scripts added (Session 7)

`scripts/test_export_naming.py`, `test_race_recovery.py`,
`test_open_lap_counts.py`, `test_navigation.py`, `test_ro_restore.py`
(full suite: 17 scripts). Note: export tests are HERMETIC — they clear the
race history in their scratch copy, because the live DB accumulates same-day
test races and the series race number counts every started race.

### Known gaps / limitations (Session 7)

- **The countdown only ticks while an RO page is open.** A class start that
  falls due while the RO page is away fires on RETURN (backdated correctly),
  but the finish sheet's lap buttons for that class stay locked until then.
  Server-side countdown timing is the future fix.
- Pause (STOP) → Start still RESTARTS the countdown from zero (unchanged
  behaviour); a reload during a pause does not auto-resume.
- Bug 26 (more drag-and-drop space in start-event boxes) still open.

