# Drag-and-Drop Web Application Architecture

This project implements a full-stack Kanban-style interface featuring real-time client-to-server state synchronization using native web APIs and Python.


┌────────────────────────────────────────────────────────────────────────┐
│                        GLOBAL CONTROL HEADER                           │
│  [Master Start Time: HH:MM]     [START]   [STOP]   [RESET OVERRIDE]    │
│  [Live System Clock: HH:MM:SS]                     [STATE: STATUS]     │
├───────────────────────────────────┬────────────────────────────────────┤
│     LEFT-SIDE ASSET PALETTE       │      VERTICAL SEQUENCE PLANNER     │
│   (Dynamic Folder-Scanned Templates)  │        (Active Event Grid Schedule)    │
│                                   │                                    │
│  ┌─────────────────────────────┐  │  ┌──────────────────────────────┐  │
│  │ ☰ [Flag Asset: Class Flag]   │  │  │ Row 1: Ilca 6  [ 03:45 ]     │  │
│  │     (Draggable Template)    │  │  │ Status: ACTIVE (Flashing)    │  │
│  └─────────────────────────────┘  │  └──────────────────────────────┘  │
│  ┌─────────────────────────────┐  │  ┌──────────────────────────────┐  │
│  │ ☰ [Class Profile: Starling] │  │  │ Row 2: Starling [ 05:00 ]    │  │
│  │     (Draggable Template)    │  │  │ Status: PENDING (Neutral)    │  │
│  └─────────────────────────────┘  │  └──────────────────────────────┘  │
└───────────────────────────────────┴────────────────────────────────────┘




old 30/05/2026
## 🛠️ System Architecture Diagram

```text
[ Browser Frontend ]                               [ Flask Backend (Python) ]

  |                                                  |
  |-- 1. Drag & Drop Event (JS API)                  |
  |-- 2. DOM Updates (Moves Element)                 |
  |-- 3. HTTP POST request (Fetch API JSON) -------->|
  |                                                  |-- 4. Parses JSON Payload
  |                                                  |-- 5. Mutates Data Dictionary
  |<-- 6. Returns HTTP 200 OK (Success JSON) --------|
```

## 📐 Key Functional Blocks

### 1. The Frontend UI (HTML5 / Native JavaScript)
* **Draggable Elements:** Items use `draggable="true"` and the `ondragstart` listener to load their unique string identifier into the browser data buffer using `ev.dataTransfer.setData()`.
* **Drop Targets:** Columns monitor continuous movement via `ondragover` (where `ev.preventDefault()` must be called to allow drops) and process the payload via `ondrop`.
* **State Sync:** Instead of refreshing the page, JavaScript triggers an asynchronous network request (`fetch()`) sending the payload down to the server context.

### 2. The Backend Runtime (Python 3 / Flask)
* **Routing:** Listens dynamically on `/` for presentation delivery and `/update-item` strictly via `methods=['POST']` for state updates.
* **Payload Ingestion:** Uses `request.get_json()` to convert incoming JSON streams automatically into standard Python dictionaries.

---

## 🐍 Environment Data & Command Logs

For future system updates or debugging, use these configuration properties extracted from system verification:

* **Host Environment Manager:** Anaconda (Conda Base Environment)
* **Absolute Python Runtime Path:** `C:\Users\anton\miniconda3\python.exe`
* **Network Binding Endpoint:** `http://127.0.0.1:5000`

### Routine Project CLI Commands

Always run these commands from the `C:\Users\anton\flagmachine\drag-drop-app` folder directory:

#### Install Dependencies
```powershell
C:\Users\anton\miniconda3\python.exe -m pip install flask
```

#### Launch Application Engine
```powershell
C:\Users\anton\miniconda3\python.exe app.py
```

#### Terminate Server Instance
Press **`Ctrl + C`** directly inside the active PowerShell terminal panel.
## 🔄 Revision Addendum: Vertical Sequence Planner Pivot

The architecture has evolved from a two-dimensional Kanban layout (column-to-column item migration) to a **One-Dimensional Sequential Array Planner** explicitly tailored for temporal sequencing.

