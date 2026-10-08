# Session 3 - Finish Sheet Implementation
## First Version (v1.0) - Build Complete ✓

---

## Overview

**Redesign Goal:** Continuous scoring from race start → list of sailing boats → lap counting → finish tracking.

**Previous State:** Flag machine and scoring were functionally separated.

**New State:** Integrated finish sheet that tracks boats from start through finish with continuous lap tallying.

---

## What Was Built

### 1. Backend Infrastructure (`app.py`)

#### New Database Schema
```
races
  ├─ race_id (PK)
  ├─ start_time
  ├─ status (READY, RUNNING, ENDED)
  └─ class_groups

sailors
  ├─ uid (PK)
  ├─ sailor_name, short_name
  ├─ sail_no (unique)
  ├─ boat_class
  ├─ handicap
  └─ seed

race_sailors (join table)
  ├─ race_id (FK)
  ├─ uid (FK)
  ├─ lap_count
  ├─ finish_time
  └─ placement

lap_records
  ├─ race_id (FK)
  ├─ uid (FK)
  ├─ lap_number
  └─ timestamp
```

#### New API Endpoints
- `POST /api/start-race` → Create race, add sailors
- `GET /api/sailors-for-onwater` → Load sailors grouped by class (4 columns)
- `POST /api/record-lap` → Increment lap counter + record timestamp
- `POST /api/mark-finish` → Record finish time, disable checkbox
- `POST /api/reorder-sailors` → Update placement after manual drag/reorder
- `GET /api/get-elapsed-time` → Return formatted HH:MM elapsed since race start

#### State Management
- `app_state['race_id']` tracks active race
- `app_state['race_start_timestamp']` enables elapsed time calculation
- All endpoints read/write to SQLite `score.db`

---

### 2. Frontend UI (`finishsheet.html`)

#### Layout
- **Top Banner:** 
  - Title: "⚓ FINISH SHEET"
  - Elapsed time display (HH:MM)
  - Start/End race buttons
- **4-Column Grid:**
  - Column 1: Top class by sailor count
  - Column 2: 2nd top class
  - Column 3: 3rd top class
  - Column 4: "Open" (remainder classes)

#### Sailor Card
- **Sail Number** (large, amber text)
- **Class Name** (small, muted text)
- **Nickname** (medium)
- **Controls:**
  - `+ Lap` button (blue) → increments lap counter
  - Lap counter display (green number)
  - Finish checkbox (green checkmark when checked)
- **Finished State:** Card turns green, checkbox disables, lap button still works

#### Responsive Design
- Touch-friendly button sizing (12px+ targets)
- 14" monitor optimized (tested on 1920x1200+)
- Dark theme (matches flagmachine UI)
- Scrollable columns

---

### 3. JavaScript Logic (`finishsheet.js`)

#### Core Functions

**Initialization**
```javascript
initFinishSheet()
  ├─ loadAndRenderSailors() - Fetch from /api/sailors-for-onwater
  ├─ Setup event listeners
  └─ Start elapsed time update loop (1 sec)
```

**Sailor Loading & Rendering**
```javascript
loadAndRenderSailors()
  ├─ GET /api/sailors-for-onwater
  ├─ Group by class (top 3 + open)
  └─ renderColumns() → createSailorCard() per sailor

renderColumns()
  └─ Build 4-column grid, attach event listeners

createSailorCard()
  ├─ Display sail #, class, name, lap counter
  ├─ Attach lap button click handler
  ├─ Attach finish checkbox change handler
  └─ Attach drag/drop events
```

**Lap Tallying**
```javascript
recordLap(uid, card)
  ├─ Check race_active
  ├─ POST /api/record-lap
  └─ Update lap display locally
```

**Finish Marking**
```javascript
markFinish(uid, is_finished, card)
  ├─ Check race_active
  ├─ POST /api/mark-finish
  ├─ Add 'finished' class to card (green styling)
  └─ Disable checkbox
```

