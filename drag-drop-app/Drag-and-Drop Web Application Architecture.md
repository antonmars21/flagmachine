# Drag-and-Drop Web Application Architecture

This project implements a full-stack Kanban-style interface featuring real-time client-to-server state synchronization using native web APIs and Python.

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