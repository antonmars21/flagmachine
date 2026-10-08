# Flag Machine + Finish Sheet — Club Laptop Setup

A lightweight sailing race management system: Flag Machine (race countdown control panel) + Finish Sheet (sign-on, race tracking, finish recording, CSV export).

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

### 3. Launch the App
**Option A — Batch file (easiest):**
- Double-click `START.bat`

**Option B — PowerShell:**
- Right-click `START.ps1` → "Run with PowerShell"
- If you get a permissions error, open PowerShell as Administrator first

**Option C — Manual:**
```
python app.py
```
(Run in a single Command Prompt window)

### 4. Open in Browser
- **Flag Machine:** http://localhost:5000
- **Finish Sheet:** http://localhost:5000/finishsheet

---

## What You Have

### Flag Machine (Port 5000)
- Drag-and-drop race flag sequences
- **Unlimited dynamic start sequences** via "+" button (Session 5)
- Live countdown timers
- Outdoor display board
- Sequential grid timing (Start 2 begins after Start 1 completes)

### Finish Sheet (Port 5000/finishsheet)
- Fleet sign-on (registry sidebar with checkbox to mark racing today)
- **Dynamic columns** - one per start sequence from Flag Machine
- Lap counting with "+ Lap" buttons and timestamps
- Finish marking with checkboxes
- CSV export with sequence numbers and lap times
- Sailor registry sidebar with add/edit/delete functionality

---

## File Structure

```
drag-drop-app/
├── START.bat                 ← Launch on Windows (batch)
├── START.ps1                 ← Launch on Windows (PowerShell)
├── app.py                    ← Main Flask backend (Flag Machine + Finish Sheet)
├── score.db                  ← Fleet registry (SQLite)
├── check_versions.py         ← Version checking utility
├── query_db.py               ← Database inspection utility
├── requirements.txt          ← Python dependencies
├── templates/
│   ├── index.html           ← Flag Machine UI (with "+" button)
│   ├── display.html         ← Outdoor display board
│   └── finishsheet.html      ← Finish Sheet UI with registry sidebar
├── static/
│   ├── js/
│   │   ├── app.js           ← Flag Machine logic (dynamic grids)
│   │   └── finishsheet.js   ← Finish Sheet logic (sequence-aware)
│   ├── css/
│   │   ├── style.css        ← Flag Machine + shared styling
│   │   └── registry.css     ← Registry sidebar styling
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

### Port already in use (5000)
- Close other apps using port 5000
- Or manually edit `app.py` to change port (last line: `app.run(port=XXXX)`)
- Check running processes: `netstat -ano | findstr ":5000"`
- Kill process: `taskkill /PID <PID> /F`

### Database locked
- Close all browser tabs for the apps
- Restart the Flask server

### sailors not appearing in Finish Sheet
- Ensure sailors are marked "racing today" in registry sidebar
- Check class_id mappings in database (should match boat_classes.class_id)
- Verify Flag Machine has flags dropped in sequences

### CSV export not working
- Ensure a race has been started
- Check that race_id exists in races table
- Verify lap records exist for CSV lap times data

---

## Usage Tips

### Sign On Fleet (Finish Sheet)
1. Open the Sailor Registry sidebar from Finish Sheet (click "👥 Sailor Registry" button)
2. Use search box to find sailors by name, sail number, or class
3. Check the checkbox to mark sailors as "racing today"
4. Only checked sailors appear in Finish Sheet columns
5. Use Add/Edit/Delete buttons to manage sailor database

### Record Finishes and Laps (Finish Sheet)
1. **Start Race**: Click "▶ Start Race" in Finish Sheet banner
2. **Record Laps**: Click "+ Lap" button for each sailor as they complete laps
3. **Mark Finish**: Check the finish checkbox when sailor finishes
4. **End Race**: Click "⏹ End Race" when race is complete
5. **Export CSV**: Click "📥 Export CSV" for results with sequence and lap data

### Control Race Start (Flag Machine)
1. Set Master Start Time (top left) or use START button for immediate start
2. Click "+" button to add more start sequences (unlimited)
3. Drag flags into each sequence grid
4. Click START or let system time trigger automatically
5. Display board shows large flag + countdown for outdoor viewing
6. Each sequence starts only after previous sequences complete

### Multiple Start Sequences
1. Use "+" button to add Start 2, Start 3, etc.
2. Drag different class flags into each sequence
3. All sequences run in order (Start 1 → Start 2 → Start 3)
4. Finish Sheet automatically creates separate columns for each sequence

---

## Contact / Support

For issues or feature requests, check the `AgentReadme/` folder for full documentation.

---

**Version:** 1.2 (Dynamic Start Sequences)  
**Last Updated:** October 8, 2026  
**Session:** 5 Complete
