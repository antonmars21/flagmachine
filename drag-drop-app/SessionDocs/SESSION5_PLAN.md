# Session 5 Plan: Countdown Integration + Sailor Registry Selection + Boat Class Flags

**Status**: Planning (Post-Session 4)  
**Focus**: Connect Flag Machine countdown to Finish Sheet race start, restore sailor registry pre-race selection, implement boat class ↔ flag mapping table

---

## OVERVIEW

Session 4 achieved core Finish Sheet layout and database functionality. Session 5 will:
1. **Link Flag Machine countdown to Finish Sheet** — Trigger race start from Flag Machine START button, not manual Finish Sheet button
2. **Restore sailor registry selection UI** — Pre-race "select sailors for today's course" interface before countdown
3. **Implement boat class ↔ flag mapping table** — Eliminate hardcoded class names, prevent typos via relational reference

---

## OBJECTIVES

### Objective 1: Link Flag Machine Countdown to Finish Sheet Race Start

**Current state (Session 4):**
- Flag Machine and Finish Sheet run on same Flask app (app.py, port 5000)
- Finish Sheet has manual "▶ Start Race" button
- These are decoupled; no data flow between them

**Desired state (Session 5):**
- Race officer opens Flag Machine (http://localhost:5000/)
- Sets up flag sequence + countdown
- Clicks START (or countdown auto-triggers at `master_start_time`)
- Flag Machine sets `app_state['status'] = 'RUNNING'`
- **Finish Sheet automatically detects race start** via `/api/race-status` polling
- Finish Sheet automatically calls `/api/start-race` with selected sailors
- Both UIs sync: Finish Sheet elapsed time = Flag Machine countdown

**Implementation:**
1. Add `/api/race-status` endpoint to app.py
   - Returns: `{ status: 'READY'|'RUNNING'|'PAUSED'|'ENDED', race_start_timestamp, master_start_time }`
2. Modify finishsheet.js
   - Poll `/api/race-status` every 500ms
   - Detect transition from READY → RUNNING
   - Auto-trigger `startRace()` when transition detected
3. Update Finish Sheet UI
   - Hide manual "▶ Start Race" button (replaced by automatic detection)
   - Show status indicator: "Waiting for countdown..." → "Race started at HH:MM:SS"

**Testing:**
- Open Flag Machine + Finish Sheet side-by-side
- Start countdown from Flag Machine
- Verify Finish Sheet auto-detects start + enables lap buttons
- Verify elapsed times sync (within 1 second)

---

### Objective 2: Restore Sailor Registry Selection UI

**Current state (Session 4):**
- Finish Sheet displays all 27 sailors immediately
- No pre-race registration/selection step
- Race starts with all sailors (or selected few via `/api/start-race`)

**Desired state (Session 5):**
- Finish Sheet loads with **registry sidebar** (like Session 2 Sailor Scorer v1.0)
- Sidebar shows all 27 sailors, sorted: unsigned first (alpha), signed-on bottom
- **Toggle checkboxes** to select "racing today"
- Large green "REGISTER SAILORS FOR TODAY" button
- When countdown triggers, only **checked sailors** are added to race
- After registration, sidebar collapses, main 4-column board appears

**UI Layout:**
```
┌─────────────────────────────────────────────────────┐
│ FINISH SHEET         [Status: Waiting for countdown] │
├─────────────────────────────────────────────────────┤
│ Sidebar (300px) │ Main Board (flex: 1)              │
│                 │                                    │
│ [Search]        │ [Waiting for race start...]       │
│                 │ (4-column grid hidden pre-race)   │
│ Fleet (all 27)  │                                    │
│ ☐ Sailor 1      │ After START:                      │
│ ☐ Sailor 2      │ [elapsed: 00:15]                 │
│ ...             │ Col 1  Col 2  Col 3  Col 4       │
│ ☑ Sailor 15     │ [14]   [4]    [3]    [6]         │
│ ☑ Sailor 16     │ sailors in cards                  │
│                 │                                    │
│ [REGISTER FOR   │                                    │
│  TODAY'S RACE]  │                                    │
└─────────────────┴────────────────────────────────────┘
```

**Implementation:**
1. Create new template `finishsheet_registry.html`
   - Sidebar with sailor list (checkboxes)
   - Search filter
   - Register button (disabled until ≥1 sailor checked)
2. Add route `/finishsheet-registry` (replaces `/finishsheet`)
3. Add API endpoints:
   - `POST /api/select-sailors-for-today` — Save checked UIDs to session state
   - `GET /api/get-selected-sailors` — Return list of UIDs marked for today
4. Modify finishsheet.js
   - Pre-race: show registry, hide main board
   - When race starts: show main board, collapse registry
5. Database: No schema change needed (use session state or temp flag in sailors table)

**Testing:**
- Load `/finishsheet-registry`
- Search + filter sailors
- Check 5 sailors, click "REGISTER FOR TODAY'S RACE"
- Wait for countdown trigger
- Verify only 5 sailors appear in main board (not 27)
- Verify sidebar collapses after race start

---

### Objective 3: Implement Boat Class ↔ Flag Mapping Table

**Current state (Session 4):**
- Boat class names hardcoded in code + database: "Ilca 6", "Starling", "Optimist", etc.
- Risk: typo errors → sailors not grouped correctly
- Flag images in `/static/flags/` loaded by filename scan
- No authoritative mapping between class name and flag image

**Desired state (Session 5):**
- New database table: `boat_classes`
  ```sql
  CREATE TABLE boat_classes (
      class_id     INTEGER PRIMARY KEY AUTOINCREMENT,
      class_name   TEXT UNIQUE NOT NULL,      -- "Ilca 6", "Starling", etc.
      flag_image   TEXT,                      -- "ilca6.png", "starling.png"
      color_hex    TEXT DEFAULT '#0369a1',    -- Column header color
      created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- Seed data (6 classes):
  - "Ilca 6" → ilca6.png → #0369a1 (blue)
  - "Ilca 7" → ilca7.png → #06b6d4 (cyan)
  - "Starling" → starling.png → #8b5cf6 (purple)
  - "Optimist" → optimist.png → #ec4899 (pink)
  - "P" → p_flag.png → #f59e0b (amber)
  - "Zephyr" → zephyr.png → #10b981 (green)
- Update sailors table: add `class_id` FOREIGN KEY (replace hardcoded class_name in queries)
- Update `/api/sailors-for-onwater`: join on boat_classes to get flag_image + color
- Frontend: Use flag_image from API, style column headers with color_hex

**Benefits:**
- Single source of truth for class names + flags
- Prevents typos (app enforces class_id, not free-text class_name)
- Easy to add/remove classes without code changes
- Sailors already in DB: backfill `class_id` from `class_name` lookup

**Implementation:**
1. Create migration script `migrate_boat_classes.py`
   - Create `boat_classes` table
   - Seed 6 class records
   - UPDATE sailors SET class_id = (SELECT class_id FROM boat_classes WHERE class_name = sailors.boat_class)
   - Add FOREIGN KEY constraint (or keep class_name for backward compat during transition)
2. Update app.py queries
   - `/api/sailors-for-onwater`: JOIN on boat_classes, return flag_image + color
3. Update finishsheet.js
   - Render column headers with `style="background-color: ${colorHex}"`
   - Use flag_image from API if provided
4. Keep `boat_class` TEXT column in sailors for backward compat

**Testing:**
- Run migration: `python migrate_boat_classes.py`
- Query boat_classes table: verify 6 records
- Query sailors: verify class_id populated
- Call `/api/sailors-for-onwater`: verify flag_image + color in response
- Load Finish Sheet: verify column headers color-coded
- Change one class color in DB, reload page: verify color updated

---

## DELIVERABLES (Session 5)

### Code Changes

| File | Change | Lines | Status |
|------|--------|-------|--------|
| app.py | Add `/api/race-status` endpoint | +15 | TODO |
| app.py | Add `/finishsheet-registry` route | +20 | TODO |
| app.py | Update `/api/sailors-for-onwater` to join boat_classes | +5 | TODO |
| app.py | Add `/api/select-sailors-for-today` endpoint | +10 | TODO |
| templates/finishsheet_registry.html | NEW: registry UI with sidebar + search + register button | +200 | TODO |
| static/js/finishsheet.js | Add race-status polling, auto-start detection | +30 | TODO |
| static/js/finishsheet.js | Add registry mode toggle, sailor filtering | +50 | TODO |
| migrate_boat_classes.py | NEW: create boat_classes table, seed data, backfill sailors | +80 | TODO |
| AgentReadme/SESSION5_PLAN.md | This file | — | ✓ |

### Database Changes

| Table | Change | Status |
|-------|--------|--------|
| races | Add `status` tracking (linked to Flag Machine) | ✓ (already present) |
| sailors | Add `class_id` FOREIGN KEY (optional, backward compat) | TODO |
| boat_classes | NEW table with class name ↔ flag mapping | TODO |

### Testing Checklist

- [ ] Flag Machine START → Finish Sheet auto-detects → race starts
- [ ] Finish Sheet elapsed time syncs with Flag Machine countdown
- [ ] Registry sidebar filters + searches sailors
- [ ] Register button enables only when ≥1 sailor checked
- [ ] After race starts, only registered sailors appear in 4-column board
- [ ] Boat class colors render in column headers
- [ ] Typo errors eliminated (class_id enforced)
- [ ] Backward compatibility: old sailor records still work
- [ ] Lap recording + finish marking still work post-migration

---

## DEPENDENCIES & RISKS

### Dependencies
- **Objective 1** requires: app_state['status'] already managed by Flag Machine (✓ Session 1)
- **Objective 2** requires: Objective 1 working (auto-start detection)
- **Objective 3** has no dependencies; can run in parallel

### Risks
- **Race-status polling lag:** 500ms poll interval may miss short countdown sequences. *Mitigation: Add event-based trigger (WebSocket) in future session.*
- **Sailor selection persistence:** If page refreshed pre-race, selection lost. *Mitigation: Use localStorage or database session table.*
- **Class name migration:** Backfilling class_id from class_name assumes 100% match. *Mitigation: Test migration on copy of DB first, verify no orphaned records.*

---

## TIMELINE

**Estimated effort:**
- Objective 1: 2–3 hours (polling, auto-detection, sync)
- Objective 2: 3–4 hours (registry UI, search, filtering, session state)
- Objective 3: 1–2 hours (migration script, FK setup, API update)
- Testing: 1–2 hours

**Total: 7–11 hours, likely 1 full session**

---

## SUCCESS CRITERIA (Session 5 Complete)

1. ✓ Flag Machine START button triggers Finish Sheet race auto-start (no manual button click)
2. ✓ Sailor registry UI allows pre-race selection (≥1 sailor can be unchecked)
3. ✓ Only registered sailors appear in 4-column board after race starts
4. ✓ Boat class colors render correctly in column headers
5. ✓ Boat classes table enforces unique class names (prevents typos)
6. ✓ All lap + finish functionality works post-migration
7. ✓ Page reloads without data loss
8. ✓ Manual testing pass: end-to-end flow (Flag Machine → Finish Sheet registry → race → lap → finish)

---

## NOTES FOR SESSION 5 AGENT

### Pre-Session Checklist
- [ ] Verify Session 4 app.py builds without errors
- [ ] Confirm score.db has 27 sailors, normalized boat_class names
- [ ] Check `/api/sailors-for-onwater` returns columns with all sailors
- [ ] Verify Flag Machine countdown works (START button sets app_state['status'] = 'RUNNING')

### Git Workflow (Optional)
```bash
git branch session-5
git checkout session-5
# ... implement objectives 1–3
git commit -m "Session 5: countdown integration, sailor registry, boat class mapping"
git merge main (after testing)
```

### Debug Tips
- Check browser console for finishsheet.js errors (race-status polling)
- Verify app_state in Flask: `print(app_state)` in endpoints
- Test migration dry-run: `SELECT * FROM boat_classes` post-migration
- Use browser DevTools to inspect column header styles (color_hex applied)

---

## FUTURE WORK (Post-Session 5)

- Session 6: Event-based sync (WebSocket instead of polling)
- Session 7: CSV export with lap counts + finish times
- Session 8: Handicap scoring (net time calculation)
- Session 9: Multi-race per day (series mode)
- Session 10: Mobile app / tablet UI optimization

---

**Prepared by**: Gordon (Docker AI Assistant)  
**Date**: Session 4 Post-Action  
**Next Action**: Begin Session 5 implementation
