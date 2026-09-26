# Bug & Issue Tracker

## Current Bugs

### 🔴 CRITICAL - Secondary Flag Drop Box Not Functional
- **Ticket:** BUG-002
- **Title:** Cannot drag flag into secondary (+Flag) drop box
- **Status:** UNRESOLVED (Repeating loop condition reached)
- **Severity:** Low (cosmetic feature; doesn't affect race timing)
- **Affected Component:** `createRow()` function, secondary-flag-box event handlers
- **Description:**
  - Primary flag column drag-drop works correctly
  - Secondary flag drop box visible and styled properly
  - dragover event listeners attached and styled
  - Drag-drop event chain not completing to drop handler
- **Reproduction Steps:**
  1. Open control panel
  2. Create an event row with primary flag
  3. Attempt to drag another flag onto the "+Flag" secondary box
  4. Box highlights on dragover, but drop doesn't register
- **Root Cause (Suspected):**
  - Possible event bubbling/capture issue with parent row element
  - Parent row may be intercepting drag events before secondary box
  - Pointer-events chain potentially blocked by parent layout
- **Attempted Fixes:**
  - Added inline `pointer-events: auto` to secondary-flag-box
  - Added `e.stopPropagation()` to dragover/dragleave/drop handlers
  - Added try-catch error handling in drop listener
  - No console errors observed during drag
- **Next Debug Steps:**
  - Isolate secondary box from parent row drag listeners
  - Test with temporary `pointer-events: none` on parent row during hover
  - Verify dataTransfer.getData('card-data') is retrievable in drop context
  - Consider moving secondary box to separate container outside row
- **Related Files:**
  - `static/js/app.js` (createRow function, lines ~90-110)
  - `templates/index.html` (row HTML structure)
  - `static/css/style.css` (row layout flexbox)

---

## Closed/Resolved Issues

### ✅ RESOLVED - Display Timer Shows "1" After All Events Complete
- **Ticket:** BUG-001
- **Title:** Display board timer continues showing minutes after Grid 2 finishes
- **Status:** RESOLVED
- **Fix Applied:** Added `hasAnyActive` tracking in `updateCountdown()`
  - When all rows CLEAR (no ACTIVE or PENDING), sends `live_timer: '0'` to backend
  - Display board now correctly shows 0 and hides flag
- **Commit:** Updated createRow() updateCountdown() function with completion detection
- **Testing:** Verified timer goes to 0 when race finishes

---

## Feature Requests / Future Enhancements

### 🟡 NICE-TO-HAVE - Audio/Visual Alerts
- Beep or flash when rows transition to ACTIVE
- Useful for race officer awareness during back-to-back sequences

### 🟡 NICE-TO-HAVE - Keyboard Shortcuts
- Space = START
- P = PAUSE (STOP)
- R = RESET
- E = END RACE

### 🟡 NICE-TO-HAVE - Countdown Optimization
- Reduce tick rate from 100ms to 200ms to improve CPU efficiency
- No performance impact on user experience at 500ms display board polling

### 🟡 NICE-TO-HAVE - Persistent Storage
- Save race sequences to JSON file or simple database
- Load sequences from template library

### 🟡 NICE-TO-HAVE - Mobile Display Board Support
- Responsive design for tablet/phone outdoor viewing
- Consider WiFi IP-based display instead of localhost

---

## Test Coverage

### Manual Tests Passed ✓
- [x] Drag flag into Grid 1 → row created
- [x] Drag flag into Grid 2 → row added to separate grid
- [x] Reorder rows within same grid
- [x] Edit countdown minutes (min 1 enforced)
- [x] Delete row (remove button)
- [x] START button initiates countdown
- [x] STOP pauses countdown, unlocks UI
- [x] RESET clears all rows back to PENDING
- [x] END RACE marks race as finished
- [x] Display board auto-updates flag when Grid 1 → Grid 2 transition
- [x] Display board shows grid total countdown in whole minutes
- [x] UI locks during RUNNING state (drag disabled, etc.)
- [x] Auto-start trigger when system time ≥ master_start_time

### Manual Tests Failed ❌
- [ ] Drag flag into secondary (+Flag) box → No drop registration

---

## Performance Notes

- **Countdown loop:** 100ms = 10x per second (responsive but CPU-intensive)
- **Display board polling:** 500ms = 2x per second (acceptable for visual refresh)
- **Browser memory:** No detected leaks with long race durations
- **Network:** Low bandwidth usage (small JSON payloads)

---

## Version History

| Date | Version | Status | Notes |
|------|---------|--------|-------|
| Current | 1.0.0 | Stable | Core race engine complete; secondary flags cosmetic |

