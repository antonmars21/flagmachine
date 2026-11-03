<!-- This is a Kanban Board file created with MD Kanban extension -->
<!-- GitHub: https://github.com/jebakumarj/md-kanban -->
<!-- VS Code Extension: Search "MD Kanban" in the extension store (ID: jeddak.md-kanban) -->

# Kanban Board

## To Do

## In Progress

#### RO page opened twice - duplicate windows on relaunch / double-click
<!-- id: task-1793590100000-7 -->
the single-instance guard only protected the Flask server; every relaunch (or a double-click on the desktop shortcut) re-ran the window-opening block and opened the RO page a second time. Fix: launch lock + "app windows already open?" check in START.bat and START.ps1 - relaunch only opens windows when none are open, so the RO page can never open twice.
<!-- priority: high -->

#### Display board opens twice
<!-- id: task-1793590200000-8 -->
RO page still had a Display Board link (opened a 2nd display as a tab next to the launcher's own display window) - link removed; and the relaunch duplicate-window guard only saw each browser process's main window, missing a non-main display window - now enumerates ALL visible windows (scripts/check_app_windows.ps1).
<!-- priority: high -->

#### Open class flag: sailors not defaulting to Open Category; stations not activating at start = 0
<!-- id: task-1793590300000-9 -->
with only openclass.png in the start event, sailors stayed in individual registry class columns instead of Open Category, so when the sequence hit 0 only the open start fired and no station card activated. Fixed in app.py sailors_for_onwater: group-all-by-class now requires a completely EMPTY sequence; open-only/signal-only sequence sends everyone to Open Category and the open start activates it. Regression: scripts/test_open_flag_only.py.
<!-- priority: high -->

#### Ticked sailors not added to the station sheets (Station 1 empty)
<!-- id: task-1793590400000-10 -->
checked against feature/sailwave-integration / v0.99: the sailor-loading code is identical, so NOT a navigation regression - root cause is stale class_station_assignments rows persisted in score.db from a previous day (c1/open pinned to station 2), which left Station 1 with no columns. Fixed: clear_stale_station_assignments() wipes the table at server startup when no race is RUNNING (fresh day -> default split), keeps toggles during a running race. Regression: scripts/test_stale_station_assignments.py.
<!-- priority: high -->

#### Fix screen navigation
<!-- id: task-1793589931663-0 -->
we had trouble on the Dell with visibility and difficulty witht eh seperate pages. the task bar navigation was great. we need to be able to tab the web pages. Unfortunatley the Dell is a bit old and not as good as the windos laptop. - keep taskbar navigation, split the station 1 and station 2 into seperate icons, launch tabed ito 1 broweer then the user can navigate by tabs and split the sation onto the seperate touch screen
<!-- priority: high -->

#### Export data .csv file to include a dediated column called Code
<!-- id: task-1793590017614-4 -->
refereence C:\Users\Public\Documents\Sailwave\Results\2026-2027_Season\Waikato Tanner Cup representative trials - test - edit and manage - "C:\Users\anton\flagmachine\drag-drop-app\AgentReadme\Race_code_rules.md"
<!-- priority: high -->

## Done
