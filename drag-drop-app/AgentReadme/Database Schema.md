# Database Schema — score.db (SQLite)

Single SQLite database, created and migrated automatically by `app.py` on startup.
All race-day truth lives here; the server also keeps a small in-memory `app_state`
(sequence, timers, class start times) that is rebuilt from this DB on restart.

Last verified 2026-10-16 (regatta prep, commit `04553d8`).

---

## Tables

| Table | Purpose |
|---|---|
| `sailors` | The club fleet registry — one row per sailor. Managed via the Sailor Registry sidebar and refreshed from Sailwave (`scripts/import_sailwave.py`) |
| `boat_classes` | Boat classes: name, flag image, UI color. Single source of truth for class flag lookups (case-insensitive) |
| `races` | One row per race, auto-created when the first class-start POST fires |
| `race_sailors` | The locked roster for a race: who was signed on at their class start, their lap count, finish time, manual placement |
| `race_class_starts` | Start time + sequence number for each class in a race (class flag went down) |
| `race_open_starts` | Same for the Open Category when the RO used the openclass flag (race_id UNIQUE) |
| `lap_records` | One row per recorded lap: sailor, race, lap number, timestamp (feeds CSV lap times) |
| `sqlite_sequence` | SQLite internal (AUTOINCREMENT counters) — never edit |

---

## sailors — the fleet

```sql
uid          TEXT PRIMARY KEY     -- SL-<sail no> by convention, e.g. SL-2045.
                                 -- Optional in the Add form; auto-generated if blank,
                                 -- suffixed -2/-3... if taken (bug 23 fix)
sailor_name  TEXT NOT NULL
short_name   TEXT NOT NULL        -- shown on cards and registry
sail_no      TEXT UNIQUE NOT NULL -- UNIQUE: adding a duplicate is refused with the
                                 -- existing sailor's name (bug 23 fix)
boat_class   TEXT NOT NULL        -- legacy text class; class_id is authoritative
handicap     REAL  DEFAULT 1.0    -- tie-break for on-water ordering
seed         INTEGER DEFAULT 0    -- sign-on order tie-break
class_id     INTEGER FK -> boat_classes.class_id
racing_today INTEGER DEFAULT 0    -- sign-on tick for today; only 1s appear on the sheet
status       TEXT DEFAULT 'racing'
finish_order INTEGER DEFAULT NULL -- legacy
finish_time  TEXT DEFAULT NULL    -- legacy
```

## boat_classes

```sql
class_id    INTEGER PK AUTOINCREMENT
class_name  TEXT UNIQUE NOT NULL  -- matches Sailwave class names (e.g. 'P Class')
flag_image  TEXT                  -- filename in static/flags/ (e.g. pclass.png)
color_hex   TEXT DEFAULT '#0369a1'
created_at  TIMESTAMP
```

Signal flags (`p.png`, `Dflag.png`, postpone...) have NO boat_classes row — the
server ignores them for class starts and they create no finish-sheet columns.
The deleted bogus class 'P' (claiming p.png) must not be recreated; its import
mapping was removed from `scripts/import_sailwave.py`.

## races

```sql
race_id   INTEGER PK AUTOINCREMENT
start_time TEXT
status    TEXT DEFAULT 'READY'    -- READY / RUNNING / ENDED
class_groups TEXT
created_at TIMESTAMP
end_time  TEXT                    -- set by /api/end-race
```

Exactly one race is auto-created per race day session — the server-side
`RACE_STATE_LOCK` guarantees concurrent class-start POSTs can never create two.

## race_sailors — locked roster per race

```sql
id           INTEGER PK AUTOINCREMENT
race_id      INTEGER FK -> races
uid          TEXT FK -> sailors
lap_count    INTEGER DEFAULT 0
finish_time  TEXT                  -- set by /api/mark-finish
placement    INTEGER               -- manual drag order (not yet persisted by the UI - feature 4d)
```

Sailors sign on AFTER their class start stay live in the registry until their
first lap/finish, then join this table without duplicating (bug 14).

## race_class_starts — class starts

```sql
id              INTEGER PK AUTOINCREMENT
race_id         INTEGER NOT NULL FK -> races
class_id        INTEGER NOT NULL FK -> boat_classes
start_time      TEXT NOT NULL
source          TEXT DEFAULT 'flag_machine'
sequence_number INTEGER DEFAULT 1  -- which Start grid fired (Start 1, Start 2...)
UNIQUE(race_id, class_id)
```

The start fires only when the LAST row of a start event's full flag sequence
completes (bug 21b). One POST carries ALL the grid's flags (primary, secondary
and tertiary slots).

## race_open_starts — Open Category start

```sql
id              INTEGER PK AUTOINCREMENT
race_id         INTEGER NOT NULL UNIQUE FK -> races
start_time      TEXT NOT NULL
sequence_number INTEGER DEFAULT 1
source          TEXT DEFAULT 'flag_machine'
```

Written when the openclass flag fires. The CSV export falls back to it for
sailors with no class start row (bug 21c). Without an open flag in the sequence,
open sailors fall back to the race's earliest class start.

## lap_records

```sql
id         INTEGER PK AUTOINCREMENT
race_id    INTEGER FK -> races
uid        TEXT FK -> sailors
lap_number INTEGER
timestamp  TEXT        -- full ISO timestamp, feeds CSV 'Lap Times'
```

---

## Relationships

```
boat_classes 1 ──* sailors (class_id)
sailors     1 ──* race_sailors (uid)        [per race]
races       1 ──* race_sailors (race_id)
races       1 ──* race_class_starts (race_id, per class)
races       1 ──1 race_open_starts (race_id UNIQUE)
races       1 ──* lap_records (race_id)
sailors     1 ──* lap_records (uid)
```

## Practical notes

- **Only one machine owns the live `score.db` at a time.** It is tracked in git,
  so each swap (Dell <-> dev laptop) should be committed so the other machine
  can pull it — but never overwrite a DB that has newer races recorded.
- Copy the file only while the Flask server is stopped on the source machine.
- Test scripts and the replay tool always work on scratch copies
  (`tempref/score_*.db`), never on the live DB.
