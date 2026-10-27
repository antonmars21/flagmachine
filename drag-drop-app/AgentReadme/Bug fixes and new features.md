***Bug fixes and new features

**PROCESS RULE (agreed 2026-10-15): a bug only moves to resolved after a confirmed HUMAN browser
test. Passing regression scripts alone is not enough.

**Bugs




=============================
in progress

Bugs to fix:

 26 there need to be more space to drage and drop flags into the startevent box, ad a few spaces for additional flags

 27 3rd race Sat 24 Oct 26 (race 67) has NO results - server restarted mid-race == CODED 2026-10-27, awaiting human test
Evidence from score.db (backup taken: score.db.backup-20261027):
- race 67 started via flag machine 16:02-16:08 (3 start events), 7 sailors
  recorded lap 1 at 16:20-16:21, then nothing. No finishes. status still
  RUNNING - never ended.
- race 68 created 16:59:30 by the finish-sheet Start Race (manual_backup,
  all classes started at one instant) WHILE 67 was still running; 3 lap
  records logged 2s later (machine-speed, not scorer clicks); ended 17:12
  with no finishes.
- races 65 + 66 (races 1 and 2 that day) are healthy: 12 finishes each.
Root cause: race state (app_state: race_id, class_start_times,
open_start_time) is MEMORY-ONLY. After a mid-race Flask restart nothing
recovers the DB's RUNNING race: /api/start-race then auto-creates a NEW
race (duplicate), /api/end-race ends only the in-memory one, so the real
race is orphaned RUNNING with its laps but no results.
Fix (app.py recover_running_race(), runs at app start only - never at
import, so regression scripts are unaffected): a RUNNING race with
activity in the last 12h is ADOPTED back into app_state (end-race, laps,
CSV export all target the live race); older RUNNING races are abandoned
crash orphans and are closed ENDED at their last activity time. Next
START.bat will auto-close the current orphans (races 60 + 67).
Regression: scripts/test_race_recovery.py (adopt recent + close stale +
end-race on recovered race + reset unblocked + no-op when clean) PASS.
Human test: mid-race, restart Flask (restart_flask.bat) - the finish
sheet must keep scoring the SAME race (no new race id), End Race ends it;
a stale RUNNING race older than 12h must come up ENDED after a restart.

 28 open-category lap counter resets to 0 on every poll/refresh == FIXED
PASSED ✅ HUMAN TEST 2026-10-27 (Anton: "lap counter is working in the current test")
Seen 24 Oct by the scorer (Gabrielle Marais, Europe - no class flag, so
Open Category): the on-sheet lap counter lagged by one (lap 1 showed 0,
lap 2 showed 1), a browser refresh jumped it back to 0, and the scorer
re-clicked - recording duplicate laps 2s/2min apart in races 65 + 66
(14:23:21 after 14:21:29; 15:45:21 after 15:45:14). The Dell sheet showed
clean lap times (14:21:48 / 14:42:19), so the Windows sheet was the broken
one. Root cause: /api/sailors-for-onwater serves open-category sailors
ONLY from the live-rows query, which hardcoded '0 as lap_count' (the
started-classes query filters on s.class_id, which is NULL for open
sailors) - so every poll, sheet re-render and browser refresh reset the
displayed count even though race_sailors had the true count. Fix: live
rows now LEFT JOIN race_sailors and carry the real lap_count/finish_time
(late sign-ons before their first lap still show 0, which is correct).
Regression: scripts/test_open_lap_counts.py (lap 1 + lap 2 through the
state endpoint, finish_time, class sailors unaffected, no stale leak
after reset) PASS. Human test: sign on a sailor with no class flag, start
the race, record laps - the count must survive polls, the other
station's re-renders and a browser refresh (Ctrl+F5 first - JS is cached).
DATA REPAIR 2026-10-27 (with backup score.db.backup-20261027): the two
bogus duplicate lap records were removed from the live score.db (race 65
lap at 14:23:21, race 66 lap at 15:45:21) and Gabrielle's lap_count in
both races set to 1 (her real 2nd laps were never captured on the Windows
machine - the Dell CSVs carry them: 14:42:19 in race 59, 15:45:33 in
race 60 Dell ids).

 30 station buttons + Race Officer button open NEW browser tabs/sessions == CODED 2026-10-27, awaiting human test
