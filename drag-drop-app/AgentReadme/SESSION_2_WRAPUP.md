# Session 2 Wrap-Up — Sailor Scorer v1.0

**Date:** July 2026
**Status:** ✅ Version 1.0 Complete — Tagged and pushed to git

---

## What Was Built This Session

A fully working race day scoring tool — **Sailor Scorer v1.0** — built from scratch alongside the existing Flag Machine in the same repo. The app runs independently at `http://localhost:5001/score`.

---

## Session Journey

### Starting Point
- Existing codebase had `scorer_app.py`, `roster.html`, `roster.js`, `roster.css`, `roster.db` — all naming was inconsistent and referenced "roster" throughout
- A previous prototype existed in `static/js/temp/score.js` (orphaned)

### Step 1 — Rename Everything to `score`
- Created `score.py` from `scorer_app.py` — fixed DB path → `score.db`, route → `/score`, template → `score.html`
- Updated `score.html` — CSS link, JS link, all class names
- Moved `score.js` from `/temp/` to canonical `static/js/score.js`
- Renamed CSS class `roster-dashboard-container` → `score-dashboard-container` across all files

### Step 2 — Load the Fleet
- Seeded `score.db` with 26 sailors from `sailor names.csv` via `seed_sailors.py`
- Classes: Ilca 6, Ilca 7, Optimist, P, Starling, Zephyr
- Fixed "Zephur" → "Zephyr" typo in DB
- Note: Scott Dawson appears 3× (different classes/sail numbers — intentional, races in different classes on different days)

### Step 3 — Sign-On UX
- Fleet list sort order: unsigned first (alphabetical by short name), signed-on at bottom
- Large custom green checkboxes as primary tap target
- Signed-on rows turn green-bordered
- Real-time search filter
- **< 5 seconds to sign on the entire fleet** ← key UX goal achieved

### Step 4 — Edit & Add Sailors
- ✏ edit button on each row → modal pre-filled with all fields
- PUT `/edit-sailor/<uid>` saves changes
- DELETE `/delete-sailor/<uid>` with confirmation
- Add New Sailor form collapsed by default (low priority)

### Step 5 — Kanban Race Board
- On Water column: seed order, flat (no class grouping), compact single-line tiles
- Drag On Water → Finished: appends to bottom, stamps `HH:MM:SS`
- Reorder within Finished: up or down
- Reorder within On Water: up or down (race officer adjusts predicted order mid-race)
- Lane count badges on both columns

### Step 6 — Naughty Corner
- DNF zone (red, dashed) and DQ zone (teal, dashed) at bottom of Finished column
- 144px open drop gap above naughty corner as clear target
- Drag to DNF/DQ clears finish time; drag back to On Water reinstates

### Step 7 — Tile Design
- Single line: `SailNo  Name (Class)`
- Sail number: white, monospace, bold (highest contrast)
- Name: `#c9d1d9` (slightly lower)
- Class: muted grey

### Step 8 — Finish Time Recording
- Timestamp (`HH:MM:SS`) captured client-side at exact moment of drop
- Stored in DB as `finish_time TEXT`
- Displayed as small badge on finished tiles

### Step 9 — CSV Export
- `⬇ CSV` button in Finished column header
- Downloads `race_results.csv`: Place, Short Name, Full Name, Sail No, Class, Seed, Status, Finish Time
- Finished → DNF → DQ → DNS ordering

### Step 10 — Reset Day
- Amber `↺ Reset Day` button in board header
- Confirmation dialog; clears all race data; preserves registry

### Step 11 — Scroll Persistence
- `localStorage` saves scroll position of fleet list, On Water, Finished
- Fleet list defaults to **bottom** on fresh load
- Scroll positions cleared on Reset Day

### Step 12 — Drag Fix (Up/Down in On Water)
- Root cause: `getBoundingClientRect` during live drag gives unstable positions
- Fix: snapshot all tile midpoints at `dragstart`; `getDragAfterElement` uses snapshot, not live DOM

---

## Files Changed / Created This Session

| File | Status |
|------|--------|
| `score.py` | Created (was scorer_app.py) |
| `score.db` | Created (was roster.db) |
| `templates/score.html` | Created (was roster.html) |
| `static/js/score.js` | Created (moved from temp/) |
| `static/css/score.css` | Created (was roster.css) |
| `seed_sailors.py` | Created (one-time use, kept for reference) |
| `AgentReadme/requirements.md` | Updated (Part 2 rewritten to reflect actual build) |
| `AgentReadme/architecture.md` | Updated (Part 2 added) |
| `AgentReadme/SESSION_2_WRAPUP.md` | Created (this file) |
| `SessionDocs/backup_v1/` | Created (snapshot of all v1 files) |

---

## DB State at v1.0

- **26 sailors** registered
- All have `racing_today = 0`, `status = 'racing'`, `finish_order = NULL`, `finish_time = NULL`
- Clean state — ready for first race day

---

## Architecture Decisions Made

| Decision | Why |
|----------|-----|
| Single `sailors` table | v1 is single-race per day; no race session table needed yet |
| Page reload on every state change | Guarantees sync between server and client; fast enough for race day |
| Client-side finish timestamp | Minimises latency at the critical finish moment |
| Seed order for On Water default | Race officer sets seeds pre-race; reflects expected finishing order |
| Position snapshot for drag | Live DOM positions during drag are wrong; snapshot at dragstart is stable |
| Fleet list scrolls to bottom | Unsigned sailors (to tick) appear at top; signed-on pushed down out of the way |

---

## Known Issues / Future Work

| Item | Notes |
|------|-------|
| Duplicate sail numbers | Multiple sailors share sail numbers (e.g. 1111 for 4 Ilca 6 sailors) — data reflects real fleet |
| `scorer_app.py` still in repo root | Old file, not used; can be deleted in a cleanup commit |
| `static/js/temp/` | Old temp files still present; can be cleaned up |
| `seed_sailors.py` | One-time use; safe to delete post-v1 |
| Handicap not used in v1 | Stored in DB, ready for v2 net time calculations |
| No race session concept yet | All sailors share a single `racing_today` flag; v2 will add multi-race/series |

---

## Next Session Priorities (v2 Candidates)

1. **Multi-race support** — race session table, run multiple races per day, carry fleet forward
2. **Handicap scoring** — net time = finish_time / handicap, rank by net time
3. **Series scoring** — cumulative points across races, discard worst
4. **Flag Machine integration** — pull start time from Flag Machine for auto elapsed time
5. **Clean up repo root** — remove scorer_app.py, roster files, temp JS

---

## How to Run

```bash
# Start the scorer (from repo root)
uv run --with flask score.py
# or
python score.py

# Open in browser
http://localhost:5001/score
```

```bash
# Start the Flag Machine (separate)
python app.py   # port 5000
```
