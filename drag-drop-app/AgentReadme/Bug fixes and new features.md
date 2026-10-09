***Bug fixes and new features

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

=============================
in progress


12 open category did not activate and could not lap count or click finished == part failed - the open category  did not have
 a flag on the race officer page, john and brian had their own columns but could not count laps or finish. 
 I think it is easistest to ensure the race office MUST ut a open class flag, needs a retest business rule fixed (backend blocked laps/finishes for classes without a countdown start, 
 and open-category sailors were never added to race_sailors; 
 they now activate with the race start and join the race on first lap/finish)
14 must allow a late sailor to be added to the race after it has started, 
this happens quite frequently if a sailor has returned after boat repairs
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


**New Freatures
1 save start sequence for easy set-up
2 disqualify the sailor 
3 dnf 




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
