import io

path = 'app.py'
src = io.open(path, encoding='utf-8', newline='').read()
NL = '\r\n'

# --- 1. Add race_open_starts table to init_db ---
old = (
"        FOREIGN KEY(race_id) REFERENCES races(race_id)," + NL +
"        FOREIGN KEY(class_id) REFERENCES boat_classes(class_id)," + NL +
"        UNIQUE(race_id, class_id)" + NL +
"    )''')"
)
new = (
"        FOREIGN KEY(race_id) REFERENCES races(race_id)," + NL +
"        FOREIGN KEY(class_id) REFERENCES boat_classes(class_id)," + NL +
"        UNIQUE(race_id, class_id)" + NL +
"    )''')" + NL +
"    " + NL +
"    # Open Category start per race (race_class_starts.class_id is NOT NULL," + NL +
"    # so the open fleet's start lives in its own table)" + NL +
"    c.execute('''CREATE TABLE IF NOT EXISTS race_open_starts (" + NL +
"        id INTEGER PRIMARY KEY AUTOINCREMENT," + NL +
"        race_id INTEGER NOT NULL UNIQUE," + NL +
"        start_time TEXT NOT NULL," + NL +
"        sequence_number INTEGER DEFAULT 1," + NL +
"        source TEXT DEFAULT 'flag_machine'," + NL +
"        FOREIGN KEY(race_id) REFERENCES races(race_id)" + NL +
"    )''')"
)
assert src.count(old) == 1, f"schema anchor: {src.count(old)}"
src = src.replace(old, new)

# --- 2. class-start open branch: persist into race_open_starts (LF endings: inserted by edit tool) ---
old = (
"                        app_state['open_start_time'] = datetime.now().isoformat()\n" +
"                        # Persist the open start (class_id NULL = Open Category)\n" +
"                        # so CSV exports keep the open fleet's start time\n" +
"                        c.execute('''\n" +
"                            INSERT INTO race_class_starts (race_id, class_id, start_time, sequence_number, source)\n" +
"                            VALUES (?, NULL, ?, ?, 'flag_machine')\n" +
"                        ''', (race_id, app_state['open_start_time'], sequence_number))"
)
new = (
"                        app_state['open_start_time'] = datetime.now().isoformat()\n" +
"                        # Persist the open start so CSV exports keep the open\n" +
"                        # fleet's start time (UNIQUE(race_id) -> idempotent)\n" +
"                        c.execute('''\n" +
"                            INSERT OR IGNORE INTO race_open_starts (race_id, start_time, sequence_number)\n" +
"                            VALUES (?, ?, ?)\n" +
"                        ''', (race_id, app_state['open_start_time'], sequence_number))"
)
assert src.count(old) == 1, f"open branch anchor: {src.count(old)}"
src = src.replace(old, new)

# --- 3. export: read the open start from race_open_starts (LF: inserted by edit tool) ---
old = (
"    c.execute('''SELECT start_time, sequence_number FROM race_class_starts\n" +
"                 WHERE race_id = ? AND class_id IS NULL ORDER BY start_time LIMIT 1''', (race_id,))"
)
new = (
"    c.execute('''SELECT start_time, sequence_number FROM race_open_starts\n" +
"                 WHERE race_id = ? ORDER BY start_time LIMIT 1''', (race_id,))"
)
assert src.count(old) == 1, f"export open anchor: {src.count(old)}"
src = src.replace(old, new)

io.open(path, 'w', encoding='utf-8', newline='').write(src)
print('app.py patched OK')
