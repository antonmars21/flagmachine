<!-- This is a Kanban Board file created with MD Kanban extension -->
<!-- GitHub: https://github.com/jebakumarj/md-kanban -->
<!-- VS Code Extension: Search "MD Kanban" in the extension store (ID: jeddak.md-kanban) -->

# Kanban Board

## To Do

## In Progress

#### record to get edit
<!-- id: task-1793875762855-467 -->
the datbase appears to not release the sailor edit lock. 1) if rob started a race, then the race ended after the race edit his sail number.(last week observation) the edits dont save. 2) this week, edited jonh barnard ilca 6 sail no, saved correctly, any following edits did not save (appear editing locked)
FIXED 2026-11-09 (main f3a08a1+): root cause was the 2026-11-05 sail-no fixes never being merged to main (Dell ran old UNIQUE(sail_no) + stuck modal). Regression test_edit_after_race.py PASS (edits stick after race+reset, cross-class share OK). Awaiting RO human test on the Dell (git pull, Ctrl+F5) before Done.

#### Bug - eport to csv failed
<!-- id: task-1794209214091-5 -->
the export to csv failed: 1) find cause, this was perviously working, 2) when the user clicks end race, automatically make a .csv download, both files, Sailwave race/regatta import and the results, 3) do not zip, this creates more work for the RO who want to get and publsih the reults quickly. 4) (new functionality), when the user clicks export to csv, provide a multi select list of previosue race names and dates, and race numebr so they can get older data if needed for amendment to sailwave. - the is a link to the bug
<!-- priority: high -->
FIXED 2026-11-09 (main f3a08a1+): causes were ZIP-on-series-days + 400 after reset. Now plain CSV always, series template its own download, export falls back to last race, End Race auto-downloads both files, export button = multi-select of past races. Regression test_export_workflow.py PASS, suite 27/27. Awaiting RO human test (Ctrl+F5) before Done.

## Done
