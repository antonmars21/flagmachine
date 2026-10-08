# Sailor Scorer v1 — Build Summary & Grounded Foundations

---

## What We're Building

**Sailor Scoring Sheet v1** is a **simple finish-time recorder** for capturing individual sailor results during a race. It runs as an **independent module** alongside the Flag Machine, integrating with the **existing Sailor Registry** (roster.db).

### v1 Scope: Manual finish time entry → results table

**User flow:**
1. Create or select an active race (name, date, start time)
2. Search for a sailor from the registry (by name, sail number, or class)
3. Enter their finish time (MM:SS or MM format)
4. Click "Record Finish" → sailor + time appends to results table
5. Table updates in real-time, sorted by finish order (1st, 2nd, 3rd, ...)
6. Optionally delete/undo entries before race is marked FINISHED
7. Mark race FINISHED → all input locked

**No handicap scoring, no Flag Machine integration, no persistence** in v1.

---

## Grounded Foundations (What's Already There)

### 1. Database Structure
- **File:** `roster.db` (SQLite)
- **Existing tables:**
  - `sailors` table with full profile (uid, sailor_name, short_name, sail_no, boat_class, handicap, seed, racing_today)
  - Used by the roster/Kanban app to manage fleet registry
- **New tables we'll add:**
  - `races` (race_id, race_name, race_date, start_time, race_start_timestamp, status)
  - `race_results` (result_id, race_id, uid, finish_time_seconds, finish_order)

### 2. Flask Backend
- **File:** `app.py` (main Flask app, currently handles Flag Machine)
- **What works:**
  - Database connection pattern (get_db_connection, init_db)
  - REST API structure (Flask routes, JSON responses)
  - State management (app_state dict)
- **Integration point:** We'll add Scorer endpoints to the same app.py (or new sailor_scorer.py module)
- **New endpoints needed:**
  - POST /races (create race)
  - PUT /races/<race_id> (update status)
  - POST /races/<race_id>/results (record finish)
  - GET /api/racers/<race_id> (fetch active sailors)
  - DELETE /races/<race_id>/results/<result_id> (undo entry)

### 3. Frontend Patterns
- **Existing HTML templates:** `index.html` (Flag Machine), `display.html` (outdoor board), `score.html` (roster Kanban)
- **Existing JS patterns:**
  - Real-time search filtering (in score.js: search_sailors_list example)
  - Kanban drag-drop (native browser API, no library)
  - Fetch API for server sync
  - Form handling + auto-focus logic
  - Page reload on save (score.js reloads after Kanban updates)
- **Existing CSS:** `roster.css` (sidebar + grid layout), `style.css` (Flag Machine styling)
- **What we'll reuse:**
  - Collapsible sidebar pattern (from score.html/score.js)
  - Real-time search + filtering
  - Form validation logic
  - Fetch/POST patterns

### 4. Sailor Registry Integration
- **scorer_app.py** already demonstrates:
  - Reading sailors from roster.db
  - Filtering by `racing_today = 1`
  - Organizing by boat_class
  - Grouping + sorting (by seed value)
- **We'll do similar:** Pull active sailors → display in autocomplete selector → store uid on finish record

### 5. Kanban State Management Pattern
- **File:** `static/js/temp/score.js`
- **Pattern:** Drag-drop → saveKanbanState() → fetch to /update-kanban → window.location.reload()
- **We won't copy the reload pattern** (too harsh for rapid entry); instead we'll use live DOM updates

---

## v1 Build Checklist

### Backend
- [ ] **Database schema:** Add `races` + `race_results` tables to roster.db
- [ ] **Flask endpoints:** 7 new routes (create race, update status, record result, fetch racers, delete result, list races, get race details)
- [ ] **Input validation:** Duplicate check, time format validation, race status lock on FINISHED
- [ ] **Auto-assignment:** Finish order auto-increments (1st entry = 1, 2nd = 2, etc.)

