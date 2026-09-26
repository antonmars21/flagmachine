@echo off
echo ========================================
echo Finish Sheet - Session 3 Test Launch
echo ========================================
echo.

echo Step 1: Checking database tables...
python -c "import sqlite3; conn = sqlite3.connect('score.db'); c = conn.cursor(); c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"'); tables = [row[0] for row in c.fetchall()]; print('Tables found:', tables); conn.close()"

echo.
echo Step 2: Launching Flask server on http://localhost:5000
echo Open browser tabs:
echo   - Control Panel (Flag Machine): http://localhost:5000/
echo   - Finish Sheet (New): http://localhost:5000/finishsheet
echo.

python app.py