### 📐 Structural Realignment
1. **Data State Layer**: The master dataset represents a unified object wrapping global states (`master_start_time`, `override_status`) and an indexed array of boat events containing variables for flag assets, strings, and integers for timing parameters (`countdown_minutes`).
2. **Reordering Engine**: The HTML5 drag-and-drop mechanism has been restricted to vertical container boundary tracking. Instead of posting individual task-to-column migrations, the system updates state by passing an array of ordered IDs `[seq_id, seq_id, ...]` mapping the absolute top-to-bottom layout on a drop event.

### 🔌 API Route Modifications
- `POST /update-sequence`: Ingests a JSON payload containing the unified layout hierarchy `ordered_ids`. Rebuilds the underlying data array sequence inside memory context.
- `POST /update-settings`: Ingests localized field adjustments. Dynamically queries and mutates properties (`countdown_minutes` or `master_start_time`) on the fly without refreshing the page state.

# Drag-and-Drop Web Application Architecture

This project implements a full-stack specialized race management planner interface featuring real-time client-to-server state synchronization using native web APIs and Python.

## 🛠️ System Architecture Diagram



## 📐 Key Functional Blocks

--

## 📐 Key Functional Blocks

### 1. Dynamic Asset Scanner Module (Backend Runtime)
Instead of relying on rigid, hardcoded lists inside python memory, the application features an automated folder tracking routine:
* **File System Inspection**: On boot and runtime page loads, `app.py` queries the local file system using `os.listdir()` to scan `static/flags/`.
* **Filter Layer**: The scanner extracts assets based on standard graphical extensions (`.png`, `.jpg`, `.jpeg`, `.svg`), building a structured collection of valid race signals on the fly.
* **Template Presentation**: Discovered items are wrapped into an explicit asset variable array and passed via Jinja syntax directly down into the Asset Palette layout sidebar.

### 2. Frontend State Layer & Reordering Engine (HTML5 / JavaScript)
* **Draggable Card Elements**: Structural templates in the Asset Palette utilize `draggable="true"`. The frontend script (`app.js`) catches the `ondragstart` event to bundle target metadata strings (`data-label`, `data-flag`, `data-minutes`) into the browser's data transfer layout buffer.
* **Vertical Drop Tracking Boundary**: Drop operations are restricted to vertical boundary tracking inside the Event Grid dropzone. The system processes item array indexing via sorting rules, passing an array of ordered row identifiers down to the backend runtime on every successful layout mutation.
* **Non-Blocking Synchronization**: Structural layout reordering and isolated row value modulations (such as editing countdown durations directly inside row input elements) issue asynchronous background network requests (`fetch()`) to update the server storage map without causing full-page web reloads.

### 3. Live Execution Clockwork & Countdown Engine (Upcoming Phase)
The execution layer shifts the application from a passive planner into an active automation controller:
* **Master System Clock Sync**: A background JavaScript execution script running via a strict `setInterval()` tick sequence continuously matches local system time against the user-specified `master_start_time` anchor.
* **The Daisy-Chain Cascade**: The countdown runner operates as a sequential one-dimensional array. Only one boat class row may be executing actively at a given time. As soon as an active timer runs down to exactly `00:00`, its internal status flags change, it fires a start alert, and automatically transfers execution focus to ignite the next pending row directly below it in the sequence list.
* **Tri-State Visual Mutation Layer**: Timers dynamically apply CSS layout styles corresponding to execution phases:
  * `state-pending`: Default layout styling for upcoming sequences.
  * `state-active`: Vivid, high-visibility flashing layout for currently executing classes.
  * `state-clear`: Muted style properties representing events whose starts have completed.

---

## 🔌 API Route Map

* **`GET /`**: Renders the complete dashboard view, passing the discovered image assets list along with the persistent sequence state structure stored in server memory.
* **`POST /update-sequence`**: Receives an ordered JSON payload containing array indices (`ordered_ids`). Re-indexes and matches row ordering constraints instantly in backend context.
* **`POST /update-settings`**: Intercepts localized input adjustments from the UI, updating single variables like individual class countdown durations or global master start positions.
* **`POST /execute-control`**: (Incoming) Ingests unified execution directives (`START`, `STOP`, `RESET`) from header dashboard controls to transition states across the server-client boundary.

---

## 🐍 Environment Settings & Command Logs

