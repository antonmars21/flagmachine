# Session Work Summary & Self-Help Notes

## What We Accomplished This Session

### 1. Core Drag-Drop System ✓
- **Created fresh app.js** from scratch with proper event handling
- **Library card drag-drop:** Drag flags from sidebar into Event Grid 1 or Grid 2 → creates new row
- **Row reordering:** Drag rows within same grid to change sequence order
- **Drop zone visual feedback:** Highlight zones on hover, reset on leave

### 2. Countdown Engine ✓
- **100ms tick loop:** `updateCountdown()` runs every 100ms
- **Cumulative timing:** Each row calculates based on sum of previous row durations
- **State machine:** PENDING → ACTIVE → CLEAR based on elapsed time
- **Grid totals:** Sums all ACTIVE + PENDING rows, sends to display board
- **Dual start trigger:** Manual button + auto-trigger when system time ≥ master_start_time

### 3. Backend Integration ✓
- **Flask API routes:** `/update-sequence`, `/update-settings`, `/execute-control`, `/api/display-state`
- **State sync:** Sequence synced after every drag-drop or reorder
- **Timer sync:** Whole-minute countdown sent to display board every 100ms

### 4. Display Board ✓
- **Simplified design:** Flag image + large countdown (whole minutes only)
- **Toggle button:** Hide/show countdown for privacy
- **Polling:** Every 500ms fetches active flag + timer from backend
- **Completion logic:** When timer reaches 0, flag disappears and shows "GO"

### 5. UI Locking During Race ✓
- **RUNNING state:** Grays out drag handles, disables removes, blocks new rows
- **READY/PAUSED:** Re-enables all editing

---

## Known Bug (Unresolved)

### 🔴 Secondary Flag Box Drop Not Working
- **Issue:** Cannot drag flag into "+Flag" secondary drop box
- **Evidence:** 
  - Primary flag drop works fine
  - Secondary box has correct CSS (display: flex, pointer-events: auto in inline style)
  - dragover/drop event listeners attached in createRow()
- **Last attempt:** Added `pointer-events: auto` inline style + `e.stopPropagation()` to prevent bubbling
- **Status:** Repeating loop condition reached — moved to backlog

---

## Lessons Learned & Debugging Tips

### 1. Drag-Drop Event Flow
- **dragstart:** Set dataTransfer ONLY on the DRAGGED element (library card)
- **dragover:** MUST call `e.preventDefault()` to enable drop
- **drop:** MUST call `e.preventDefault()` + `e.stopPropagation()` to stop bubbling
- **dragleave:** Check `e.target === this` to avoid triggering on child elements

### 2. Pointer Events & Nested Elements
- **Issue:** Child elements inside flexbox can intercept drag events if `pointer-events` not set
- **Fix:** Ensure drop target has `pointer-events: auto` or no parent has `pointer-events: none`
- **Note:** The secondary flag box has proper pointer-events, so issue likely elsewhere (possibly parent row interference)

### 3. State Syncing Pattern
- Frontend updates `app_state` immediately (optimistic)
- Then POST to server endpoint
- Server stores in `app_state` dict
- Display board polls `/api/display-state` to get current active row + timer

### 4. Countdown Calculation
```javascript
// Cumulative timing:
Row 1: start=0, end=5*60 (300s)
Row 2: start=300, end=600
Row 3: start=600, end=660

// Status per elapsed time:
if (elapsed < row.start) status = PENDING
else if (elapsed < row.end) status = ACTIVE
else status = CLEAR

// Grid total:
sum of all (ACTIVE or PENDING rows' remaining_seconds)
then divide by 60 and round UP for display
```

### 5. Flask Backend Patterns
- Use `request.get_json()` for POST body
- Store state in module-level dict (app_state)
- Return JSON with `jsonify()`
- No database — session-only persistence

### 6. Master Start Time vs Manual Start
- Both are valid entry points
- System checks every 1 second: `if current_time >= master_start_time: triggerRaceStart()`
- Manual button directly calls `triggerRaceStart()`
- First to execute wins (no conflict logic needed)

---

## For Next Time: Quick Debug Checklist

If secondary flag drop still doesn't work:

1. **Check browser console (F12):** Look for JavaScript errors during drag
2. **Verify dragstart on library card:** 
   - Does dragstart fire when dragging library card? (Should see in console)
   - Does `dataTransfer.setData('card-data', ...)` work?
3. **Verify dragover on secondary box:**
   - Add `console.log('dragover')` in dragover handler
   - Does it fire when hovering over +Flag box?
4. **Check pointer-events inheritance:**
   - Run in console: `document.querySelector('.secondary-flag-box').style.pointerEvents`
   - Should output: "auto"
5. **Event bubbling:**
   - Try adding `e.stopPropagation()` in dragover AND dragleave
   - Parent row might be stealing events
6. **Alternative fix:** Disable row's dragstart/dragover to isolate secondary box:
   ```javascript
   row.addEventListener('dragstart', e => { e.stopPropagation(); return false; });
   row.addEventListener('dragover', e => { e.stopPropagation(); return false; });
   ```

---

## File Locations Reference

```
C:\Users\anton\flagmachine\drag-drop-app\
├── app.py                          # Flask backend
├── static/
│   ├── js/
│   │   └── app.js                 # Main countdown + drag-drop engine
│   ├── css/
│   │   └── style.css              # 4-column layout styling
│   └── flags/                      # PNG flag images
└── templates/
    ├── index.html                 # Control panel UI
    ├── display.html               # Outdoor display board
```

---

## Next Session Action Items

1. ⚠️ **Debug secondary flag drop** (see checklist above)
2. Test entire race flow end-to-end
3. Verify display board receives flag + countdown correctly
4. Test auto-start trigger with system clock
5. Consider: refresh rate optimization (200ms instead of 100ms for efficiency)
