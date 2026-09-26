@echo off
REM Session 3 - Finish Sheet Test Build
REM This script validates the implementation and provides next steps

echo.
echo ============================================
echo Session 3: Finish Sheet - Build Complete
echo ============================================
echo.

echo [+] Files created:
echo     - Updated app.py (16.5 KB) with new routes and database schema
echo     - Created templates\finishsheet.html (7.6 KB)
echo     - Created static\js\finishsheet.js (9.1 KB)
echo     - Updated templates\index.html (added Finish Sheet link)
echo.

echo [+] New Backend Endpoints:
echo     GET  /finishsheet                    - Render finish sheet UI
echo     POST /api/start-race                 - Start new race with selected sailors
echo     GET  /api/sailors-for-onwater       - Get sailors grouped by class (4 columns)
echo     POST /api/record-lap                 - Increment lap counter
echo     POST /api/mark-finish                - Record sailor finish time
echo     POST /api/reorder-sailors            - Update manual ranking
echo     GET  /api/get-elapsed-time           - Get race elapsed time
echo.

echo [+] Database Tables Created:
echo     - races (race_id, start_time, status, class_groups)
echo     - sailors (uid, sailor_name, short_name, sail_no, boat_class, handicap, seed)
echo     - race_sailors (race_id, uid, lap_count, finish_time, placement)
echo     - lap_records (race_id, uid, lap_number, timestamp)
echo.

echo [+] Frontend Features:
echo     - 4-column layout (grouped by class, top 3 + Open)
echo     - Touch-friendly buttons (14 inch monitor optimized)
echo     - Lap counter with + button (click to increment)
echo     - Finish checkbox (marks boat as finished, disables checkbox)
echo     - Drag-and-drop reordering (manual ranking)
echo     - Live elapsed time banner
echo     - Boat status: Active / Finished (color change)
echo.

echo ============================================
echo NEXT STEPS - Session 3 Testing:
echo ============================================
echo.

echo 1. START THE SERVER:
echo    From C:\Users\anton\flagmachine\drag-drop-app\
echo    Run: python app.py
echo.

echo 2. OPEN BROWSER TABS:
echo    - Flag Machine (existing): http://localhost:5000/
echo    - Finish Sheet (new):       http://localhost:5000/finishsheet
echo.

echo 3. TEST WORKFLOW:
echo    a) Click "Start Race" button
echo    b) Select a sailor and click "+ Lap" multiple times
echo    c) Check "Finish" checkbox to mark boat as finished
echo    d) Drag sailor cards to reorder manually
echo    e) Watch elapsed time update in banner
echo.

echo 4. VALIDATION CHECKLIST:
echo    [ ] Sailors display in 4 columns grouped by class
echo    [ ] Lap counter increments on button click
echo    [ ] Finish checkbox toggles and disables
echo    [ ] Completed sailors move to bottom and change color
echo    [ ] Drag-and-drop reordering works
echo    [ ] Elapsed time updates every second
echo    [ ] Database records lap_records and finish_time
echo.

echo 5. KNOWN ITEMS TO REVIEW:
echo    - Max laps per class (not implemented yet - add config)
echo    - Auto-move finished sailors to bottom (currently manual drag)
echo    - Placement calculation logic
echo    - Integration with flagmachine timers (banner shows elapsed only)
echo.

echo ============================================
echo Files Summary:
echo ============================================
echo.
echo app.py
echo  ├─ init_finishsheet_tables() - Database schema
echo  ├─ /finishsheet - Main route
echo  ├─ /api/start-race - Begin race with sailors
echo  ├─ /api/sailors-for-onwater - Load sailors by class
echo  ├─ /api/record-lap - Increment lap
echo  ├─ /api/mark-finish - Record finish time
echo  ├─ /api/reorder-sailors - Update placement
echo  └─ /api/get-elapsed-time - Race elapsed time
echo.
echo templates/finishsheet.html
echo  ├─ Top banner (elapsed time, start/end buttons)
echo  ├─ 4-column grid layout
echo  └─ Sailor cards (sail #, class, name, lap counter, finish checkbox)
echo.
echo static/js/finishsheet.js
echo  ├─ initFinishSheet() - Setup on page load
echo  ├─ loadAndRenderSailors() - Fetch and display
echo  ├─ recordLap() - API call for lap increment
echo  ├─ markFinish() - API call for finish time
echo  ├─ Drag/drop handlers - Manual reordering
echo  └─ updateElapsedTime() - Live timer
echo.

echo.
echo Ready for testing! Press any key to exit.
pause >nul
