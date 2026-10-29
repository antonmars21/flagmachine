***Bug fixes and new features - CHANGELOG

V0.99 FIELD BETA 2026-10-29. This file is now the fix HISTORY/changelog - the
live task tracker is the kanban board (FlagMachine.kanban.md at the repo
root, git-ignored local file; columns Triage / Confirmed / In Progress /
Verify / Closed). Open work lives on the board: B26 (start event box drop
slots), B24 (late join time), B15 (awaiting explicit RO confirmation),
D1 (Europe flag image) + features F1-F5 (save sequence, DSQ, DNF, Sailwave
refine, results review page). Current system snapshot: CURRENT_STATE.md.

**PROCESS RULE (agreed 2026-10-15): a bug only moves to resolved after a confirmed HUMAN browser
test. Passing regression scripts alone is not enough.

**Bugs

=============================
in progress

Bugs to fix:

 26 there need to be more space to drage and drop flags into the startevent box, ad a few spaces for additional flags

=============================
To Test 

===========================

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



 27 3rd race Sat 24 Oct 26 (race 67) has NO results - server restarted mid-race == PASSED ✅ HUMAN TEST  29/10CODED 2026-10-27, awaiting human test
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

 30 station buttons + Race Officer button open NEW browser tabs/sessions == FIXED
