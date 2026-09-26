# Flag Machine + Sailor Scorer — Club Laptop Setup

A lightweight sailing race management system: Flag Machine (race countdown control panel) + Sailor Scorer (sign-on, race tracking, finish recording).

---

## Quick Start (Windows)

### 1. Install Python
- Download Python 3.11+ from [python.org](https://www.python.org/downloads/)
- During installation, **check "Add Python to PATH"**
- Verify: Open Command Prompt, type `python --version`

### 2. Install Flask
Open Command Prompt in the app folder and run:
```
pip install Flask
```

### 3. Launch the Apps
**Option A — Batch file (easiest):**
- Double-click `START.bat`

**Option B — PowerShell:**
- Right-click `START.ps1` → "Run with PowerShell"
- If you get a permissions error, open PowerShell as Administrator first

**Option C — Manual:**
```
python app.py
python score.py
```
(Run both commands in separate Command Prompt windows, or use `&` to run in background)

### 4. Open in Browser
- **Flag Machine:** http://localhost:5000
- **Sailor Scorer:** http://localhost:5001

---

## What You Have

### Flag Machine (Port 5000)
- Drag-and-drop race flag sequences
- Dual grids for multiple boat classes
- Live countdown timers
- Outdoor display board

### Sailor Scorer (Port 5001)
- Fleet sign-on (checkbox to mark racing)
- Kanban board: On Water → Finished → DNF/DQ
- Drag-and-drop to record finishes with timestamps
- CSV export (`⬇ CSV` button)
- Reset Day button to clear race data

---

## File Structure

```
drag-drop-app/
├── START.bat                 ← Launch on Windows (batch)
├── START.ps1                 ← Launch on Windows (PowerShell)
├── app.py                    ← Flag Machine backend
├── score.py                  ← Sailor Scorer backend
├── score.db                  ← Fleet registry (SQLite)
├── requirements.txt          ← Python dependencies
├── templates/
│   ├── index.html           ← Flag Machine UI
│   ├── display.html         ← Outdoor display board
│   └── score.html           ← Sailor Scorer UI
├── static/
│   ├── js/
│   │   ├── app.js           ← Flag Machine logic
│   │   └── score.js         ← Sailor Scorer logic
│   ├── css/
│   │   ├── style.css        ← Flag Machine styling
│   │   └── score.css        ← Sailor Scorer styling
│   └── flags/               ← Flag images
└── AgentReadme/             ← Documentation
```

---

## Troubleshooting

### "Python not found"
- Ensure Python is in PATH: `python --version` from Command Prompt
- If not, reinstall Python with "Add Python to PATH" checked

### "ModuleNotFoundError: No module named 'flask'"
```
pip install Flask
```

### Port already in use (5000 or 5001)
- Close other apps using those ports
- Or manually edit `app.py` and `score.py` to change ports (last line: `app.run(port=XXXX)`)

### Database locked
- Close all browser tabs for the apps
- Restart the Flask servers

---

## Usage Tips

### Sign On Fleet (Sailor Scorer)
1. Fleet list on left sidebar (search by name, sail number, or class)
2. Green checkboxes mark "Racing Today"
3. Signed-on sailors appear at bottom of list (unsigned at top)

### Record Finishes
1. Drag sailor tile from "On Water" → "Finished"
2. Finish time auto-stamped (`HH:MM:SS`)
3. Reorder within "Finished" to correct places
4. Drag to red "DNF" or teal "DQ" zone for penalties
5. CSV export when done

### Control Race Start (Flag Machine)
1. Set Master Start Time (top left)
2. Drag flags into sequence grid
3. Click START or let system time trigger automatically
4. Display board shows large flag + countdown for outdoor viewing

---

## Contact / Support

For issues or feature requests, check the `AgentReadme/` folder for full documentation.

---

**Version:** 1.0  
**Last Updated:** July 2026