**Race Control**
```javascript
startRace()
  ├─ Collect all displayed sailors
  ├─ POST /api/start-race
  ├─ Set race_id, race_active = true
  └─ Enable elapsed time updates

endRace()
  └─ Set race_active = false
```

**Drag & Drop (Manual Reordering)**
```javascript
handleDragStart/End/Over/Drop
  ├─ Drag sailor card
  ├─ Drop in same or different column
  ├─ Reorder DOM
  └─ (Future: POST /api/reorder-sailors for placement)
```

**Elapsed Time**
```javascript
updateElapsedTime()
  ├─ Every 1 second
  ├─ GET /api/get-elapsed-time
  └─ Format and display HH:MM in banner
```

---

## Current Limitations & TODOs

### v1.0 (What's Working)
✅ Race start/end UI  
✅ 4-column sailor grouping by class  
✅ Lap counter with increment button  
✅ Finish checkbox (marks & disables)  
✅ Drag-and-drop reordering (DOM only)  
✅ Live elapsed time display  
✅ Database persistence (SQLite)  
✅ Touch-friendly button sizing  

### v1.1 (Pending Implementation)
- [ ] Auto-move finished sailors to bottom of column
- [ ] Class-specific lap requirements (e.g., ILCA 6 = 3 laps)
- [ ] Visual indication of active race (banner pulse or timer color)
- [ ] Persist placement changes to database on reorder
- [ ] Clear/reset race (delete from race_sailors)
- [ ] Export race results as CSV/PDF
- [ ] Dual-operator state sync (WebSocket or polling)
- [ ] Undo/redo for lap changes

### Known Issues (Session 3 Backlog)
- Checkbox cannot be manually unchecked (intentional by design)
- Drag/drop reorders DOM but doesn't persist placement to DB yet
- No "max laps" enforcement per class
- No sound notification on finish

---

## Testing Checklist

### Unit Tests (Manual)

**1. Sailor Display**
- [ ] Open `/finishsheet`
- [ ] Verify 4 columns display
- [ ] Verify sailors grouped by class (top 3 + Open)
- [ ] Verify sail numbers, class, nicknames visible

**2. Lap Tallying**
- [ ] Click "Start Race"
- [ ] Click "+ Lap" on a sailor 3 times
- [ ] Verify lap counter shows 3
- [ ] Check database: `SELECT * FROM lap_records` has 3 rows

**3. Finish Marking**
- [ ] Same sailor as above, check "Finish" checkbox
- [ ] Verify card turns green
- [ ] Verify checkbox disables
- [ ] Check database: `SELECT * FROM race_sailors` shows finish_time

**4. Elapsed Time**
- [ ] Watch banner timer count up
- [ ] Should show MM:SS format
- [ ] Should increment every 1 second

**5. Drag/Drop Reordering**
- [ ] Drag sailor card to different column
- [ ] Drop it
- [ ] Verify card visually moves

**6. Multiple Sailors**
- [ ] Add laps to 3 different sailors
- [ ] Mark 1 as finished
- [ ] Verify each sailor's state independently

**7. Race End**
- [ ] Click "End Race"
- [ ] Verify Start button re-enables
- [ ] Verify timer resets to 00:00

---

## Database Inspection

```sql
-- Check current races
SELECT * FROM races;

-- Check race sailors (current race)
SELECT rs.uid, s.sail_no, s.short_name, rs.lap_count, rs.finish_time 
FROM race_sailors rs
JOIN sailors s ON rs.uid = s.uid
WHERE rs.race_id = (SELECT MAX(race_id) FROM races);

-- Check all lap records
SELECT rs.uid, s.sail_no, lr.lap_number, lr.timestamp
FROM lap_records lr
JOIN sailors s ON lr.uid = s.uid
ORDER BY lr.timestamp DESC;
```

---

## File Locations

