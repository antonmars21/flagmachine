# Next Session - Decisions Needed

Read `AgentReadme/Bug fixes and new features.md` first for the full bug list and status.

## Q1. Bug 14 - DECIDED 2026-10-15 (fixed)
Late sign-ons stay in their OWN class column, no "late" badge (common after boat repairs).
Fix in `/api/sailors-for-onwater`: sailors whose class started but who are not in the locked
roster (race_sailors) stay live and visible until their first lap/finish, then join the roster
without duplicating. Regression: `scripts/test_late_signon.py`.

## Q2. Open class rule - DECIDED 2026-10-15 (implemented as bug 12 rule)
No minimum-boat rule. The RO sets class flags in the start events; when a sailor's class has a
flag (primary OR secondary) they get their own column; when there is no matching flag they go to
Open Category. The RO can load multiple classes into one start (e.g. Ilca 6 + Ilca 7 together)
via the secondary flag - backend now matches ALL flags in every start event.

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