### Frontend (Templates)
- [ ] **HTML (scorer.html):**
  - Top bar: race info (name, date, status, elapsed time)
  - Left sidebar: sailor search + boat class filter
  - Main form: sailor autocomplete + time input + Record button
  - Results table: place | name | sail no | class | finish time
  - Close button on sidebar (toggle collapse like score.html)

### Frontend (JavaScript)
- [ ] **Race selector:** Dropdown to create or pick active race
- [ ] **Sailor autocomplete:** Search by name, sail no, or class (real-time filter, reuse score.js pattern)
- [ ] **Time parsing:** Accept "1:23:45", "1:23", "123" → convert to seconds (5025, etc.)
- [ ] **Form submit:** POST to /races/<race_id>/results → instant table update (no reload)
- [ ] **Table render:** Live DOM update, sorted by finish_order, grouped by boat_class (visual dividers)
- [ ] **Delete button:** Each row has remove btn → DELETE to /races/<race_id>/results/<result_id>
- [ ] **State locking:** When race.status = FINISHED, disable all inputs + hide Record button

### Frontend (CSS)
- [ ] Reuse roster.css sidebar + style.css button patterns
- [ ] Results table styling: borders, hover effects, place badges
- [ ] Responsive form layout (3-column input area)
- [ ] Optional: Class grouping visual dividers

---

## Files to Create/Modify

### New Files
- [ ] `templates/scorer.html` — v1 UI template
- [ ] `static/js/scorer.js` — v1 form + table logic
- [ ] Optional: `static/css/scorer.css` (or inline in scorer.html)

### Modified Files
- [ ] `app.py` — Add 7 new routes for Scorer API
- [ ] `roster.db` — Add races + race_results tables (via init_db() or SQL script)

### Existing (Reference Only)
- `scorer_app.py` — Shows sailor listing pattern (don't modify for v1)
- `score.html` / `score.js` — Patterns to reuse, not to integrate

---

## Data Flow (v1)

### Create Race
```
User form (race name, date, start time)
  ↓
POST /races
  ↓
Backend: Insert into races table (status=READY)
  ↓
Frontend: Update race selector, reset form
```

### Record Finish
```
User selects sailor + enters time
  ↓
POST /races/<race_id>/results { uid, finish_time_seconds }
  ↓
Backend: 
  - Query next finish_order = max(finish_order) + 1
  - Insert into race_results
  - Return updated results list
  ↓
Frontend:
  - Clear form, re-focus sailor selector
  - Live update results table (sort by finish_order)
  - Show updated entry count
```

### End Race
```
User clicks "End Race"
  ↓
PUT /races/<race_id> { status: 'FINISHED' }
  ↓
Backend: Update races table
  ↓
Frontend: 
  - Lock all inputs (disable form)
  - Hide Record button
  - Show "Race Finished" badge
```

---

## Key Design Decisions (v1)

1. **Manual entry only** — No auto-capture from Flag Machine (v2 feature)
2. **Session memory, not persistent** — Races/results lost on app restart (v2 = full DB)
3. **No re-ordering** — Finish order locked once entered (v2 = drag-reorder)
4. **No handicap math** — Store handicap from registry but don't calculate (v2 feature)
5. **Independent module** — Scoring sheet is separate from Flag Machine (clean separation, can run both simultaneously)
6. **Real-time form/table** — No page reloads (unlike Kanban app, which reloads after every change)
7. **Lightweight entry** — Single-page flow: pick sailor → enter time → click Record → repeat

---

## Next Steps

1. **Create database schema** — Add races + race_results tables to roster.db
2. **Write backend endpoints** — 7 Flask routes for CRUD operations
3. **Build scorer.html** — UI template with form + results table
4. **Write scorer.js** — Form logic, table updates, search filter, time parsing
5. **Test end-to-end** — Manual entry, real-time updates, status locking
6. **Plan v2** — Handicap scoring, Flag Machine sync, export

---

## References

- **Existing scorer_app.py:** Sailor registry filtering + grouping patterns
- **score.js:** Real-time search, Kanban drag-drop (avoid reload pattern)
- **app.py:** Flask route structure, JSON responses, database connection
- **requirements.md (Part 2):** Full v1 spec + future phases
