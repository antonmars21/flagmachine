# System State Reference — Session 4 Final

**Last Updated**: Session 4 Complete  
**Status**: Finish Sheet v1.1 API + Database Functional, Browser Testing Pending

---

## QUICK REFERENCE

### Running System
```
URL (Flag Machine):      http://localhost:5000/
URL (Finish Sheet):      http://localhost:5000/finishsheet
Backend:                 app.py (Flask, port 5000, debug=True)
Database:                score.db (SQLite, merged schema)
```

### Sailors
- **Total**: 27
- **Classes**: Ilca 6 (14), Starling (4), Optimist (3), Ilca 7 (2), P (1), Zephyr (3)
- **Distribution in UI**: Col 1 (14), Col 2 (4), Col 3 (3), Col 4 (6)

### Database Tables
```
sailors          (uid, sail_no, short_name, boat_class, seed, ... + legacy cols)
races            (race_id, status, created_at)
race_sailors     (id, race_id, uid, lap_count, finish_time, placement)
lap_records      (id, race_id, uid, lap_number, timestamp)
```

### API Endpoints (Finish Sheet)
```
GET  /finishsheet                    → HTML page
GET  /api/sailors-for-onwater        → {status, columns, class_groups}
POST /api/start-race                 → {status, race_id}
POST /api/record-lap                 → {status, lap_count}
POST /api/mark-finish                → {status, finish_time}
GET  /api/get-elapsed-time           → {status, elapsed_seconds, formatted}
```

---

## VERIFIED FUNCTIONALITY (Session 4 ✓)

| Feature | Test Result | Notes |
|---------|------------|-------|
| `/finishsheet` page loads | PASS | HTML renders, banner + buttons visible |
| 27 sailors load | PASS | Grouped in 4 columns, classes correct |
| Sailor card display | PASS | sail_no, short_name, boat_class shown |
| `/api/start-race` | PASS | Creates race_id, adds sailors to race_sailors |
| `/api/record-lap` | PASS | Increments lap_count, timestamps lap_records |
| `/api/mark-finish` | PASS | Sets finish_time in race_sailors |
| `/api/get-elapsed-time` | PASS | Returns MM:SS formatted time |
| Database schema | PASS | All 5 tables present, data integrity OK |
| Sailor normalization | PASS | boat_class names consistent across DB |

---

## NOT YET TESTED (Browser / Interactive)

| Feature | Status | Blocker? |
|---------|--------|----------|
| Browser grid rendering | TODO | No (API works) |
| Button interactions | TODO | No (API works) |
| Checkbox state + visual | TODO | No (API works) |
| Drag-drop reordering | TODO | No (future feature) |
| Elapsed time polling | TODO | No (API works) |

---

## SESSION 5 PRIORITIES

### Must-Do
1. **Link countdown to Finish Sheet** — Flag Machine START → auto-start race
2. **Sailor registry UI** — Pre-race selection (checkbox, register button)
3. **Boat class mapping table** — Eliminate typo risk

### Should-Do
1. Browser testing (verify layout, interactions)
2. Error handling (network failures, race state errors)

### Nice-To-Do
1. WebSocket sync (instead of HTTP polling)
2. CSV export
3. Mobile optimization

---

## KEY FILES

| File | Role | Status |
|------|------|--------|
| `app.py` | Main Flask app | ✓ Working |
| `score.db` | SQLite database | ✓ Data OK |
| `templates/finishsheet.html` | UI template | ✓ Loads |
| `static/js/finishsheet.js` | Client logic | ✓ Loads (not tested in browser) |
| `AgentReadme/Architecture.md` | Documentation | ✓ Updated |
| `AgentReadme/Requirements.md` | v1.1 Spec | ✓ Updated |
| `AgentReadme/SESSION5_PLAN.md` | Next session | ✓ Created |
| `AgentReadme/SESSION4_SUMMARY.md` | This session | ✓ Created |

---

## GOTCHAS & NOTES

### For Session 5 Developer
1. **app_state dict**: Shared between Flag Machine + Finish Sheet (both read/write)
   - `app_state['status']` = 'READY' | 'RUNNING' | 'PAUSED' | 'ENDED'
   - `app_state['race_id']` = current race ID (or None)
   - `app_state['race_start_timestamp']` = ISO format time string

2. **Database schema merge**: Session 2 legacy columns still exist (racing_today, status, finish_order, finish_time) but NOT used by Finish Sheet
   - Safe to keep for backward compat
   - Finish Sheet uses race_sailors table instead

3. **Port 5000 cleanup**: Old Flask processes may linger
   - Use `netstat -ano | findstr ":5000"` to find
   - Kill with `taskkill /PID <PID> /F`

4. **Column keys are strings in JSON**: Python dicts convert to JSON strings
   - API returns: `{"1": [...], "2": [...], "3": [...], "4": [...]}`
   - finishsheet.js handles both int and string lookups

5. **Race-status polling**: finishsheet.js will need to poll `/api/race-status` (doesn't exist yet)
   - This endpoint should return Flag Machine status
   - Finish Sheet auto-detects READY → RUNNING transition

---

## QUICK START (Developer Onboarding)

### 1. Check Database
```bash
cd C:\Users\anton\flagmachine\drag-drop-app
python
>>> import sqlite3
>>> conn = sqlite3.connect('score.db')
>>> tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
>>> print(tables)
# Should show: sailors, races, race_sailors, lap_records, sqlite_sequence
```

### 2. Start Flask
```bash
cd C:\Users\anton\flagmachine\drag-drop-app
C:\Users\anton\miniconda3\python.exe app.py
# Should see: "Running on http://localhost:5000"
```

### 3. Test API
```bash
curl http://localhost:5000/api/sailors-for-onwater
# Should return JSON with 27 sailors in 4 columns
```

### 4. Open Browser
```
http://localhost:5000/finishsheet
# Should show page with banner, buttons, (grid will be empty until race starts)
```

---

## DEPLOYMENTS CHECKLIST

- [x] Code compiles (no syntax errors)
- [x] Database loads (27 sailors, normalized names)
- [x] API responds (6 endpoints tested)
- [x] Documentation current (Architecture.md, Requirements.md updated)
- [ ] Browser tested (not yet)
- [ ] Interactive tested (not yet)
- [ ] End-to-end tested (not yet)
- [ ] Production ready (pending Session 5)

---

**For questions or issues, see:**
- `Architecture.md` — System design
- `Requirements.md` — Feature spec
- `SESSION4_SUMMARY.md` — What was done
- `SESSION5_PLAN.md` — What's next

