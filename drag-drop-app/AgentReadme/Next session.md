# Next Session - Decisions Needed

Read `AgentReadme/Bug fixes and new features.md` first for the full bug list and status.

## Q1. Bug 14 - confirm diagnosis
Your recording shows SL-177 (Charlotte, P Class) signed on 23s AFTER the P Class start fired.
She then vanishes from the finish sheet (not in the locked roster, excluded from live rows).
Is this bug 14? If yes, which handling:
  a) Show late sign-ons in their class column, flagged "late" (recommended)
  b) Route them to Open Category
  c) Block the registry checkbox once their class has started

## Q2. Open class rule - minimum 3 boats to constitute a class
Confirm: class with <3 signed on at its start moment -> sailors sail in Open Category.
Sub-decisions:
  a) Decide at class-start moment and freeze (recommended) - or another time?
  b) Hide the sub-3 class column on the finish sheet, or show empty?
  c) Once dissolved to open, it stays open even if a 4th boat signs on late - OK?
  d) Open category results need handicap/corrected times (Phase 2) - required now or later?
  e) Add an amber signed-on count per flag on the RO page as a pre-start warning?

## Q3. Bug 5 scope - reset finish sheet
Recording shows reset-finish-sheet also WIPES the live Flag Machine sequence (app_state).
Confirm: reset should clear laps/finishes/placements but NEVER touch a running sequence.

## Q4. Remaining bug priority order
Active bugs: 4 (end-race button sync), 5 (reset), 6-9 (UI layout), 13 (nul file breaks git commit).
Which order? Suggested: 4 and 5 (race-critical), then 13 (blocks commits), then 6-9 as one UI pass.

## Q5. New features priority
1 Save start sequence, 2 DSQ, 3 DNF - which first? (DSQ/DNF pair naturally with bug 12/open work.)

## Housekeeping reminders for next session
- tempref/recording.jsonl = the 23:40 session (SL-177 late sign-on repro). Replay:
  C:\ProgramData\miniconda3\python.exe scripts\replay_race.py
- Hard refresh browser (Ctrl+F5) before testing - JS is cached.
- Regression tests live in scripts/: test_grouping.py, test_export_csv.py, test_open_category.py,
  test_import_and_flags.py (all run against scratch DB copies, never live data).