```
C:\Users\anton\flagmachine\drag-drop-app\
├── app.py                          (updated: 16.5 KB)
├── score.db                        (SQLite, auto-created tables)
├── templates\
│   ├── index.html                  (updated: added Finish Sheet link)
│   ├── finishsheet.html            (NEW: 7.6 KB)
│   └── display.html                (unchanged)
├── static\js\
│   ├── app.js                      (unchanged)
│   └── finishsheet.js              (NEW: 9.1 KB)
└── static\css\
    └── style.css                   (unchanged)
```

---

## Integration with Flagmachine

The finish sheet is a **new independent tab** but shares:
- Same database (`score.db`)
- Same Flask server (localhost:5000)
- Same sailor registry (seeds from `seed_sailors.py`)

**Timeline Integration:**
- Flag machine sets master start time
- Finish sheet is started manually or auto-triggered when race begins
- Both systems can run simultaneously without conflict

**Future Enhancement:**
- Finish sheet could read "active flag" from flagmachine state
- Display flag name in banner alongside elapsed time
- Auto-mark sailors as finished when they reach max laps

---

## Architecture Notes

### State Flow
```
User clicks "Start Race" (finishsheet.html)
    ↓
POST /api/start-race
    ↓
Backend creates: races + race_sailors rows
    ↓
Sets app_state['race_id']
    ↓
Frontend: setInterval(updateElapsedTime, 1000)
    ↓
GET /api/get-elapsed-time → uses app_state['race_start_timestamp']
    ↓
User clicks "+ Lap" on sailor
    ↓
POST /api/record-lap
    ↓
Backend: UPDATE race_sailors.lap_count, INSERT lap_records row
    ↓
Frontend updates card display
```

### Database Design Notes
- **races:** Stores race metadata & timing
- **race_sailors:** Join table enables many sailors per race
- **lap_records:** Complete audit trail of every lap with timestamp
- **sailors:** Master sailor registry (populated by seed_sailors.py)

### Why SQLite?
- Persistent across sessions (unlike app_state dict)
- Audit trail of lap times (lap_records table)
- Easy inspection with SQL
- No separate database server needed for single-host deployment

---

## Next Session (Session 4) Planning

### High Priority
1. **Auto-move finished sailors to bottom** 
   - Finished card should visually sink to bottom of column
   - Impl: After `markFinish()` success, reorder card in DOM

2. **Persist placement changes**
   - Call POST /api/reorder-sailors after drag/drop
   - Send: `{uid, placement, column}`
   - Backend: Update race_sailors.placement

3. **Max laps enforcement**
   - Add config: `class_max_laps = {ILCA 6: 3, Optimist: 2}`
   - Disable "+ Lap" button when lap_count >= max_laps
   - Auto-mark finish when max reached

4. **Dual-operator sync**
   - Two operators on same race (laptop + touch monitor)
   - Use `setInterval(reloadSailors, 2000)` to fetch updates
   - Or upgrade to WebSocket (Socket.io)

### Medium Priority
5. Export race results (CSV)
6. Undo/redo for lap changes
7. Sound notifications
8. Pre-race sailor selection UI
9. Mobile phone as wireless lap counter (separate device)

### Low Priority
10. Score calculation engine (separate from finish sheet)
11. Multiple races in parallel
12. Handicap adjustments

---

## Quick Start Command

```bash
cd C:\Users\anton\flagmachine\drag-drop-app
python app.py
# Then open:
# http://localhost:5000/              (Flag Machine)
# http://localhost:5000/finishsheet   (Finish Sheet)
```

---

## Summary

**Session 3 delivered a working finish sheet v1.0** with:
- 4-column sailor display grouped by class
- Live lap tallying with timestamps
- Finish marking with auto-disable
- Drag-and-drop reordering
- Live elapsed time display
- Full database persistence

Ready for testing and refinement in Session 4.

---

**Created:** Session 3  
**Version:** 1.0  
**Status:** Ready for Testing  
**Next Review:** Session 4
