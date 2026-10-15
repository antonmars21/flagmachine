***Bug fixes and new features

**PROCESS RULE (agreed 2026-10-15): a bug only moves to resolved after a confirmed HUMAN browser
test. Passing regression scripts alone is not enough.

**Bugs

==================
resolved

1 the sailors selected in the register dont land in the correct finish class, the count down has 
three seperate starts with class flags, this should sort/goup the sailor register into 3 matching
 class, any unmathed will automaticall be in the 'open class' == fixed ✅
2 when click the clear sailor resitry - do  not display a warning - low risk of information loss,
 easy to recover from a user mistake == fixed ✅
3 csv export fails == fixed ✅

10 the sailor register sort by class no longer sorts == passed ✅ fixed (Sort by Class option was missing from the dropdown; added option + sort logic, secondary sort by name)
11 finish sheet start numbers now match the race officer grid numbers == passed ✅ fixed (grid renumbering updated the page headers but not the rows' grid_index, so class-start reported stale numbers; rows are now re-pointed when grids are removed/renumbered)
12 open category finish sheet did not activate == Passed ✅ human test FAILED 2026-10-15 (backend was fixed
and passed regression tests, but the human test showed Open Category cards never activate).
Test scenario: Start 1 = Ilca 6 + Ilca 7 (Anton, Bridget - worked correctly, own columns, lapped
fine). Start 2 = pclass flag. Victoria (P Class) OK. Emma (Starling, no flag in sequence = Open
Category) - her column never activated when countdowns hit 0. Root cause found: finishsheet.js
pollClassStarts() re-disables every card whose class has not started on each poll, and Open
Category cards have no class_id, so they were permanently disabled even though the card was
created with buttons enabled. Fix applied: poller now treats open-category cards as started once
the race is running (race_id exists), and card creation only enables open-category buttons once
the race is active. NOTE: this is the same failure as bug 19. Regression scripts cannot catch
frontend bugs - awaiting confirmed human test (hard refresh Ctrl+F5 first, JS is cached).
BUSINESS RULE ADDED after clarifying the RO test setup (2026-10-15): the RO can drag the OPEN CLASS
flag (openclass.png) into a start event - the Open Category then activates ONLY when that start
event fires (e.g. open flag in Start 2 -> open activates at Start 2, not Start 1). Without an open
flag in the sequence, Open Category activates with the race's first start. Backend: class-start
recognises openclass.* (previously a silent 404 - no boat class behind it), open start stored in
app_state['open_start_time'], record-lap/mark-finish block open sailors until the open start fires,
race-status reports open_started/open_flag_in_sequence. Frontend: poller and card creation use
the backend-reported open_started. Regression: scripts/test_open_flag.py (all tests pass).
15a flag asset fix - Passed ✅ P Class flag updated pclass.jpg -> pclass.png (new 686x785 image; boat_classes now points at pclass.png; old pclass.jpg removed from static/flags so it no longer appears as a draggable card in the RO flag picker). P (blue peter, p.png) and P Class (pclass.png) are TWO DIFFERENT flags/classes - do not merge them. tempref/recording.jsonl references updated to pclass.png so the replay tool keeps working.


=============================
in progress




14 must allow a late sailor to be added to the race after it has started == regression + replay PASS (sailors signed on AFTER their class start stay visible in their own class column, live until first lap/finish, then join the locked roster race_sailors without duplicating. Regression: scripts/test_late_signon.py; replay of the 23:40 recorded session passes all 15 steps). Awaiting confirmed human test per process rule
21 The timers are not recording start time = expert results show:
Sequence	Class	Sailor	Sail No	Start Time	Laps	Lap Times	Finish Time	Race End Time
	Ilca 6	Anton	187893		1	2026-10-15T23:05:59.664573	2026-10-15T23:06:15.351890	2026-10-15T23:06:19.936983
	Ilca 6	Bridget	212958		1	2026-10-15T23:05:56.424181	2026-10-15T23:06:10.087931	2026-10-15T23:06:19.936983
	P Class	Victoria	177		1	2026-10-15T23:06:05.727660	2026-10-15T23:06:17.268994	2026-10-15T23:06:19.936983
	Starling	Emma	779		1	2026-10-15T23:06:04.032287	2026-10-15T23:06:13.304246	2026-10-15T23:06:19.936983
1	Ilca 7	John	214440	2026-10-15T23:04:52.983708	1	2026-10-15T23:06:02.381396	2026-10-15T23:06:11.737419	2026-10-15T23:06:19.936983
NOTE the start time and lap Times MUST be running on the total start sequence time, NOT the fist flag timer, 
check document in the start time there will be a sequence of flags, 
running ususally class flag for 1 minute, class flag plus P.png, for the second minute and dflag.png for the last minute.

22 the sailor registry reset race did not clear the highlighted finish boxes and not ready for the next race of the day
======================
active


4 the 2 end race buttons are not synched, 1 button on each page must stop all timers and chnage race status from running to ended
5 reset finish sheet does not reset anything - it should clear lap counts etc.
6 move the add start button on the race officer page to the lower right, 
use the same rectangle with rounded edge as all other buttons
7 the gold/yellow boarders for active count down is very wide/garish, 1/2 the line thickness.
8 the start event boxes need to be narrower so more start sequences are visisble, reduce cell padding, keep the text and falg boxes the same size
9 the finish sailors, aslo need to reduce the realestae and show many more sailors, line all data points onto 1 line, sail number is most promitent and right aligned
close to the lap counter

13 something creates a nul ("C:\Users\anton\flagmachine\drag-drop-app\nul") file that breaks the git commit
15 add the elapsed time per class for each finish sheet so the race officer will know when the max 
allowed time per race is approaching
16 write into requirements that 2 classes caan be in the same start sequence, currenlty the only 1 class can be use at a time.
17 the finish activates after the first sub timer, the finish sheet must be on the last subtimer in the start event 
18 if more than 4 strat events, then any remaining class defaults to open class even though it has a flag
19 the open class can not record results and laps == same root cause as bug 12 (finishsheet.js poller re-disabled open-category cards every poll); fix applied with bug 12, awaiting confirmed human test
20 incorrect previous bug, on the finish sheet, the order of sailors must start with Lap Count asc, so once a sailor complets the lap they move to the bottom of the list, the person doing scoring is
 workign with the sailors at the top of the list as the approach lap completion. 

**New Freatures
1 save start sequence for easy set-up
2 disqualify the sailor 
3 dnf 
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