RO report 2026-10-27 (was NOT previously logged in this tracker - recorded
here now): the Finish Sheet 1 / Finish Sheet 2 buttons on the RO control
page opened a NEW browser tab on every click, and going back via the Race
Officer Control button landed in new blank sessions - multiple finish
sheet sessions then fought over lap/finish captures (the station id lives
per tab in sessionStorage, so each new tab is a fresh, blank session).
Fix (templates/index.html): the station buttons no longer carry
target="_blank" - they navigate THIS tab to /finishsheet?station=1|2. The
finish sheets' 'Race Officer Control' button already navigated the same
tab; now the round trip RO <-> stations stays in ONE tab per screen with
no duplicate sessions. The Display Board link keeps its new-tab behaviour
BY DESIGN (it runs on the separate outdoor screen - it is not navigation
between work pages).
Regression: scripts/test_navigation.py (station buttons same-tab on /,
RO control same-tab on both finish sheets, display board has no work-page
links, no stray target="_blank" anywhere else) PASS.
Human test (Ctrl+F5 the RO page first - the HTML is cached): click
Finish Sheet 1, then Race Officer Control, then Finish Sheet 2 - the
whole round trip must happen in the SAME tab with no new tabs opening.

 29 Dell exports: no series name + filename not series/date == CODED 2026-10-27, awaiting human test
