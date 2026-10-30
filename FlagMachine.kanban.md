<!-- This is a Kanban Board file created with MD Kanban extension -->
<!-- GitHub: https://github.com/jebakumarj/md-kanban -->
<!-- VS Code Extension: Search "MD Kanban" in the extension store (ID: jeddak.md-kanban) -->

# FlagMachine Board

Board rules: a card reaches Closed ONLY after a confirmed HUMAN browser test
(process rule 2026-10-15). Regression scripts alone are never enough. Never
reopen a Closed card - file a new card that references the old one. Full fix
history: `drag-drop-app/AgentReadme/Bug fixes and new features.md`.
ID scheme: **B**ug / **F**eature / **D**ata.

## Triage

#### new bug
<!-- id: task-1793269849027-0 -->

## Confirmed

#### B26 - More drag-and-drop space in the start event box
<!-- id: task-v099-0-b26 -->
Not enough space to drop flags into the start event box; add a few empty
slots for additional flags. Never coded - pure RO-page UI
(templates/index.html + app.js). Check layout against bug 8 (narrower
event boxes).
**Accept:** each event box shows several empty drop slots; a flag dropped
into a later slot lands there without squeezing existing rows; sheet
columns and grid numbers unchanged.

#### B24 - Record the time a late sailor joins the race
<!-- id: task-v099-0-b24 -->
Late sign-ons appear live until first lap/finish (B14, closed), but the
moment they joined the race is not recorded anywhere.
**Accept:** a late sign-on carries its join timestamp in the DB (new
column or capture_actions entry); visible on the results page (F5).

#### D1 - Europe class flag image
<!-- id: task-v099-0-d1 -->
'Europe' is a real class (created by the B33/34 repair) but has no flag
image, so Europe sailors stay in Open Category - correct while no flag
exists.
**Accept:** drop a Europe flag image into static/flags/classflags/, restart
- the repair attaches it and Europe gets its own start column.

#### F1 - Save start sequence for easy set-up
<!-- id: task-v099-0-f1 -->
The RO rebuilds the same sequence every race day. Save the current start
sequence under a name and reload it from the RO page in one click. Server
state already rebuilds the page (B31 machinery); needs storage in score.db
+ Save/Load UI + regression script.
**Accept:** build a sequence, save it, restart the app, load it back -
every grid, flag, label and duration restores identically.

#### F2 - Disqualify the sailor (DSQ)
<!-- id: task-v099-0-f2 -->
Mark a sailor DSQ from the finish sheet after the race; the result carries
through to the Sailwave CSV export.
**Accept:** DSQ a finished and an unfinished sailor -> the CSV codes them
DSQ so the scorer does not edit by hand in Sailwave.

#### F3 - Did not finish (DNF)
<!-- id: task-v099-0-f3 -->
One-click DNF for sailors still on the water at race end; carried to the
CSV (today unfinished sailors export with an empty FinishTime). Pairs
naturally with F2.
**Accept:** end a race with unfinished sailors, mark one DNF -> CSV codes
DNF.

#### F4 - Refine Sailwave import/export
<!-- id: task-v099-0-f4 -->
General tidy-up of the Sailwave round-trip: field mapping, class matching,
UID edge cases (e.g. the Dell's SL-2045 report).
**Accept:** agreed per refinement when the card is pulled.

#### F5 - Results check page (review + re-export from score.db)
<!-- id: task-v099-0-f5 -->
A page to browse recorded races in score.db: selectors/filters on the top
row (date, series, class, sailor), review laps/finishes, re-export any race
as the Sailwave CSV. Groundwork exists: scripts/export_race_by_id.py.
**Accept:** open the page, pick a past race, re-export it byte-identical to
the original export.

## In Progress

## Verify

#### B15 - Per-class elapsed clocks
<!-- id: task-v099-0-b15 -->
Coded 2026-10-22 and working in field use since, but never explicitly
confirmed by the RO. Confirm on the water and close.
**Accept:** each class column header clock ticks from that class's start
and freezes at race end; cards stay single-line name + sail number.

## Closed

#### v0.99 field beta - navigation + windows (2026-10-29)
<!-- id: task-v099-0-c-nav -->
B30/B31/B32+B34 app windows (START.bat --app mode, no navigation buttons),
sequence + countdown restore on reload, unique taskbar icons, desktop
launcher with single-instance guard. Human-confirmed 2026-10-29.

#### v0.99 field beta - class grouping + registry (2026-10-29)
<!-- id: task-v099-0-c-class -->
B33+B34 missing boat classes self-heal (Ilca 4 column from its flag),
B35 registry ticks load sailors before/during/after a race, B28 open lap
counters, B12/B19 open category activation, B14 late sign-on, B24-era
reset-finish-sheet fixes (B22/B5). Human-confirmed 2026-10-29.

#### v0.99 field beta - results + exports (2026-10-29)
<!-- id: task-v099-0-c-export -->
B29 export naming + series race numbers (R1, R2, ...), calendar ships with
the app (Feature 6), Sailwave CSV import/export (Feature 7), B27 mid-race
server restart recovery, Wed 28 Oct results re-exported. Human-confirmed
2026-10-29.

#### v0.99 field beta - start line + stations (2026-10-29)
<!-- id: task-v099-0-c-start -->
B4 end-race/start-button sync, B25 voice-over countdown, Feature 4
multi-station finish sheet with per-station undo, HOTFIX drag-and-drop JS
parse, B10/B11/B20 sheet ordering + grid numbers. Human-confirmed 2026-10-29.