* **Host Machine Manager**: Anaconda (Conda Base System Path Environment)
* **Absolute Python Engine Direct Path**: `C:\Users\anton\miniconda3\python.exe`
* **Application Workspace Root Directory**: `C:\Users\anton\flagmachine\drag-drop-app`
* **Local Web Server Access Address**: `http://127.0.0.1:5000`

### Terminal Launch Sequences
```powershell
cd C:\Users\anton\flagmachine\drag-drop-app
C:\Users\anton\miniconda3\python.exe app.py

### 1. The Frontend UI (HTML5 / Native JavaScript)
* **Left-Side Library Column**: Acts as an independent repository housing predefined sailing class templates and graphic flag assets. The Race Officer populates and designs the event sequence by dragging elements out of this menu and dropping them directly into the planner grid.
* **Draggable Elements**: Items within the library container use `draggable="true"` and an `ondragstart` event listener to stream identifying strings into the browser data buffer via `ev.dataTransfer.setData()`.
* **Drop Targets**: The vertical sequence container monitors continuous positional changes via `ondragover` (where `ev.preventDefault()` is invoked to allow a drop) and processes row updates via native `ondrop` handlers.
* **State Sync**: Instead of refreshing the view, client JavaScript processes data variations instantly and sends JSON payloads down to the server context via the asynchronous `fetch()` API, ensuring real-time structural synchronization without a page reload.

### 2. The Backend Runtime (Python 3 / Flask)
* **Routing Infrastructure**: Provides endpoint triggers (`/`) for basic application page layout delivery, and accepts background tracking endpoints strictly via `POST` methods for server-side evaluation.
* **Payload Ingestion**: Uses `request.get_json()` to process arriving network data payloads and unpack them into natively manipulatable Python dictionaries.

## 🐍 Environment Data & Command Logs
To bypass path mismatches, the codebase directly references the explicit local path environment:
* **Host Environment Manager**: Anaconda / Miniconda (Conda Base Environment Context)
* **Absolute Python Runtime Path**: `C:\Users\anton\miniconda3\python.exe`
* **Network Binding Endpoint**: `http://127.0.0.1:5000`

## 🔄 Revision Addendum: Vertical Sequence Planner Pivot
The architecture has shifted from a standard multi-column Kanban layout into a specialized One-Dimensional Vertical Sequence Planner optimized for chronological event timelines.

### 📐 Structural Realignment
1. **Data State Layer**: The master dataset represents a unified object wrapping global states (`master_start_time`, `override_status`) and an indexed array of scheduled boat events. Each row tracks variables for class labels, flag asset paths, and numerical duration fields (`countdown_minutes`) independently, allowing time parameters to exist separately from the image file.
2. **Reordering Engine**: The HTML5 drag mechanism is strictly locked to vertical layout tracks. Reordering mutations pass an ordered array of primary keys `[seq_id, seq_id, ...]` matching the absolute top-to-bottom layout sequence directly into backend storage memory.

### ⏱️ The Live Countdown Engine Clockwork
* **The Master Anchor**: The frontend JavaScript loop attaches to the host computer's system time, continuously checking real-world hours against the specified `master_start_time`.
* **The Daisy-Chain Cascade**: Timers execute sequentially. When the active row countdown hits `00:00`, its execution status transitions, and it instantly fires an internal trigger to wake up and start the next class row down the list.
* **Dynamic UI Visual States**: The loop applies on-the-fly updates to row classes to modify CSS representations depending on state properties:
  * `PENDING`: Assigned to waiting items; displays a neutral, un-highlighted layout style.
  * `ACTIVE`: Assigned to the running item; triggers high-visibility flashing or color variations.
  * `CLEAR`: Assigned to completed items; shifts row formatting to a dimmed, muted style.
* **State Override Controls**: Administrative triggers (`Start`, `Override Reset`, `Override Stop`) intercept active clock loops to halt, flush, or force-start execution states dynamically.
* **Version 1 Execution Lock**: Once the master start time triggers execution, the planner enters a read-only locked state. Layout reordering or duration editing is frozen until the entire countdown sequence completes.

## 🔌 API Route Modifications
* `POST /update-sequence`: Ingests a JSON payload detailing the current structural layout hierarchy (`ordered_ids`) on a drop event, rebuilding the database array sequence in-memory.
* `POST /update-settings`: Captures field adjustments on individual row durations (`countdown_mi


