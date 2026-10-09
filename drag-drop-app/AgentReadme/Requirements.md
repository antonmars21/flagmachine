# Requirements: Flag Machine + Finish Sheet v1.2

---

## PART 1: FLAG MACHINE (Sessions 1–3 + Session 5 Enhancements)

### 1. Control Panel Interface
- **Multi-grid support:** Define N boat classes with separate sequences (unlimited dynamic creation via "+" button)
- **Grid management:** Add/Remove start sequence grids with unique visual identification
- **Flag library:** Drag-and-drop library of flag images (PNG/JPG from `/static/flags/`)
- **Sequence builder:** Drag flags into grid to create event sequence
- **Countdown settings:** Each row shows editable duration in whole minutes (min 1, default based on flag)
- **Live countdown display:** Each row shows MM:SS format countdown (e.g., "00:45")
- **Grid total countdown:** Display sum of all remaining rows per grid
- **Row reordering:** Drag rows within same grid to reorder sequence
- **Secondary flags:** Option to add a second flag per row (cosmetic only; doesn't affect timing)
- **Remove rows:** Delete button to remove individual rows from sequence
- **Race control buttons:** START (green), STOP (red), RESET (gray), END RACE (blue)

### 2. Race Timing Engine
- **Dual start trigger:** Manual (START button) or Automatic (system clock ≥ master_start_time)
- **Countdown calculation:** Elapsed time since race start
- **Cumulative sequencing:** Each row begins at sum of all previous row durations
- **Row state transitions:** PENDING → ACTIVE → CLEAR based on elapsed time
- **Update frequency:** 100ms tick rate

### 3. UI Locking During Race
- Drop zones, row dragging, remove buttons, minutes editors all locked when RUNNING

### 4. Display Board (Outdoor)
- Large flag image + whole-minute countdown
- Toggle hide/show countdown
- Polls `/api/display-state` every 500ms

### 5. Server-Side Features
- REST API for sequence, settings, control, display-board data
- State persistence: per-session only (no database)

---

## PART 2: FINISH SHEET v1.2 (Session 5 — COMPLETED ✓)

### Overview

**Integrated into main app.py** (port 5000). Replaces Sailor Scorer v1.0 front-end. Allows dual operators to record lap counts and finish times for sailors on the water in real-time.

**Served at:** `http://localhost:5000/finishsheet`
**Database:** `score.db` (merged Session 2 + Session 3 + Session 5 schema)
**Backend:** app.py (Flask, port 5000, debug=True)

---

### v1.2 Features (Session 5 Enhancements)

#### 1. Dynamic Column Sailor Display

**Layout:**
- **Unlimited columns**: Automatically adapts to number of start sequences + classes
- **Sequence-aware**: Columns grouped by start sequence (Start 1, Start 2, etc.)
- **Empty columns**: Shows columns for classes in sequence even with zero sailors
- **Open Category**: Trailing column for sailors with classes not in any sequence

**Sailor grouping logic (verified working, 2026-10-09):**

Sources of truth:
- Flag Machine start sequence: which classes start, and in what order (grid_index)
- `boat_classes` table: maps class_id to a flag_image
- `sailors` table: each sailor's `racing_today` flag and `class_id`

Rules:
1. Only sailors checked in the Sailor Registry (`racing_today = 1`) appear on the finish sheet.
2. The countdown sequence may contain N separate starts with class flags. Each flag in the sequence is matched (case-insensitive) to a `boat_classes` row via `flag_image`, producing one column per class start.
3. Sailors whose `class_id` matches a class in the current sequence land in that class's column, grouped by (class_id + sequence/grid index).
4. Any sailor whose class is NOT in the current sequence — or who has no class or whose class has no flag — automatically lands in the trailing "Open Category" column.
5. Columns sort by sequence number first, then sailor count descending. Classes in the sequence with zero signed-on sailors still show an empty column.
6. Once a class has started, its roster locks to the sailors who were signed on at that class's start moment (`race_sailors`). Classes not yet started stay live, reflecting registry checkbox changes in real time.

Data integrity (enforced automatically at every app startup):
- `sailors.class_id` is re-synced to `boat_classes` by case-insensitive boat class name. Sailors whose class matches no boat class get `class_id = NULL` and therefore group into Open Category.
- `boat_classes.flag_image` is re-scanned against the files in `/static/flags/`. Classes whose flag is NULL or missing on disk are matched to a flag file by normalized class name (e.g. "Ilca 7" → `ilca7.png`), or a documented alias ("3.7" → `farr3point7.png`). Classes with no matching flag image keep `flag_image = NULL` → their sailors group into Open Category.

Sailor data source (Sailwave integration):
- Sailors are imported via the "Refresh Sailwave" button from `C:\Users\Public\Documents\Sailwave\Flagmachine_database\Boats_Master.xml`.
- The XML `compclass` field (the division, e.g. "ILCA 6") determines a sailor's boat class. `compfleet` (coarse fleet, e.g. "ILCA") is ignored.
- `short_name` is the helm's first name; `sailor_name` is the full helm name; UID is `SL-<sail_no>`.

**Sailors per class (current data):**
- Database: 55 sailors across 11 boat classes, imported from Boats_Master.xml
- Dynamic: Varies based on racing_today selection and Flag Machine sequences

#### 2. Sailor Card Display

**Card format (single row per sailor):**
```
[Sail No]  [Boat Class]
[Nickname (e.g., "Werner")]
[+ Lap] [Lap Count] [Finish Checkbox]
```

**Card styling:**
- Default: dark blue background (`#1a2332`), white text
- Sail number: `#f59e0b` (amber, high contrast)
- Nickname: `#cbd5e1` (light grey)
- Class: `#94a3b8` (muted grey)
- Hover: lift effect + border highlight
- **Finished state:** green background (`#064e3b`), sail number amber, checkbox checked + disabled

**Card interactions:**
1. **+ Lap button:** Increments lap counter. Disabled until race starts.
2. **Lap counter:** Shows current lap count (0 pre-race, increments per click). Reads from `race_sailors.lap_count`.
3. **Finish checkbox:** Marks sailor as finished. Disabled until race starts. Once checked, disabled (can't uncheck). Adds `.finished` class to card.

#### 3. Top Banner

**Elements:**
- **Left:** "⚓ FINISH SHEET" logo/title
- **Center:** Elapsed time display (MM:SS format, updates every 1 second)
- **Right:** "▶ Start Race" button (green, enabled pre-race), "⏹ End Race" button (red, disabled pre-race)

**Button states:**
- **Pre-race:** Start enabled, End disabled, all sailor buttons disabled
- **Race active:** Start disabled, End enabled, all sailor buttons enabled, elapsed time counting
- **Post-race:** Start enabled, End disabled, all sailor buttons disabled

#### 4. Start Race Flow

**Trigger:** User clicks "▶ Start Race" button

**Sequence:**
1. `finishsheet.js`: Collect all sailor UIDs from all 4 columns
2. POST `/api/start-race { selected_sailors: [uid1, uid2, ...] }`
3. Backend (`app.py`):
   - Insert into `races` table, get `race_id`
   - For each sailor: INSERT into `race_sailors` with `lap_count=0, finish_time=NULL, placement=NULL`
   - Set `app_state['race_id']`, `app_state['race_start_timestamp']` (ISO format)
4. Frontend:
   - Set `state.race_active = true`
   - Disable Start button, enable End button
   - Enable all lap + finish buttons on sailor cards
   - Start polling `/api/get-elapsed-time` every 1 second

#### 5. Recording Laps

**Trigger:** Operator clicks "+ Lap" button on sailor card

**Sequence:**
1. `finishsheet.js`: recordLap(uid, card)
2. Check: `if (!state.race_active) { alert('No active race') }`
3. POST `/api/record-lap { uid }`
4. Backend:
   - `UPDATE race_sailors SET lap_count = lap_count + 1 WHERE race_id = ? AND uid = ?`
   - Query updated `lap_count`
   - INSERT into `lap_records` with `lap_number, timestamp` (ISO format)
5. Frontend:
   - Update `.lap-value` text to new count
   - Card visual feedback (optional: subtle pulse or flash)

#### 6. Marking Finish

**Trigger:** Operator checks "Finish" checkbox on sailor card

**Sequence:**
1. `finishsheet.js`: markFinish(uid, is_checked, card)
2. Check: `if (!state.race_active || !is_checked) { return }`
3. POST `/api/mark-finish { uid }`
4. Backend:
   - `UPDATE race_sailors SET finish_time = NOW() WHERE race_id = ? AND uid = ?`
5. Frontend:
   - Add `.finished` class to card (green tint, lower opacity)
   - Disable checkbox (prevent uncheck)
   - Append "(Finished)" to nickname text (optional)

#### 7. Elapsed Time Display

**Trigger:** Every 1 second (while race is active)

**Sequence:**
1. `finishsheet.js`: updateElapsedTime() (called via `setInterval(..., 1000)`)
2. GET `/api/get-elapsed-time`
3. Backend:
   - Calculate `elapsed = now - race_start_timestamp`
   - Return `{ elapsed_seconds, formatted: "MM:SS" }`
4. Frontend:
   - Update `#elapsed-time` element with formatted time

#### 8. Manual Reordering (Future — Post-Session 4)

**Trigger:** Drag sailor card within/across columns (post-race)

**Logic:**
- Drag & drop (draggable=true on sailor cards)
- Reorder rows within same column
- Move sailors between columns
- POST `/api/reorder-sailors { placements: [{uid, placement}, ...] }`
- Update `race_sailors.placement` field

#### 9. End Race

**Trigger:** User clicks "⏹ End Race" button

**Sequence:**
1. `finishsheet.js`: endRace()
2. Set `state.race_active = false`
3. Disable all sailor buttons (lap, finish)
4. Disable End button, re-enable Start button
5. Stop elapsed time polling
6. Data persisted in `race_sailors` + `lap_records` tables

---

### v1.2 API Endpoints (Session 5 Additions)

**New endpoints:**
```
GET  /api/lap-times/<uid>          # Get lap times for a specific sailor
```

**Modified endpoints:**
```
POST /api/class-start              # Added: sequence_number parameter
GET  /api/sailors-for-onwater      # Enhanced: sequence-aware grouping, empty columns
GET  /api/export-race-csv         # Enhanced: sequence_number and lap_times columns
```

### v1.2 Database Schema (Session 5 Additions)

**New column:**
```sql
-- Added to race_class_starts table
ALTER TABLE race_class_starts ADD COLUMN sequence_number INTEGER DEFAULT 1
```

**Modified behavior:**
- `race_class_starts` now stores sequence_number from Flag Machine grid_index
- `/api/sailors-for-onwater` uses sequence_number for grouping
- Lap times stored in existing `lap_records` table with timestamps

---

### v1.1 Database Schema (Session 3 Merge)

**Merged schema: Session 2 sailors table + Session 3 race tracking tables**

```sql
-- Session 2: Fleet registry (preserved, used by Finish Sheet for initial display)
CREATE TABLE sailors (
    uid              TEXT PRIMARY KEY,
    sailor_name      TEXT NOT NULL,
    short_name       TEXT NOT NULL,
    sail_no          TEXT UNIQUE NOT NULL,
    boat_class       TEXT NOT NULL,
    handicap         REAL DEFAULT 1.0,
    seed             INTEGER DEFAULT 0,
    
    -- Legacy Session 2 columns (NOT used in Finish Sheet, kept for backward compatibility)
    racing_today     INTEGER DEFAULT 0,
    status           TEXT DEFAULT 'racing',
    finish_order     INTEGER DEFAULT NULL,
    finish_time      TEXT DEFAULT NULL
);

-- Session 3: New race tracking
CREATE TABLE races (
    race_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time       TEXT,
    status           TEXT DEFAULT 'READY',
    class_groups     TEXT,  -- JSON list of class names for this race
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session 3: Which sailors in which race + lap/finish tracking
CREATE TABLE race_sailors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id          INTEGER NOT NULL,
    uid              TEXT NOT NULL,
    lap_count        INTEGER DEFAULT 0,
    finish_time      TEXT DEFAULT NULL,  -- ISO format timestamp
    placement        INTEGER DEFAULT NULL,
    FOREIGN KEY(race_id) REFERENCES races(race_id),
    FOREIGN KEY(uid) REFERENCES sailors(uid)
);

-- Session 3: Audit trail for each lap recorded
CREATE TABLE lap_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id          INTEGER NOT NULL,
    uid              TEXT NOT NULL,
    lap_number       INTEGER NOT NULL,
    timestamp        TEXT NOT NULL,  -- ISO format timestamp
    FOREIGN KEY(race_id) REFERENCES races(race_id),
    FOREIGN KEY(uid) REFERENCES sailors(uid)
);
```

**Session 4 test data:**
- 27 sailors in `sailors` table
- 1 active race created (race_id=5)
- 5 sailors added to race_sailors for testing

---

### v1.1 REST API

| Method | Route | Body | Response |
|--------|-------|------|----------|
| GET | `/finishsheet` | — | HTML page (finishsheet.html) |
| GET | `/api/sailors-for-onwater` | — | `{ status, columns: {1: [...], 2: [...], 3: [...], 4: [...]}, class_groups }` |
| POST | `/api/start-race` | `{ selected_sailors: [uid, ...] }` | `{ status, race_id }` |
| POST | `/api/record-lap` | `{ uid }` | `{ status, lap_count }` |
| POST | `/api/mark-finish` | `{ uid }` | `{ status, finish_time }` |
| GET | `/api/get-elapsed-time` | — | `{ status, elapsed_seconds, formatted }` |
| POST | `/api/reorder-sailors` | `{ placements: [{uid, placement}, ...] }` | `{ status }` |

**Column data format:**
```json
{
  "status": "success",
  "columns": {
    "1": [
      {
        "uid": "SL-xxx",
        "sail_no": "123",
        "short_name": "Werner",
        "boat_class": "Ilca 6",
        "seed": 1,
        "lap_count": 0,
        "finish_time": null,
        "placement": null
      },
      ...
    ],
    "2": [...],
    "3": [...],
    "4": [...]
  },
  "class_groups": ["Ilca 6", "Starling", "Optimist", "Open"]
}
```

---

## DEPRECATION NOTICE: Sailor Scorer v1.0 (Session 2)

**Status:** DEPRECATED — Front-end decommissioned, back-end functions merged into Finish Sheet v1.1

**What's deprecated:**
- `score.py` (port 5001, `/score` route)
- `templates/score.html` (kanban board UI)
- `static/js/score.js` (v1.0 drag-drop logic)

**What's preserved:**
- `score.db` database + `sailors` table (fleet registry)
- Legacy columns for backward compatibility

**Decommissioning plan:**
1. ✓ Session 3: Build Finish Sheet v1.1 as replacement
2. ✓ Session 4: Test Finish Sheet functionality
3. Post-Session 4: Remove score.py from active codebase, archive to SessionDocs

---

## TESTING STATUS (Session 4)

### Manual Testing Verified ✓

- [x] `/finishsheet` page loads with banner + controls
- [x] 27 sailors display in 4 columns (14 + 4 + 3 + 6)
- [x] Sailor cards show sail_no, short_name, boat_class
- [x] `/api/start-race` creates race, adds sailors to race_sailors
- [x] `/api/record-lap` increments lap count + timestamps lap_records
- [x] `/api/mark-finish` sets finish_time in race_sailors
- [x] `/api/get-elapsed-time` returns elapsed MM:SS

### TODO (Post-Session 4)

- [ ] JavaScript verification: column key handling ('1', '2', '3', '4')
- [ ] Finish checkbox: green tint + disabled state visual
- [ ] Lap button: disabled pre-race, enabled race-active, counts update
- [ ] Drag-drop reordering: within columns, across columns, placement save
- [ ] End race: disable all buttons, preserve data
- [ ] CSV export: race results with finish order, times, laps
- [ ] Multi-race per day: session switching

---

## FUTURE ENHANCEMENTS (v2+)

### Phase 2 — Handicap Scoring
- Calculate net time = `finish_time_seconds / handicap`
- Rank by net time; display both gross and net

### Phase 3 — CSV Export & Reports
- PDF export with class breakdown, finish order, lap counts
- Print-friendly layout

### Phase 4 — Data Persistence
- Store race results in database for historical reference
- Multi-race per day with series scoring

### Phase 5 — Mobile / Tablet Optimization
- Touch-friendly button sizing
- Landscape/portrait modes

### Phase 6 — Corrections & Undo
- Edit finish time post-entry
- DNS marking
- Protest handling

---

## Out of Scope (Not v1.1)

- Audio/visual finish line alerts
- Barcode/RFID scanning
- Role-based access control
- Multi-user concurrent locking
- Real-time sync to multiple tablets
