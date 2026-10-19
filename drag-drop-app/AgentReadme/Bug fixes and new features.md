***Bug fixes and new features

**PROCESS RULE (agreed 2026-10-15): a bug only moves to resolved after a confirmed HUMAN browser
test. Passing regression scripts alone is not enough.

**Bugs




=============================
in progress

Feature 

Feature 4 Step 1 - multi-station class split == CODED 2026-10-16, awaiting human test per
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

Feature 4 Step 2 - STEP BACK (per screen) == CODED 2026-10-16, awaiting human test per
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

LAYOUT TIDY (RO control + finish sheets, per RO sketch 2026-10-16) == CODED same day,
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

IMPORT SAILWAVE SAILORS - boat_master.htm source == CODED 2026-10-16, awaiting human test
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


4 the 2 end race buttons are not synched, 1 button on each page must stop all timers and chnage race status from running to ended
5 reset finish sheet does not reset anything - it should clear lap counts etc.
15 add the elapsed time per class for each finish sheet so the race officer will know when the max 
allowed time per race is approaching
18 if more than 4 strat events, then any remaining class defaults to open class even though it has a flag
 
==================
resolved
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
21 = Passed =PASSED ✅ The timers are not recording start time = expert results show:
19 the open class can not record results and laps root cause as bug 12 (finishsheet.js poller re-disabled open-category cards every poll); fix applied with bug 12, awaiting confirmed human test

22 the sailor registry reset race did not clear the highlighted finish boxes and not ready for the next race of the day
== fixed ✅same  FIXED 2026-10-15, .


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
4 multi-station finish sheet (named stations) - 2 operators capture laps/finishes on separate
  screens (e.g. 4K 14in touchscreen + non-touch laptop). Currently done as 2 tabs of the same page
  with no coordination between them - the data layer is already safe (server-truth SQLite), the
  problems are coordination: double capture (both operators can click LAP/FINISH on the same sailor
  a second apart = double-counted lap), polling lag between tabs, and manual drag order being
  tab-local only (race_sailors.placement is never written, so the two screens silently disagree).
  Design:
  a) /finishsheet?station=1 / ?station=2 - station ID remembered per tab, shown as a badge
  b) server-side capture claims - short-TTL lock per sailor uid (heartbeat while a card is being
     touched); the other station dims the card ("station 1 capturing") - prevents double capture
  c) replace polling with Server-Sent Events so captures propagate to all stations sub-second
  d) persist manual drag placement to race_sailors.placement so both screens converge on one order
  e) optional: assign class columns to a station to divide the work between operators
  Deliberately NOT BroadcastChannel (tab-to-tab messaging only works same-machine; future
  scenarios - start boat, other devices/clubs - need the server-side version). Touch events are
  just clicks, so the touchscreen needs nothing special.
  AGREED WITH RO 2026-10-16 (build order: flag folder fix F0 first, then station split,
  Step Back last):
  f) STEP BACK IS PER SCREEN, ONE STEP: each station gets its own instant (no confirm)
     Step Back button reversing only THAT station's most recent capture (lap or finish,
     any sailor); pressing again steps to that station's previous capture. Post-undo
     message with Restore; undone actions kept in a log with original timestamps; other
     times stay exact, the undone action's time drops off the live sheet (accepted).
  g) every capture carries its station ID (record/replay can then distinguish screens);
     server-side 2s double-tap lap guard.
  h) class-to-station split: station 1 defaults to the FIRST 3 classes, station 2 gets
     the rest; Open Category behaves like any other class (gets an assignment + toggle);
     a toggle on each class column header moves that class to the other station so the
     scorers can balance workload mid-race; assignments are server-truth and KEPT FOR THE
     WHOLE DAY (persist across races); 4 classes per station is guidance only, not
     enforced (weekend of 5 classes on one screen was unworkable - this split is also the
     feature 5 real-estate answer).
5 finish-sheet screen real estate management for 5+ classes on the course (this weekend:
  3-4 classes). Ideas: best idea, combine witht he multi station finish sheet, 
  classes load onto station 1 and the score officers toggle 1/2 and descide which classes are on which station idcollapsible/compress class columns, narrower banner, drop the class
  text from cards when the column already identifies the class (sail number only), reduce
  per-card padding, hide the 'x sailors' count. Any further real-estate gain beyond the
  2026-10-16 cosmetic round (flag removed from cards, compact one-line rows) is this feature.




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
