# Session 1 Wrap-Up: Sailor Scorer v1 Requirements Locked

**Status:** ✅ Complete  
**Date:** Current Session  
**Deliverables:** Requirements finalized, architecture designed, build plan ready

---

## What We Did

### 1. Reviewed Existing Codebase
- Examined Flag Machine architecture (app.py, Jinja templates, JavaScript)
- Analyzed existing scorer app (scorer_app.py) — sailor registry pattern
- Reviewed existing UI patterns (roster.html, score.js) — search, drag-drop, forms
- Identified reusable foundations (DB connection, Flask routes, CSS patterns)

### 2. Updated Requirements Document
**File:** `requirements.md`  
**Changes:**
- Renamed Part 1: "Flag Machine (Existing)" with unchanged specs
- Added Part 2: "Sailor Scoring Sheet (v1)" with full functional spec
- Moved old out-of-scope items to "Part 2 - Out of Scope"
- Added 6-phase future roadmap (v2–v6) showing:
  - Phase 2: Handicap scoring & calculations
  - Phase 3: Flag Machine integration
  - Phase 4: Export & reports
  - Phase 5: Persistent storage
  - Phase 6: Undo/reorder & corrections

### 3. Created Build Summary
**File:** `SAILOR_SCORER_V1_SUMMARY.md`  
**Content:**
- Plain-English explanation of v1 scope
- Grounded foundations (what's reusable)
- Exact build checklist
- Data flow diagrams
- Design decisions rationale

---

## v1 Scope (Locked)

### What We're Building
**Manual finish-time recorder** for capturing individual sailor results during a race.

**User flow:**
1. Create/select active race (name, date, start time)
2. Search for sailor from registry (by name, sail no, or class)
3. Enter finish time (MM:SS format)
4. Click "Record Finish" → sailor + time appends to results
5. Table updates live, sorted by finish order
6. Optional: Delete entries before race marked FINISHED
7. End Race → all input locked

### Core Features (v1)
- ✅ Sailor registry integration (pull from roster.db, filter racing_today=1)
- ✅ Race session management (READY → ACTIVE → FINISHED)
- ✅ Manual finish time entry (MM:SS → seconds storage)
- ✅ Results table (place | name | sail no | class | time)
- ✅ Real-time form + table (no page reloads)
- ✅ Delete/undo entries (before FINISHED)
- ✅ Form validation (no duplicates, time format, status locking)

### What's NOT in v1 (Intentional Cuts)
- ❌ Handicap scoring / net time calculation
- ❌ Flag Machine integration (finish time auto-capture)
- ❌ Persistent storage (session memory only)
- ❌ Re-ordering finish positions (order locked at entry)
- ❌ PDF/CSV export
- ❌ Multi-race simultaneous sessions

---

## Architecture Decisions (v1)

### Database
**New tables (add to roster.db):**
```sql
races (race_id, race_name, race_date, start_time, race_start_timestamp, status)
race_results (result_id, race_id, uid, finish_time_seconds, finish_order)
```

### Backend (Flask)
**7 new endpoints:**
1. `POST /races` — Create race session
2. `GET /races` — List races
3. `GET /races/<race_id>` — Get race + results
4. `PUT /races/<race_id>` — Update status (READY → ACTIVE → FINISHED)
5. `POST /races/<race_id>/results` — Record finish (uid + time_seconds)
6. `DELETE /races/<race_id>/results/<result_id>` — Remove entry
7. `GET /api/racers/<race_id>` — Fetch active sailors for selector

### Frontend
**Files to create:**
- `templates/scorer.html` — UI template
- `static/js/scorer.js` — Form logic + table rendering
- Optional: `static/css/scorer.css` or inline styles

**Reuse from existing:**
- Sidebar collapse pattern (from score.html)
- Real-time search logic (from score.js)
- Fetch API patterns (from app.py)
- CSS framework (roster.css + style.css)

### UI Layout
```
┌─ Top Bar (race info: name, date, status, elapsed time) ─────────┐
├─────────────┬──────────────────────────────────────────────────────┤
│ Sidebar     │ Main Panel                                             │
│ • Search    │ ┌─ Form Area ─────────────────────────────────────┐  │
│ • Filter    │ │ Sailor selector (autocomplete)                  │  │
│   by class  │ │ Time input (MM:SS)                             │  │
│             │ │ [Record Finish] button + entry count           │  │
│             │ └─────────────────────────────────────────────────┘  │
│             │ ┌─ Results Table ──────────────────────────────────┐  │
│             │ │ Place | Name | Sail No | Class | Time | Delete  │  │
│             │ │ 1     | John | 123    | ILCA  | 1:23 | [X]      │  │
│             │ │ 2     | Jane | 456    | ILCA  | 1:45 | [X]      │  │
│             │ │ ─────────── (class divider) ───────────────────  │  │
│             │ │ 3     | Bob  | 789    | Star  | 2:10 | [X]      │  │
│             │ └─────────────────────────────────────────────────┘  │
└─────────────┴──────────────────────────────────────────────────────┘
```

---

## Build Sequence (Next Session)

### Phase A: Backend Foundation
1. **Database setup** (5 min)
   - Add `races` + `race_results` tables to roster.db
   - Update init_db() in app.py

2. **Flask endpoints** (30 min)
   - 7 new routes (CRUD operations)
   - Input validation (duplicate check, time format)
   - Auto-assign finish_order
   - Status locking on FINISHED

### Phase B: Frontend UI
3. **scorer.html template** (20 min)
   - Sidebar with sailor search
   - Form area (autocomplete + time input)
   - Results table with live binding

4. **scorer.js logic** (40 min)
   - Sailor autocomplete (search, filter by class)
   - Time parsing (MM:SS → seconds, handle edge cases)
   - Form submission (POST race result)
   - Live table render (sorted by finish_order, grouped by class)
   - Delete row logic
   - Status locking (disable inputs when FINISHED)

### Phase C: Testing & Polish
5. **End-to-end test** (15 min)
   - Create race, record finishes, verify table updates
   - Delete entries, verify re-ranking
   - Lock race, verify input disabled
   - Test edge cases (bad time format, duplicate sailor, etc.)

6. **CSS polish** (10 min)
   - Button styles, table borders, hover effects
   - Responsive form layout
   - Class grouping visual dividers

**Total estimated time:** 2–2.5 hours

---

## Key Files Reference

### Documentation
- `requirements.md` — Full spec (Part 1: Flag Machine, Part 2: Sailor Scorer v1, Future phases)
- `SAILOR_SCORER_V1_SUMMARY.md` — Build guide (this file's companion)
- `SESSION_1_WRAPUP.md` — This file

### Existing Code (Patterns to Reuse)
- `app.py` — Flask structure, database pattern
- `scorer_app.py` — Sailor filtering, grouping pattern
- `templates/score.html` + `static/js/temp/score.js` — Sidebar, search, Kanban drag-drop
- `static/css/roster.css` + `static/css/style.css` — Styling foundation

### To Create (Next Session)
- `templates/scorer.html` — UI
- `static/js/scorer.js` — Logic
- (Optional) `static/css/scorer.css` — Styles

### To Modify (Next Session)
- `app.py` — Add 7 endpoints
- `roster.db` (schema) — Add 2 tables

---

## Assumptions & Constraints

### Session Scope (v1)
- ✅ **Manual entry only** — Officer stands at finish line, enters time manually
- ✅ **One active race** — Only one race per session; can create new race anytime
- ✅ **In-memory session** — Data lost on app restart (no persistence in v1)
- ✅ **Locked finish order** — No re-ordering after entry (prevents human error)
- ✅ **Time format: MM:SS** — User enters "1:23:45" or "1:45"; backend converts to seconds

### Not Assumed (Future Work)
- ❌ Finish time auto-capture from Flag Machine (v2 feature)
- ❌ Handicap calculations (v2 feature)
- ❌ Export to CSV/PDF (v3/v4 feature)
- ❌ Multi-user role-based access (later feature)
- ❌ Mobile responsive design (later feature)

---

## Quick Reference: v1 Data Model

### Races Table
```
race_id (PK):              'RACE-2025-01-15-001'
race_name:                 'Saturday Fleet Race 1'
race_date:                 '2025-01-15'
start_time:                '10:30'
race_start_timestamp:      1705318200.0 (Unix time, null until START clicked)
status:                    'READY' | 'ACTIVE' | 'FINISHED'
created_at:                1705317900.0
```

### Race Results Table
```
result_id (PK):            'RES-abc123'
race_id (FK):              'RACE-2025-01-15-001'
uid (FK):                  'SL-1234567890'
finish_time_seconds:       5025 (e.g., 1h 23m 45s)
finish_order:              1 (1st place), 2 (2nd), etc.
recorded_at:               1705318245.0
```

### Sailors Table (Existing, Read-Only in v1)
```
uid (PK):                  'SL-1234567890'
sailor_name:               'John Doe'
short_name:                'J. Doe'
sail_no:                   '12345'
boat_class:                'ILCA 6'
handicap:                  1045.0 (stored but not used in v1)
seed:                      5 (informational only in v1)
racing_today:              1 (0 = not racing)
```

---

## Ready for Next Session

✅ **Requirements locked** — v1 scope is defined and approved  
✅ **Architecture designed** — Database schema, endpoints, UI layout finalized  
✅ **Build plan ready** — Step-by-step sequence, estimated times  
✅ **Reusable patterns identified** — No need to reinvent wheels  
✅ **Future roadmap drafted** — 6 phases for v2–v6 enhancements  

**Next session:** Start with database schema creation, then build Flask endpoints, then UI.

---

## Questions for Next Session?

Before starting backend:
- Any changes to the UI layout?
- Any additional fields to capture at race creation?
- Preference for endpoint naming (already outlined above)?
- Want to store any extra metadata on race_results (e.g., notes, manual adjustments)?

All locked and ready to build. See you next time!