The 24 Oct Dell CSVs came out as race_59/60/61_results.csv with an EMPTY
Series column, while the same calendar matched fine on the Windows test
machine (24 Oct = 'Points Races club sailing'). Root cause: the Dell has
no HYC Calendar xlsx in its Sailwave folder, and the export silently fell
back. Fix: the calendar now SHIPS WITH THE APP (drag-drop-app/HYC
Calendar 2026-2027.xlsx) and find_calendar_file() falls back to the app
folder when the Sailwave folder has no calendar - so every machine
running a current checkout names exports correctly. Also fixed while
here: on multi-race days the series+date filename collided (the three
Saturday races would overwrite each other) - races after the first of
the day now append their race-of-day number (R2, R3...).
Regression: scripts/test_export_naming.py (series+date filename, R2/R3
suffix, empty-Series fallback, app-folder calendar fallback) PASS;
test_export_csv + test_export_sailwave + test_calendar still PASS.
SERIES RACE NUMBERING (RO request 2026-10-27): Sailwave needs the race
number WITHIN the series, incremental across the whole season (Twilight
Series runs R1, R2, R3... every Wednesday over the weeks), not per day
and not the DB race id. The Race column now carries that number: every
started race whose date maps to the same calendar series counts, ordered
by earliest recorded start (races with no calendar series fall back to
the race-of-day number). The filename R-suffix uses the same number, so
same-day races still cannot overwrite each other. The calendar lookup was
refactored to one xlsx parse per export (date -> event map) so numbering
every race stays cheap. Regression: test_export_naming.py now also checks
R1..R4 numbering across two weeks of the same series.
24 Oct results regenerated with correct names and race numbers (races
1-2 from the Windows score.db, race 3 from the Dell db - the only
complete record): Sailing Results 24-10-26/Points Races club sailing
24-10-2026.csv (Race 1), ... R2 24-10-2026.csv (Race 2), ...
R3 24-10-2026.csv (Race 3) (new utility: scripts/export_race_by_id.py
re-exports any recorded race from any score.db copy - feature 5
groundwork).
Human test: after a race, Export CSV must download as
'<series> <date>.csv' (R2/R3 for later races of the series) with the
Series column filled and the Race column showing the series race number
(R1 on a series' first race, R2 on the second Twilight Wednesday, ...).

=============================
To Test 

HOTFIX 2026-10-22 flag drag-and-drop broken on the RO page == FIXED
PASSED ✅ HUMAN TEST 2026-10-23 (Anton: "the flag drop works"):
- Root cause: the bug-25 voice edit left a DUPLICATE 'const audioCues'
  declaration in app.js (the original at line 65 + a second one in the new
  cue section). A duplicate const is a fatal JS SyntaxError - the WHOLE
  app.js failed to parse, so nothing on the RO page ran (no drag and drop,
  no buttons). Server/app.py was never affected (compiles + all pages
  render 200).
- Fix: duplicate declaration removed; both app.js and finishsheet.js now
  verified with a real JS PARSE check (new Function) - both PARSE OK.
  Last-known-good app.py backup kept at tempref/app_py_HEAD_11f56bd.py.
- Full suite (13 scripts) passes; /, both finish sheets and /display
  render 200. Browser test: Ctrl+F5 the RO page, drag a flag into a start
  event - it must drop in and show as a row.

BUG 4 end-race + start-button sync == CODED 2026-10-22/23
PASSED ✅ HUMAN TEST 2026-10-23 (Anton: "ok, those are fixed now")
(Ctrl+F5 all pages first - JS is cached):
- End Race is ONE shared control now. The finish sheet End Race buttons send
  the SAME two calls the RO page uses (/execute-control END_RACE +
  /api/end-race), so they stop the flag machine countdown even before the
  first class flag has fired (no race record yet), and the race status goes
  RUNNING -> ENDED everywhere (races.status ENDED in the DB).
- The RO page now polls /api/race-status every 0.5s: when the race is ended
  from ANY page (RO control, finish sheet 1 or 2) the RO countdown stops,
  all sub-timers freeze, STATE badge shows ENDED. A Reset (fm_status READY)
  shows STATE: READY again.
- Part B: /api/race-status now carries fm_status (RO control state). While
  the RO Start is running the countdown, the Start Race buttons on BOTH
  finish sheets are locked out (all start buttons obey the RO control start
  button). They re-enable only after Reset/Reset Finish Sheet. END_RACE
  also locks them out until a reset.
- Elapsed/duration clocks already freeze at race end (server-side) - unchanged.
Regression: scripts/test_button_sync.py (8 checks) + full suite (13 scripts) +
15-step recorded-session replay all pass.
REGRESSION FIXED 2026-10-23 (buttons looked unsynched in the browser): the
finish-sheet Start Race (manual backup) started a race WITHOUT setting the
shared control state - fm_status stayed READY, so the RO page showed
STATE: READY while a live race was running and the pages disagreed.
Fixes: (1) /api/start-race now sets fm_status RUNNING (a race is running no
matter which page started it); (2) the RO page poller MIRRORS the shared
state onto its badge - RUNNING (flag machine OR any active race, covers
old sessions), ENDED, PAUSED, READY; (3) finish-sheet Start Race stays
locked out while the flag machine is PAUSED too (mid-sequence Stop).
Verified with a JS simulation of BOTH real files through the full cycle
(READY -> RO Start -> Pause -> race active -> End from a finish sheet ->
Reset -> manual-backup Start) - all button states and the RO badge match
on all three pages in every step.
Human test (Ctrl+F5 ALL pages first - JS is cached):
1. press Start Race on a finish sheet -> RO page shows STATE: RUNNING.
2. press End Race on ANY page -> RO countdown stops (if running), all
   pages show STATE: ENDED, lap/finish inputs disabled everywhere.
3. press Reset on the RO page -> all pages back to READY, Start Race
   re-enabled on the finish sheets.
4. while the RO countdown runs, the finish-sheet Start Race is greyed.

BUG 15 elapsed time per class == CODED 2026-10-22, awaiting human test per process rule:
- Every class column header on BOTH finish sheets now shows its own elapsed
  clock ('Elapsed: mm:ss'), ticking up from THAT class's start time (the
  Open Category column runs from the open start). Freezes at the race end
  timestamp when the race ends - so the RO can see when the max allowed
  race time per class is approaching.
- No backend changes needed: the poller already receives class_start_times;
  /api/race-status now also returns open_start_time.
