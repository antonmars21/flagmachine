

# Sailing Race Regatta Module ("Flag Machine") - Functional Specifications

## 1. Functional Requirements

### 1.1 Race Configuration & Planning Phase
* **FR-1.1**: The application must accept an administrative master start time input formatted precisely as `HH:MM`.
* **FR-1.2**: The user interface must provide a distinct left-side Library Column hosting an independent inventory of sailing class labels and graphical flag template assets.
* **FR-1.3**: The planner must allow the user to drag items (class templates and flag symbols) from the left library column and drop them directly into the active event grid.
* **FR-1.4**: The system must provide native vertical drag-and-drop mechanics to sort scheduled event rows from absolute top to bottom.
* **FR-1.5**: The planner must maintain a total separation between flag assets and timer intervals, allowing countdown clock changes to occur independently of the associated flag graphic.
* **FR-1.6**: Each row block must expose an editable numerical input field allowing the operator to dynamically change individual event durations in minutes.
* **FR-1.7**: Any updates to the sequence layout order or countdown parameters must instantly sync to the backend memory utilizing asynchronous network requests without causing full-page browser reloads.
* **FR-1.8**: Once race execution has been initiated, the planning grid must lock down completely, disabling all drag-and-drop structural edits until the total cascading sequence has finished.

### 1.2 Race Execution & Countdown Phase
* **FR-1.9**: The application must feature prominent global action components to trigger race events: `Start`, `Override Reset`, and `Override Stop`.
* **FR-1.10**: On initiation, the engine must bind to the host system clock and evaluate active time relative to the configured `master_start_time`.
* **FR-1.11**: Scheduled event timers must execute via a cascading, daisy-chained mechanism. As active row $N$ hits exactly `00:00`, its state shifts, its countdown closes out, and row $N+1$ directly starts its countdown loop.
* **FR-1.12**: The user interface must dynamically apply specialized CSS classes to adjust row visualization statuses automatically as the clock updates:
  * `PENDING`: Rendered in neutral layout formats for rows waiting in the cascade queue.
  * `ACTIVE`: Rendered in high-visibility colored or flashing formats for the currently running row.
  * `CLEAR`: Rendered in dimmed, muted formats for completed rows that have finished their run.
* **FR-1.13**: The system shall bypass and ignore all validation behaviors concerning optional auxiliary signals ("D Flag" and "E Flag") for the current Version 1 release.

## 2. Technical & Non-Functional Constraints

* **NFR-2.1**: The application must execute locally on Windows 11 using explicit pathways targeting the absolute Anaconda/Miniconda base python runtime environment (`C:\Users\anton\miniconda3\python.exe`).
* **NFR-2.2**: The application must fulfill all state mutations and counter updates smoothly without requiring standard web page refreshes.
* **NFR-2.3**: Static image files (.png, .jpg, or .svg assets) representing flags must reside in a structured local asset directory named `static/flags/`.
* **NFR-2.4**: The application codebase must construct its backend strictly utilizing Python 3 and explicit Flask modules (`Flask, render_template, request, jsonify`).