PASSED ✅ HUMAN TEST 2026-10-27 (Anton: "the station 1 and station 2 buttons
work correctly" - no new tabs, same-tab round trip confirmed). The blank
RO page seen during the same test is bug 31 (below), a different bug.
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

 31 PASSED ✅ HUMAN TEST  29/10RO page comes up EMPTY (no flags, no settings) after navigating back from a station == CODED 2026-10-27, awaiting human test
AMENDED same day after the first human test: "nearly - going back to the RO
control resets to start time number and stops the clock". The sequence now
restores, but a countdown that was RUNNING reset to its initial values
and stopped. Root cause: the countdown clock is client-side and nothing
told the server when Start was pressed. Fix (part 2): /execute-control
START now records fm_countdown_started_ms (epoch ms, POSTed by the RO
page), /api/race-status carries it, and the RO page's 500ms poller
RESUMES the countdown from the real elapsed time when it sees fm RUNNING
+ a stored start (STOP/RESET/END_RACE clear it). The first tick after a
resume catches up SILENTLY (no horn blast / no announcement pile-up) and
re-fires any class start that completed while the page was away,
BACKDATED to its true crossing time (/api/class-start accepts optional
started_at_ms; only past values accepted; re-fires are ignored - first
trigger wins, no duplicates).
RO report 2026-10-27 (found while human-testing bug 30): the Race Officer
Control button navigates back correctly, but the RO page loads FRESH - all
flags and settings are gone. Same on any refresh of the RO page. Root
cause: the start sequence lives in app_state['sequence'] on the SERVER
(the finish sheets keep their class columns from it), but the RO page only
ever PUSHED its drags to the server - nothing rebuilt the grids from the
server state, so every page load started blank.
Fix: index.html now renders window.INITIAL_SEQUENCE from app_state;
app.js restoreSequenceFromServer() rebuilds every grid + row (primary,
secondary and tertiary flags, labels, minutes, grid numbers) on page load
when the page's own sequence is empty. Runtime state (countdown position)
is NOT restored - a reloaded page shows the sequence ready; the countdown
itself runs in the RO tab that pressed Start, so keep the RO page on the
RO screen while a countdown is running (as on the water anyway).
Regression: scripts/test_ro_restore.py (sequence embedded with rows/
flags/grids, [] embeds on fresh sessions, app.js rebuilds on load incl.
2nd/3rd flag boxes; countdown_started_ms stored/cleared, race-status
carries it, class-start backdates to the true crossing time, re-fires
ignored, app.js resumes + catches up silently) PASS; js balance check on
app.js PASS; full suite PASS (test_export_naming + test_export_sailwave
made hermetic - clear the race history in their scratch, because the live
DB accumulates same-day test races and the series race number counts
every started race).
Human test (Ctrl+F5 the RO page first - HTML + JS are cached): build a
sequence with 2 starts and a secondary flag, press START, open Finish
Sheet 1, click 'Race Officer Control' - the clock must STILL BE TICKING
at the correct remaining time (not reset, not stopped). F5 on the RO
page mid-countdown must also resume the clock. Classes that finish while
the page is away must appear started (with their true start times) on
return.

 29 Dell exports: PASSED ✅ HUMAN TEST  29/10no series name + filename not series/date == CODED 2026-10-27, awaiting human test
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


32 + 34 (navigation) - PASSED ✅ HUMAN TEST  29/10 RO to station navigation closes the RO control == CODED 2026-10-29, awaiting human test
RO report 2026-10-28: navigating from RO control to a finish station (and
the RO-to-stations button generally) replaced the RO page - the RO control
window, with its countdown, horn and voice, was gone until the operator
navigated back. Bug 31's resume made the DATA survive, but the RO screen
itself must never move.
Fix (the agreed direction from the bug 32 note): application windows, not
browser tabs, and no navigation buttons at all:
- START.bat now waits for the server to answer, then opens each page in its
  OWN Chrome/Edge application window (--app mode: no tab bar, no
  back/forward buttons): RO control (/), Finish Sheet 1
  (/finishsheet?station=1), Finish Sheet 2 (/finishsheet?station=2) and the
  Display Board (/display). Chrome is used if installed, otherwise Edge
  (present on every Windows 10/11 machine).
- The Finish Sheet 1/2 buttons are REMOVED from the RO page
  (templates/index.html) and the 'Race Officer Control' back button is
  REMOVED from both finish sheets (templates/finishsheet.html) - there is no
  way left to navigate a work window onto another work page, so the RO
  control cannot be closed by navigation. Each window is one purpose, one
  session (station id in sessionStorage stays per window).
- The Display Board link stays on the RO page (new tab BY DESIGN - separate
  outdoor screen, and it does not navigate the RO window away).
- START.ps1 left as-is (legacy launcher; START.bat is the documented path).
Regression: scripts/test_navigation.py rewritten for the new design (RO page
has no finish-sheet links, finish sheets have no work-page links or any
target attribute, display board unchanged, START.bat must open all four
pages as --app windows) PASS; full suite (18 scripts) PASS.
Human test: double-click START.bat - after the app starts, FOUR separate
application windows must open (RO control, Finish Sheet 1 with Station 1
badge, Finish Sheet 2 with Station 2 badge, Display Board), each WITHOUT
browser tabs or navigation buttons. The RO page must show no Finish Sheet
buttons; the finish sheets must show no 'Race Officer Control' button; press
F5 on the RO page mid-countdown - the clock must resume (bug 31 behaviour,
unchanged).
AMENDED 2026-10-29 (RO request: taskbar as the key navigator): every window
now has a UNIQUE taskbar icon - a Chrome/Edge --app window takes the page's
FAVICON as its window/taskbar icon, so each page embeds a distinct one:
RO control = red 'RO' (icon_ro.png), Finish Sheet 1 = green '1'
(icon_fs1.png), Finish Sheet 2 = blue '2' (icon_fs2.png), Display Board =
orange 'D' (icon_display.png). Icons are 128x128 PNGs in static/icons/,
generated by the no-dependency utility scripts/make_window_icons.py (pure
stdlib - no new pip requirement); the finish sheet picks its icon by the
station passed from the server. NOTE (first launch after this change):
browsers cache favicons - the taskbar may show old/generic icons until each
window has been refreshed once (F5). Windows taskbar tip: if the four
windows group under one browser button, set taskbar buttons to 'Never
combine' (Settings > Personalisation > Taskbar) so each window shows its
own icon+label.
Regression: scripts/test_navigation.py extended (all four pages embed a
DISTINCT favicon link, finish-sheet icons differ per station, every icon
file exists and serves over HTTP) PASS.
Human test: START.bat -> four windows, hover the taskbar: RO control shows
the red RO icon, Finish Sheet 1 green 1, Finish Sheet 2 blue 2, Display
Board orange D; F5 each window once if an icon looks stale.
AMENDED 2026-10-29 (RO: "tidy up the graphics in these icons"): the icons
were a 5x7 block font scaled up - jagged/pixelated. make_window_icons.py is
rewritten as a small VECTOR rasterizer (still pure stdlib, no Pillow): the
glyphs are drawn geometrically (stroke capsules + ellipse rings/sectors for
the R bowl, O, 2 arc, D bowl) and anti-aliased with 9 subsamples per pixel,
on a rounded-corner square with a vertical gradient and TRANSPARENT corners
(RGBA PNG), plus a slightly darkened anti-aliased edge so each icon stays
defined against any taskbar background. Same four PNGs, same filenames, no
template changes; run with --preview for an ASCII shape check.
Human test: F5 each window once (favicons are cached) - icons must look
smooth, not pixelated, with rounded corners and a gradient fill.
Regression: scripts/test_navigation.py extended (all four pages embed a
DISTINCT favicon link, finish-sheet icons differ per station, every icon
file exists and serves over HTTP) PASS.
Human test: START.bat -> four windows, hover the taskbar: RO control shows
the red RO icon, Finish Sheet 1 green 1, Finish Sheet 2 blue 2, Display
Board orange D; F5 each window once if an icon looks stale.

HERMETIC TESTS 2026-10-29: the live registry is user-managed (old sailors
tidied away, roster refreshed from Sailwave), and four regression scripts
still depended on live sailors existing (SL-1091 etc.) - they broke the
moment the roster was tidied. test_export_csv, test_export_sailwave,
test_grouping + test_open_category now seed their own fixture sailors into
their scratch DB copies via scripts/seed_test_sailors.py (INSERT OR REPLACE
on the SCRATCH only - the live DB is never touched), and test_export_csv's
name assertion was corrected to the Sailwave layout (HelmName = FULL
sailor_name, not short_name; its hardcoded Starling class_id 3 is now a
name lookup). Full suite (18 scripts) PASS against the tidied live DB.

WED 28 OCT RESULTS EXPORTED 2026-10-29 PASSED ✅ HUMAN TEST  29/10(race 76, the day's single race,
regenerated with the bug-29 naming): 'Sailing Results 28-10-26/Twilight
Series club racing R3 28-10-2026.csv' - 15 sailors, 13 finishes, 2 P Class
sailors without a finish (empty FinishTime for DNC/DNF coding), Series
column + series race number R3 correct. NOTE: in this export every sailor
carries their own class and its start time (Ilca 4 sailors exported as
Ilca 4, start 18:12) - the 'Ilca 4 defaulted to open class' report (below)
was a finish-SHEET display behaviour, not an export corruption.

33 + 34 -  PASSED ✅ HUMAN TEST  29/10Ilca 4 sailors load into Open Category despite the Ilca 4 flag in the start event box == CODED 2026-10-29, awaiting human test
RO report 2026-10-29 (after bug 35 passed): "the loading sailors is working,
Ilca 4 are still loading into open class despite having a flag in the start
event box, visible left yellow flag". Root cause (the data half flagged in
the bug 35 note): boat_classes had NO 'Ilca 4' row. Manually added sailors
(add/edit sailor linked the class by NAME and never created the class row -
only the Sailwave import did), so the Ilca 4 sailors had class_id NULL. The
start sequence -> column lookup matches boat_classes BY FLAG IMAGE, so the
dragged ilca4.png matched NOTHING: no Ilca 4 column was created and the
sailors grouped into Open Category (this was also Wednesday's bug 34).
Fix (app.py):
- repair_missing_boat_classes() runs at startup next to
  reconcile_class_flag_images(): every distinct sailors.boat_class without a
  boat_classes row gets one (flag auto-matched from the class flag folder,
  never openclass.png - Open Category is a virtual column), and NULL
  sailors.class_id values are linked to it. Classes with no flag image
  (Europe) keep their sailors in Open Category, which is correct: no
  flag = no start.
- ensure_boat_class_id(): add-sailor + edit-sailor now get-or-create the
  class, so manual entries can never strand sailors again.
- find_class_flag_image(): class flags only - signal flags can never attach
  to a class; openclass.png can never be a class flag.
LIVE DB HEALED 2026-10-29 (idempotent repair, verified before/after): new
class rows 'Ilca 4' (class_id 14, ilca4.png) + 'Europe' (class_id 13, no
flag image exists on disk); the 3 Ilca 4 sailors (Lucy SL-3, Rose SL-51360,
Helen SL-0206424) are linked to Ilca 4. Gabrielle (Europe) stays Open
Category until a Europe flag image is dropped into static/flags/classflags/.
Verified on the live server: /api/sailors-for-onwater now returns a real
'Ilca 4' column (flag ilca4.png) - no restart needed beyond the one the RO
already did.
Regression: scripts/test_class_repair.py (repair creates the Ilca 4 class
with ilca4.png + links sailors; ilca4.png flag in the sequence -> Ilca 4
COLUMN with its sailors; Europe stays Open; class-start fires for the
created class; add-sailor creates a missing class; edit-sailor re-links;
openclass.png never a class flag; P Class = pclass.png + signal flags
clean; idempotent) PASS. test_open_lap_counts.py made hermetic (post-repair
no named-class sailor stays class_id NULL, so it seeds a CLASSLESS sailor -
empty boat_class - as its open-category fixture). Full suite (20 scripts)
PASS.
Human test (no restart needed - the classes are already in the live DB):
drag the Ilca 4 flag into a start event -> the finish sheet must show an
'Ilca 4' column (not Open Category) with the Ilca 4 sailors in it; tick a
new Ilca 4 sailor -> they land in the Ilca 4 column. Note the Ilca 4 column
defaults to station 1 (first-3 rule) - use the station toggle on its header
if station 2 should score it. On the Dell: next START.bat run performs the
same repair automatically.

DESKTOP LAUNCHER + SINGLE-INSTANCE GUARD == PASSED ✅ HUMAN TEST  29/10CODED 2026-10-29, awaiting human test
RO request: a desktop shortcut to launch the app, and relaunching must never
leave more than one localhost (Flask server) running.
- START.bat now checks whether http://localhost:5000 already answers BEFORE
  starting anything: if it does, NO second server is started - the batch says
  "ALREADY RUNNING", reuses the existing server and just reopens the four app
  windows (this is also how a closed window gets restored). A fresh launch
  (server down) starts Flask as before and waits for it to answer.
- New desktop shortcut "Flag Machine" (created on this machine's desktop
  2026-10-29): points at START.bat, working dir = the app folder, icon =
  static/icons/app.ico. The icon is a NEW pennant-flag glyph (navy square,
  two white pennants on a pole) drawn by the same vector rasterizer in
  make_window_icons.py, wrapped as PNG-in-ICO (no new dependency).
- scripts/make_desktop_shortcut.bat creates/updates the shortcut for the
  CURRENT user, always pointing at the START.bat next to its own folder -
  run it once on the club laptop / the Dell to install the shortcut there.
Regression: scripts/test_navigation.py extended (the already-running check
must precede the Flask start line; the ALREADY RUNNING path reuses the
server; shortcut installer exists; app.ico is a valid PNG-in-ICO) PASS; full
suite (20 scripts) PASS.
Human test: double-click the desktop "Flag Machine" shortcut -> server +
four windows come up. Double-click it AGAIN while the app is running -> NO
second server window appears (the Flask command window count stays 1); the
app windows reopen - close extras. Close one app window, relaunch the
shortcut -> the window is restored against the SAME running server.

35 - the sailor registry does not load the sailors when they are ticked into the race start list == FIXED
PASSED ✅ HUMAN TEST 2026-10-29 (Anton: "the loading sailors is working").
RO report 2026-10-29 (after the app-window launch worked): ticking sailors in
the Sailor Registry did not load them into the finish-sheet start list; the
window eventually refreshed after 10+ seconds (or a restart). Investigation:
the live server + API serve ticked sailors correctly in every state (verified
against the live 22:08 server AND a scratch DB) - the freeze is client-side.
Root cause: app_state['race_id'] STAYS SET after End Race (by design - only
Reset clears it, so end-race/laps/CSV export keep targeting the ended race),
and finishsheet.js computed `state.race_active = !!data.race_id`. After the
first race of the day was ended, EVERY column refresh was gated behind
`if (!state.race_active)`: the tick handler, the 3s background refresher,
clear-registry and add/edit/delete sailor all froze - ticked sailors never
loaded until a Reset, a sheet_version bump or a restart. The same gate also
hid mid-race late sign-ons (bug 14 worked at the API level but the sheet
never re-rendered).
Fix (static/js/finishsheet.js):
- race_active now means RUNNING: `!!data.race_id && !data.race_ended` - once
  the race is ENDED the columns go live again. Bug 4 is intact: fm_status
  ENDED still locks Start Race (fmEngaged) and lap/finish inputs stay
  disabled until a Reset.
- a tick / clear-registry / add / edit / delete is a DELIBERATE sign-on
  action: loadAndRenderSailors() now runs unconditionally (mid-race late
  sign-ons appear immediately, bug 14's visible half). Only the automatic
  3s poller keeps its pre-race gate (no churn while a race runs).
Regression: scripts/test_registry_refresh.py (pre-race tick served, race_id
persists after End Race - the trap, tick after End Race served live as a
late sign-on, reset-finish-sheet clears it, JS invariants: the race_ended
guard on race_active, exactly ONE gated refresh left = the 3s poller,
brace balance) PASS; full suite (19 scripts) PASS.
Human test (Ctrl+F5 BOTH finish sheet windows first - the JS is cached):
1. tick a sailor BEFORE any race -> they appear in their class column
   immediately (well under 3s).
2. start a race, end it, then tick a NEW sailor -> they must appear in the
   start list immediately (previously this stayed frozen until a reset).
3. mid-race, add a late sailor (Add Sailor form or tick) -> they must appear
   in their class column while the race is still running.
NOTE while investigating (data facts, not bugs): the tidied roster's Ilca 4
and Europe sailors have class_id NULL because boat_classes has NO 'Ilca 4'
or 'Europe' row (add-sailor links class by name and never creates the class
row; the Sailwave import DOES create classes). They can only ever group into
Open Category until those class rows exist (this is the data half of bugs
33/34). ilca4.png exists in static/flags/classflags/, so adding an 'Ilca 4'
class row pointing at it is all that is needed for a proper Ilca 4 column.


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
4 refine Sailwave import export
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