AMENDED 2026-10-22 after RO feedback (tidy): header is now ONE row - class
name left, elapsed mm:ss right (NO 'Elapsed:' label, sailor count REMOVED,
station toggle kept clear of it). Sailor cards are single-line compact rows
(short name + sail number only, boat class row dropped) to maximise space
for the sailor lists. Lap-time formats checked: toast is fixed 24h
HH:MM:SS (toLocaleTimeString could render AM/PM on some Windows locales);
the detailed CSV Lap Times column is now HH:MM:SS instead of raw ISO
microseconds.
AMENDED 2026-10-22 (2nd RO feedback): NO individual per-sailor time display
on the card - no room on screen. Each sailor's own timing stays RECORDED
(lap timestamps from the first lap onward - DB + both CSV exports), it is
just not shown on the card.
Human test: after each class start, its column header clock starts ticking;
end the race -> all clocks freeze; cards stay single-line name + sail
number; lap times still appear in the CSV exports.

BUG 25 voice-over countdown == CODED 2026-10-22/23
PASSED ✅ HUMAN TEST 2026-10-23 (Anton session wrap-up: "ok, those are fixed now";
the full sequence was heard working after the preset fix)
(Sound On, laptop speakers):
- The voice now follows the TOTAL time of the start event (the grid's Total
  Countdown), not each sub-timer: when the event starts it reads out the
  FIRST flag of the sequence plus the total time ('First flag: Ilca 6.
  Three minutes.'), then every whole minute, then 15 seconds, 10 seconds,
  and the last 5 seconds (5, 4, 3, 2, 1). Flag-down horn per flag unchanged.
- The old 30/20-second warnings are replaced by the 15-second call.
AMENDED 2026-10-22 after RO feedback (tidy): the opening announcement is
just the flag name - 'Starling. Three minutes.' (no 'First flag:' prefix).
AMENDED 2026-10-22 (2nd RO feedback - per-flag cues): the countdown cues now
run for EVERY flag change, not just the event total: each flag's own
sub-timer announces its whole minutes, 15 seconds, 10 seconds and the last
5 seconds (5, 4, 3, 2, 1) - the flag officer needs these beats to raise the
next flag and drop the last one. Horn at flag-down unchanged.
AMENDED 2026-10-22 (3rd RO feedback + RO diagram - final wording): every
time a flag is RAISED the voice reads THE FLAG NAME (the row's card label)
plus the TIME REMAINING IN THE START EVENT at that moment. A 3x1min event
says: 'Ilca 6. Three minutes.' (t=0) -> 'P. Two minutes.' (t=1:00) ->
'Ilca 6. One minute.' (t=2:00). Between raises, each flag's own sub-timer
calls its whole minutes (the raise's coinciding minute call is suppressed
so it doesn't talk over the announcement), then 'Fifteen seconds',
'Ten seconds' and the last 5 seconds, then the horn at flag-down.
Example (RO's Start 2: Pclass 3 min + Pclass 1 min = 4 min total):
'Pclass. Four minutes.' -> 'Two minutes.' -> 'One minute.' -> 15/10/5-4-3-2-1
-> horn -> 'Pclass. One minute.' -> 15/10/5-4-3-2-1 -> horn = P Class START.
REGRESSION FIXED 2026-10-22 (announcements stopped): the RO Start button
preset the first row's status to ACTIVE, so the countdown tick never saw
the PENDING -> ACTIVE transition that triggers the flag-change
announcement - the opening '<flag>. <total time>' never spoke. Fix: the
preset removed (the tick flips the row within 100ms anyway). Verified with
a JS simulation running the REAL app.js against the RO diagram sequence:
'Ilca 6. Three minutes.' / 15 / 10 / 5-4-3-2-1 / horn / 'P. Two minutes.' /
15 / 10 / 5-4-3-2-1 / horn / 'Ilca 6. One minute.' / 15 / 10 / 5-4-3-2-1 /
horn = START, class-start POST carries all the event's flags.
Human test: build a multi-flag start event (e.g. 3 rows of 1 min), press
Start with Sound On and listen for the full sequence above.

FEATURE 6 Sailwave results by regatta name + matched date == CODED 2026-10-22,
awaiting human test per process rule:
- New calendar lookup in app.py reads the HYC Calendar xlsx
  (C:\Users\Public\Documents\Sailwave\Flagmachine_database\HYC Calendar 2026-2027.xlsx)
  with a stdlib xlsx reader (no new pip dependency).
  Wednesday rule honoured: only the Twilight race (from 6pm) is matched,
  never the earlier training/coaching session (latest start time wins,
  coaching/learn-to-sail/committee rows are excluded).
- Check it in the browser: http://localhost:5000/api/race-calendar-event
  (or ?date=YYYY-MM-DD) returns the matched regatta/series name.
- The Export CSV filename is now named by regatta + matched date, e.g.
  'Twilight Series club racing 21-10-2026.csv'; without a calendar match
  it falls back to race_<id>_results.csv.
Regression: scripts/test_calendar.py (fixture + the REAL calendar file:
21 Oct 26 -> Twilight Series club racing, 17 Oct 26 -> A Series (1,2,3),
12 Dec 26 -> HYC XMAS REGATTS & DINNER).

FEATURE 7 export CSV for direct Sailwave import == CODED 2026-10-22/23
PASSED ✅ HUMAN TEST 2026-10-23 (Anton: "redone csv file passed human test"):
- The Export CSV button now produces a direct-Sailwave-import CSV: columns
  Fleet, Class, SailNo, HelmName, Handicap, SERIES, Race, StartTime,
  FinishTime, Elapsed, Laps, LapTimes - the field names follow the club's own
  Sailwave export conventions (Boats_master.htm). HelmName is the FULL
  sailor name, Elapsed is mm:ss.s (finish - class start). Unfinished sailors
  export with empty FinishTime/Elapsed so the scorer can code them DNC/DNF.
- AMENDED 2026-10-23 (RO, pre-Sailwave-sync): dedicated SERIES column carries
  the calendar-matched series/regatta name (blank when the race date has no
  calendar event); Race is the stable race identifier ('Race <id>');
  LapTimes column carries every recorded lap as a 24h HH:MM:SS clock
  ('22:50:44; 22:55:12'). The detailed layout gained the Series column too
  (first column).
- The legacy human-readable layout is still available at
  /api/export-race-csv?format=detailed.
Regression: scripts/test_export_sailwave.py (now checks Series, race id and
lap times) + existing test_export_csv.py + test_open_flag.py (updated for
the new layout) pass.
Human test: run a race, press Export CSV, then File > Import in Sailwave.

IMPORT SAILWAVE SAILORS - (in testingboat_master.htm source == CODED 2026-10-16, awaiting human test
per process rule (Ctrl+F5 all pages):
- The button is now IDENTICAL on all pages: purple 'Import Sailwave sailors' (RO header +
  both finish sheet banners), same handler, same wording (busy text 'Importing...', success
  'Sailwave sailors imported successfully!').
- SOURCE CHANGE: the import now reads the Sailwave boat_master.htm HTML competitor list
  (table: Fleet, Class, Boat, SailNo, HelmName, Handicap) - preferred over Boats_Master.xml,
  which stays as a fallback. Order: Sailwave folder Boats_master.htm -> tempref/boat_master.htm
  -> Boats_Master.xml variants. New parser parse_sailwave_htm() in scripts/import_sailwave.py
  produces the same boat shape as the XML parser, so UID/short_name/class/handicap mapping
  is unchanged; import_sailwave_data dispatches by file extension.
- MOJIBAKE FIXED (2nd find): app.js + finishsheet.js busy text and success alert contained
  double-backslash escape TEXT (rendered as garbage on screen); now the real icons/newlines.
Regression: scripts/test_import_htm.py (parse 55 competitors + spot checks + scratch-DB
import + source preference) + full suite (10 scripts) pass.
Human test: restart, click Import Sailwave sailors on the RO page, expect the import alert
with the new wording and no garbage text; repeat on a finish sheet.


======================
bug backlog


4 end race / start button sync == PASSED ✅ HUMAN TEST 2026-10-23 -> see To Test section
15 elapsed time per class == CODED 2026-10-22, awaiting explicit human confirmation -> see To Test section

 24 If a sailor is added to the race After their class has started, record the time added to the race
 25 voice-over total start event countdown == PASSED ✅ HUMAN TEST 2026-10-23 -> see To Test section
==================
resolved
PASSED ✅ HUMAN TEST 2026-10-16 (Anton: "good all working as expected").
Feature 4 multi-station finish sheet - delivered this session: = implementedeted ✅
Feature 4 Step 1 - multi-station class split == CODED 2026-10-16, = implementedeted ✅ awaiting human test per
process rule (Ctrl+F5 both finish sheet screens first - JS is cached):
- /finishsheet?station=1 or ?station=2 - URL is authoritative, remembered per tab
  (sessionStorage), shown as a badge in the banner; plain /finishsheet defaults to station 1.
- Server-truth assignments in new table class_station_assignments, KEPT FOR THE WHOLE DAY
  (survive races, end-race, reset-finish-sheet, server restart).
- Default split: the FIRST 3 columns on the sheet go to station 1, the remainder (incl.
  Open Category - it behaves like any other class) to station 2; new classes added later
  default by position without disturbing stored toggles.
- Each class column header has a toggle button (2 / 1) that moves the class to the other
  station; the other screen re-renders within ~0.5s (assignments_version in race-status).
- Each station shows ONLY its own columns (4 classes per station is guidance, not enforced).
- POST /api/assign-class-station {class_key, station}; GET /api/sailors-for-onwater?station=N
  filters columns and returns assignments for all columns; no param = all columns (legacy).
Regression: scripts/test_stations.py (7 checks pass: defaults, filtering, toggle, upsert,
new-class default, persistence across race cycle, validation) + existing suite unchanged.
HUMAN TEST 2026-10-16: LAYOUT PASSED (badges, split, toggle all work; timers not run).
AMENDED same day after RO feedback: sailor card is now TWO lines - sailor name + the
COMPLETE sail number (larger, never truncated) on the top row, boat class in a smaller
row under the name; column scrollbars are now LIGHT coloured (clearly visible slider);
'1 sailors' fixed to '1 sailor'. NOTE: the station badge/toggle CSS was missing in the
first round (buttons rendered unstyled but worked); styles now applied properly.
renamed: assignments_version -> sheet_version (one counter now also covers step back
and restore re-renders).

Feature 4 Step 2 - STEP BACK (per screen) == CODED 2026-10-16 = implementedeted ✅, awaiting human test per
process rule (Ctrl+F5 both finish sheet screens first):
- Amber 'Step Back' button in each station's banner. One press instantly (no confirm)
  reverses THAT station's most recent capture only - lap or finish, any sailor; never
  touches the other operator's captures. Pressing again steps to that station's
  previous capture.
- Toast bottom-right confirms what was removed, e.g. 'Stepped back: Lap 3 for Anton
  (14:03:12)' with a RESTORE button (10s). Restore re-applies with the ORIGINAL time.
- New table capture_actions (race, sailor, action, station, timestamp, lap_number,
  ref_id, undone, undone_at) - every lap/finish is logged with its station; undone
  actions are kept (nothing hard-deleted).
- Time policy (agreed): undo removes only the mistaken action; all other timestamps
  stay exact; the undone action's time drops off the live sheet (accepted by RO).
- 2s double-capture guard on the server: same sailor lapped twice within 2 seconds is
  rejected (double tap / both operators). Boats need minutes per lap.
- Superseded finishes refuse undo/restore (409) rather than corrupting data.
- record-lap/mark-finish now carry the station ID (record/replay distinguishes screens;
  old recordings without it still work - station NULL captures are not step-back-able).
- race-status sheet_version bump makes ALL stations re-render ~0.5s after a step back,
  restore or column toggle.
Regression: scripts/test_stepback.py (10 checks pass) + full suite passes.
Human test: run a short race, lap/finish from both stations, Step Back on each screen
must reverse only that screen's captures; Restore brings it back with the same time.

LAYOUT TIDY (RO control + finish sheets, per RO sketch 2026-10-16) == CODED same day = implementedeted ✅,
awaiting human test per process rule (Ctrl+F5 all pages):
- UNIFIED BUTTON SYSTEM across both pages: one .btn spec (12px 22px padding, 8px radius,
  15px/700 font, 46px min height, inline-flex centered, subtle shadow + hover lift).
  All inline style overrides removed; semantic colour classes only (btn-endrace blue,
  btn-sailwave purple, btn-finishsheet green, btn-stepback amber, etc.).
- RO page: header order per sketch [Start][Stop][Reset][End Race][Sound On]; right side
  now has [Refresh Sailwave][Finish Sheet 1][Finish Sheet 2] - the RO can jump straight
  to either station. Old single green Finish Sheet link removed.
- MOJIBAKE FIXED: the RO Refresh Sailwave button contained literal '\ud83d\udd04' text
  (from an old bad edit) and rendered as garbage - now the proper emoji.
- Finish sheets: browser tab title is now 'Finish sheet 1' / 'Finish sheet 2' (server
  passes the station; plain /finishsheet defaults to station 1); station badge +
  'Race Officer Control' back button on the left.
AMENDED 2nd RO feedback same day:
- RO page: Finish Sheet 1/2 links MOVED out of the header into the bottom bar next to a
  NEW 'Display Board' link (opens /display in a new tab) - header is now just
  [Start][Stop][Reset][End Race][Sound On] + clocks + STATE + Refresh Sailwave (less
  word wrap).
- Finish sheet banner button order per 2nd sketch: [FINISH SHEET + station badge]
  [<- Race Officer Control] [ELAPSED TIME] [Sailor Registry][Start Race][End Race]
  [Undo][Export CSV][Import Sailwave sailors]. 'Step Back' button renamed to 'Undo'
  (same feature: per-station instant one-step back, id btn-step-back unchanged);
  'Refresh Sailwave' renamed to 'Import Sailwave sailors' (same endpoint).
Regression: stations/stepback/start_event/open_flag all pass + render checks
(link targets, tab titles, button order) pass. Frontend needs the human browser test.

F0 flag folder split (flags moved into static/flags/classflags/ + signalflags/):
app scanned only the flat folder, so the RO flag picker was EMPTY and every flag URL
was dead. == Passed ✅ HUMAN TEST 2026-10-16 (RO picker shows CLASS FLAGS + SIGNAL
FLAGS groups; start event rows render; display board flags correct after refresh).
Fix: _scan_flag_folders() + flag_url() resolve each flag to its subfolder; bare
filenames stay in boat_classes/sequence so class matching, CSV and recordings are
unaffected; startup repair scans classflags only - a signal flag (p.png) can never
attach to a boat class (P Class = pclass.png, never merge).



1 the sailors selected in the register dont land in the correct finish class, the count down has 
three seperate starts with class flags, this should sort/goup the sailor register into 3 matching
 class, any unmathed will automaticall be in the 'open class' 
2 when click the clear sailor resitry - do  not display a warning - low risk of information loss,
 easy to recover from a user mistake == fixed ✅
3 csv export fails == fixed ✅

10 the sailor register sort by class no longer sorts == passed ✅ fixed (Sort by Class option was missing from the dropdown; added option + sort logic, secondary sort by name)
11 finish sheet start numbers now match the race officer grid numbers == passed ✅ fixed (grid renumbering updated the page headers but not the rows' grid_index, so class-start reported stale numbers; rows are now re-pointed when grids are removed/renumbered)
12 open category finish sheet did not activate == Passed ✅ human test FAILED 2026-10-15 (backend was fixed
and passed regression tests, 
15a flag asset fix - Passed ✅ P Class flag updated pclass.jpg -> pclass.png (new 686x785 image; boat_classes now points at pclass.png; old pclass.jpg removed from static/flags so it no longer appears as a draggable card in the RO flag picker). P (blue peter, p.png) and P Class (pclass.png) are TWO DIFFERENT flags/classes - do not merge them. tempref/recording.jsonl references updated to pclass.png so the replay tool keeps working.
13 the stray 'nul' file that broke git commits == resolved 2026-10-16 (git-level, not a browser bug): file deleted (it is a reserved Windows device name - Explorer and plain 'del nul' silently fail; Git Bash 'rm' removed it) and 'drag-drop-app/nul' is already in .gitignore, so commits cannot break again even if it reappears. Likely cause: a '> nul' redirect run in a Git Bash session (MSYS creates a real file named nul; cmd treats nul as a device, so the .bat launchers are safe).
16 requirements: 2 classes in the same start sequence == resolved 2026-10-16: Requirements.md updated (secondary/tertiary flag slots + shared starts). The code already supported it - one class-start POST per start event carries ALL the grid's flags, and every recognised class gets its own finish-sheet column.
6 move the add start button- = Passed ✅ on the RO page to the lower right == CODED 2026-10-16 (fixed
7 gold/yellow active countdown border halved Passed ✅ CODED 2026-10-16, awaiting human test per process rule
8 start event boxes narrower / more start sequences visible ==  == - Passed ✅ CODED 2026-10-16; 
9 finish sailors compact == == - Passed ✅ CODED 2026-10-16; AMENDED 
23 cannot add a new sailor on the Dell == passed ✅- keeps saying SL-2045 not available  How UIDs work: uid is the
sailors PRIMARY KEY



14 must allow a late sailor to be added  =PASSED ✅ to the race after it has started == regression + replay PASS (sailors signed on AFTER their class start stay visible in their own class column, live until first lap/finish, then join the locked roster race_sailors without duplicating. Regression: scripts/test_late_signon.py; replay of the 23:40 recorded session passes all 15 steps). Awaiting confirmed human test per process rule
21 = Passed  The timers are not recording start time = expert results show:
19 the open class can not record results and laps root cause as bug 12 (finishsheet.js poller re-disabled open-category cards every poll); fix applied with bug 12, awaiting confirmed human test

22 the sailor registry reset race did not clear the highlighted finish boxes and not ready for the next race of the day
== fixed ✅same  FIXED 2026-10-15, .
5 reset finish sheet =PASSED ✅does not reset anything - it should clear lap counts etc.

=================

Hot fix list = complete and tested & working

1) Note the RO and scorers tend to be retired sailors so the screns need to be simple  == == fixed ✅same

20 incorrect previous bug, on the finish sheet, the order of sailors must start with Lap Count asc, so once a sailor complets the lap they move to the bottom of the list, the person doing scoring is
 == == fixed ✅same CODED 2026-10-16, 

6 add a sound file to laptop speaker with count = implemented   ✅

**New Freatures


1 save start sequence for easy set-up
2 disqualify the sailor 
3 did not finish
5 results check from the score.db, to go back and re-Export, make a page to review and look at race results in the score.db, it has selectors and filters on the top row to make various selections




***Test Record/Replay (bug reproduction tool)

How to record a session:
1. In a browser open: http://localhost:5000/api/test/record?action=start
2. Click through the race-day flow exactly as when the bug occurred (build sequence,
   sign on sailors, start, laps, finishes, end race). Every API call your clicks
   produce is logged to tempref/recording.jsonl.
3. Stop recording: http://localhost:5000/api/test/record?action=stop

How to replay instantly (no countdown waits):

    C:\ProgramData\miniconda3\python.exe scripts/replay_race.py

The replay runs against a scratch copy of score.db (live data untouched) and fires
every recorded step back-to-back - class starts, laps and finishes all happen
immediately instead of waiting for the countdowns. Any step returning HTTP >= 400
is flagged FAIL with its request body - that is the minimal reproduction for the bug.
Options: --gap 0.2 (small pause between steps), --keep-db (keep scratch DB for inspection).

Note: recording stops if the server restarts (debug auto-reload) - start recording
after the pages are loaded, and record one bug session at a time.
