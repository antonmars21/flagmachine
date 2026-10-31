"""
Session 4: Finish Sheet v1.1 - Race Officer Control + Sailor Tracking
Runs on localhost:5000 with Flag Machine and Finish Sheet integrated
"""
import os
import re
import json
import sqlite3
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Serializes race auto-creation and roster locking: simultaneous class-start
# POSTs (multi-flag start event) must not each create their own race (bug 21).
RACE_STATE_LOCK = threading.Lock()

# ==================== TEST RECORDING (bug reproduction) ====================
# Records the API calls produced by UI button clicks so a race-day session can
# be replayed instantly (scripts/replay_race.py) without waiting for countdowns.
# Toggle from the browser:
#   start: http://localhost:5000/api/test/record?action=start
#   stop:  http://localhost:5000/api/test/record?action=stop
RECORDING_DIR = os.path.join(os.path.dirname(__file__), 'tempref')
RECORDING_PATH = os.path.join(RECORDING_DIR, 'recording.jsonl')
RECORD_NOISE = {
    '/api/display-state', '/api/race-status', '/api/get-elapsed-time',
    '/api/sailors-registry', '/api/sailors-for-onwater',
    '/api/refresh-sailwave-status', '/api/test/record',
    '/update-status', '/update-live-timer',  # 100ms countdown pollers
}
recording_state = {'active': False}
recording_lock = threading.Lock()

@app.before_request
def _capture_request():
    """Grab the raw request body while it's still readable (for recording)."""
    if recording_state['active'] and request.path not in RECORD_NOISE \
            and not request.path.startswith('/static'):
        request._record_body = request.get_data(as_text=True)
    return None

@app.after_request
def _log_recorded_request(response):
    """Append each captured request to the recording as one JSON line."""
    if recording_state['active'] and getattr(request, '_record_body', None) is not None:
        try:
            with recording_lock:  # dev server is threaded - serialize appends
                with open(RECORDING_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        't': datetime.now().isoformat(),
                        'method': request.method,
                        'path': request.path,
                        'body': request._record_body,
                        'status': response.status_code,
                    }) + '\n')
        except OSError:
            pass
    return response

@app.route('/api/test/record')
def test_record_toggle():
    """Start/stop recording of UI API calls (for instant replay later)."""
    action = request.args.get('action', 'status')
    if action == 'start':
        os.makedirs(RECORDING_DIR, exist_ok=True)
        with open(RECORDING_PATH, 'w', encoding='utf-8') as f:
            pass  # truncate for a fresh recording
        recording_state['active'] = True
        return jsonify({"status": "recording", "path": RECORDING_PATH})
    if action == 'stop':
        recording_state['active'] = False
        return jsonify({"status": "stopped", "path": RECORDING_PATH})
    return jsonify({
        "status": "recording" if recording_state['active'] else "idle",
        "path": RECORDING_PATH,
    })

DB_PATH = 'score.db'
FLAGS_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'flags')
# Flags are split into classflags/ and signalflags/ (2026-10-16) so a preparatory
# signal flag (p.png, blue peter) can never be confused with a boat class flag
# (pclass.png, P Class). The flat folder is honoured as a legacy fallback so an
# old extract without the subfolders keeps working.
CLASS_FLAGS_SUBDIR = 'classflags'
SIGNAL_FLAGS_SUBDIR = 'signalflags'
FLAG_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.svg')

def _scan_flag_folders():
    """Return {group: [bare filenames]} for every flag image on disk.
    Groups: 'class' and 'signal' when the split folders exist; with no
    subfolders (legacy layout) all flat files report as 'class'."""
    groups = {}
    for sub, group in ((CLASS_FLAGS_SUBDIR, 'class'), (SIGNAL_FLAGS_SUBDIR, 'signal')):
        path = os.path.join(FLAGS_FOLDER, sub)
        if os.path.isdir(path):
            files = [f for f in os.listdir(path)
                     if f.lower().endswith(FLAG_EXTENSIONS)
                     and os.path.isfile(os.path.join(path, f))]
            if files:
                groups[group] = files
    if not groups and os.path.isdir(FLAGS_FOLDER):
        flat = [f for f in os.listdir(FLAGS_FOLDER)
                if f.lower().endswith(FLAG_EXTENSIONS)
                and os.path.isfile(os.path.join(FLAGS_FOLDER, f))]
        if flat:
            groups['class'] = flat
    return groups

def flag_url(filename):
    """Resolve a bare flag filename to its URL: classflags/ then signalflags/
    subfolder, else the legacy flat path. Bare filenames stay in the DB and
    the start sequence, so class matching and recorded sessions are unaffected."""
    if not filename:
        return None
    for sub in (CLASS_FLAGS_SUBDIR, SIGNAL_FLAGS_SUBDIR):
        if os.path.exists(os.path.join(FLAGS_FOLDER, sub, filename)):
            return f'/static/flags/{sub}/{filename}'
    return f'/static/flags/{filename}'
SAILWAVE_DB_FOLDER = r'C:\Users\Public\Documents\Sailwave\Flagmachine_database'

# ==================== RACE CALENDAR (regatta/series naming) ====================

CALENDAR_MONTHS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                   'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
# A calendar row counts as racing when one of these appears in the event name
CALENDAR_RACING_WORDS = ('racing', 'regatt', 'series', 'points race', 'mark foy',
                         'club sailing', 'club race')
# ... unless one of these does (training, coaching, admin, social)
CALENDAR_EXCLUDE_WORDS = ('coaching', 'learn to sail', 'lts', 'training', 'meeting',
                          'committee', 'open day', 'working bee', 'rigging',
                          'planning', 'first aid', 'optisail', 'school holiday',
                          'no sailing', 'no hyc', 'info session', 'muster',
                          'powerboat', 'end of term', 'icebreaker', 'refresher')


def find_calendar_file():
    """Locate the HYC race calendar workbook (HYC Calendar*.xlsx): first in
    the Sailwave database folder, then in the app folder (the calendar ships
    with the app - bug 29: the Dell had no calendar in its Sailwave folder,
    so every export silently fell back to race_<id>_results.csv with an
    empty Series column)."""
    for folder in (SAILWAVE_DB_FOLDER, os.path.dirname(os.path.abspath(__file__))):
        try:
            files = [f for f in os.listdir(folder)
                     if f.lower().startswith('hyc calendar') and f.lower().endswith('.xlsx')]
        except OSError:
            continue
        if files:
            return os.path.join(folder, sorted(files)[0])
    return None


def _xlsx_rows(xlsx_path):
    """Yield (date_text, time_text, event) per worksheet row. Stdlib-only
    xlsx reader (zip + XML) so no extra dependency is needed."""
    import zipfile
    import xml.etree.ElementTree as ET
    M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(xlsx_path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall(f'{{{M}}}si'):
                shared.append(''.join(t.text or '' for t in si.iter(f'{{{M}}}t')))
        sheets = sorted(n for n in z.namelist()
                        if re.match(r'xl/worksheets/sheet[0-9]+[.]xml', n))
        if not sheets:
            return []
        root = ET.fromstring(z.read(sheets[0]))
        rows = []
        for row in root.iter(f'{{{M}}}row'):
            vals = []
            for c in row.findall(f'{{{M}}}c'):
                v = c.find(f'{{{M}}}v')
                val = v.text if v is not None else ''
                if c.get('t') == 's' and val != '':
                    val = shared[int(val)]
                vals.append(val or '')
            while len(vals) < 3:
                vals.append('')
            rows.append(vals[:3])
        return rows


def _parse_calendar_date(text):
    """'Wed 14 Oct 26' -> date(2026, 10, 14). Date ranges ('Mon 25 - Fri 29
    Jan 27') and TBC rows return None - they are never club racing events."""
    if not text:
        return None
    m = re.match(r'^(?:Mon|Tues|Wed|Thurs|Fri|Sat|Sun)[a-z]*\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{2})$',
                 text.strip())
    if not m:
        return None
    mon = m.group(2)[:3].lower()
    if mon not in CALENDAR_MONTHS:
        return None
    try:
        return datetime(2000 + int(m.group(3)), CALENDAR_MONTHS[mon], int(m.group(1))).date()
    except ValueError:
        return None


def _parse_calendar_time(val):
    """Calendar time cell -> (hour, minute). Excel stores times of day as a
    fraction of 24h (0.75 = 18:00); text cells look like '16:30-19:30'.
    Returns None when there is no usable time."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        frac = float(s)
        if 0 < frac < 1:
            mins = round(frac * 24 * 60)
            return (mins // 60) % 24, mins % 60
    except ValueError:
        pass
    m = re.match(r'(\d{1,2}):(\d{2})', s)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _calendar_events_by_date(calendar_path=None):
    """date -> event name for EVERY racing date in the calendar. Same rules
    as the single-date lookup: non-racing rows are skipped, and the latest
    start-time row of a day wins (Wednesday rule: the 18:00 Twilight row
    beats any earlier row of the same day). One xlsx parse for all dates,
    so series race numbering can look up every race with one read."""
    path = calendar_path or find_calendar_file()
    if not path or not os.path.exists(path):
        return {}
    events = {}
    current_date = None  # empty date cells inherit the previous row's date
    for date_text, time_text, event in _xlsx_rows(path):
        d = _parse_calendar_date(date_text)
        if d:
            current_date = d
        ev = (event or '').strip()
        if not ev or not current_date:
            continue
        low = ev.lower()
        if any(w in low for w in CALENDAR_EXCLUDE_WORDS):
            continue
        if not any(w in low for w in CALENDAR_RACING_WORDS):
            continue
        t = _parse_calendar_time(time_text)
        prev = events.get(current_date)
        # latest start time wins (None = no usable time, always loses)
        if prev is None or (t is not None and (prev[1] is None or t > prev[1])):
            events[current_date] = (ev, t)
    return {d: ev for d, (ev, t) in events.items()}


def get_calendar_event_for_date(target_date, calendar_path=None):
    """Return the regatta/series name for a date from the HYC race calendar,
    or None when the calendar/file/date has no racing event.

    Wednesday rule (agreed with the RO): only the Twilight race (from 6pm)
    is picked, never the earlier training/coaching session - the latest
    start time wins, so the 18:00 Twilight row beats any earlier row of
    the same day."""
    return _calendar_events_by_date(calendar_path).get(target_date)


def _race_date(race_id):
    """The calendar-matching date of a race: its earliest recorded start
    (class or open), falling back to today."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT MIN(start_time) FROM (
                     SELECT MIN(start_time) AS start_time FROM race_class_starts WHERE race_id = ?
                     UNION ALL
                     SELECT MIN(start_time) AS start_time FROM race_open_starts WHERE race_id = ?
                 )''', (race_id, race_id))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        try:
            return datetime.fromisoformat(row[0]).date()
        except ValueError:
            pass
    return datetime.now().date()


def _race_ordinal_of_day(race_id, race_date):
    """1-based position of this race among the day's started races (by
    earliest recorded start), so multi-race days (e.g. the three Saturday
    races) get distinct export filenames - R2, R3... after the first."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT r.race_id AS rid, MIN(s.start_time) AS st
        FROM races r
        JOIN (
            SELECT race_id, start_time FROM race_class_starts
            UNION ALL
            SELECT race_id, start_time FROM race_open_starts
        ) s ON s.race_id = r.race_id
        GROUP BY r.race_id
    ''')
    same_day = []
    for row in c.fetchall():
        if not row['st']:
            continue
        try:
            if datetime.fromisoformat(row['st']).date() == race_date:
                same_day.append(row['rid'])
        except ValueError:
            continue
    conn.close()
    same_day.sort()
    try:
        return same_day.index(race_id) + 1
    except ValueError:
        return 1


def _series_race_number(race_id):
    """Sailwave race number of this race WITHIN its series: incremental
    across the whole series (e.g. Twilight Series runs R1, R2, R3... every
    Wednesday over the weeks), NOT per day. Every started race whose date
    maps to the same calendar series counts, ordered by earliest recorded
    start - so numbers stay stable as new races are added. Returns None
    when the race's date has no calendar series."""
    events = _calendar_events_by_date()
    race_date = _race_date(race_id)
    series = events.get(race_date)
    if not series:
        return None
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT r.race_id AS rid, MIN(s.start_time) AS st
        FROM races r
        JOIN (
            SELECT race_id, start_time FROM race_class_starts
            UNION ALL
            SELECT race_id, start_time FROM race_open_starts
        ) s ON s.race_id = r.race_id
        GROUP BY r.race_id
    ''')
    same_series = []
    for row in c.fetchall():
        if not row['st']:
            continue
        try:
            d = datetime.fromisoformat(row['st']).date()
        except ValueError:
            continue
        if events.get(d) == series:
            same_series.append((row['st'], row['rid']))
    conn.close()
    same_series.sort()
    for number, (_, rid) in enumerate(same_series, 1):
        if rid == race_id:
            return number
    return None


def _export_filename(event_name, race_id, race_date, ordinal=1):
    """CSV filename named by regatta/series + matched date (feature 6).
    The suffix is the race's number within the series (R2, R3...) - or the
    race-of-day number when the date has no calendar series - so the day's
    races never overwrite each other in the downloads folder."""
    if event_name:
        safe = re.sub(r'[<>:"/\\|?*]', '', event_name).strip()
        safe = re.sub(r'\s+', ' ', safe)
        suffix = f' R{ordinal}' if ordinal > 1 else ''
        return f'{safe}{suffix} {race_date.strftime("%d-%m-%Y")}.csv'
    return f'race_{race_id}_results.csv'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_finishsheet_tables():
    """Initialize finish sheet database tables."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS boat_classes (
        class_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name   TEXT UNIQUE NOT NULL,
        flag_image   TEXT,
        color_hex    TEXT DEFAULT '#0369a1',
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS races (
        race_id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time TEXT,
        end_time TEXT,
        status TEXT DEFAULT 'READY',
        class_groups TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Backward-compat: add end_time column if races table pre-existed without it
    c.execute("PRAGMA table_info(races)")
    race_columns = [col[1] for col in c.fetchall()]
    if 'end_time' not in race_columns:
        c.execute('ALTER TABLE races ADD COLUMN end_time TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sailors (
        uid TEXT PRIMARY KEY,
        sailor_name TEXT,
        short_name TEXT,
        sail_no TEXT UNIQUE,
        boat_class TEXT,
        handicap REAL,
        seed INTEGER,
        class_id INTEGER,
        FOREIGN KEY(class_id) REFERENCES boat_classes(class_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS race_sailors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_id INTEGER,
        uid TEXT,
        lap_count INTEGER DEFAULT 0,
        finish_time TEXT,
        placement INTEGER,
        FOREIGN KEY(race_id) REFERENCES races(race_id),
        FOREIGN KEY(uid) REFERENCES sailors(uid)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS lap_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_id INTEGER,
        uid TEXT,
        lap_number INTEGER,
        timestamp TEXT,
        FOREIGN KEY(race_id) REFERENCES races(race_id),
        FOREIGN KEY(uid) REFERENCES sailors(uid)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS race_class_starts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        sequence_number INTEGER DEFAULT 1,
        source TEXT DEFAULT 'flag_machine',
        FOREIGN KEY(race_id) REFERENCES races(race_id),
        FOREIGN KEY(class_id) REFERENCES boat_classes(class_id),
        UNIQUE(race_id, class_id)
    )''')
    
    # Open Category start per race (race_class_starts.class_id is NOT NULL,
    # so the open fleet's start lives in its own table)
    c.execute('''CREATE TABLE IF NOT EXISTS race_open_starts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_id INTEGER NOT NULL UNIQUE,
        start_time TEXT NOT NULL,
        sequence_number INTEGER DEFAULT 1,
        source TEXT DEFAULT 'flag_machine',
        FOREIGN KEY(race_id) REFERENCES races(race_id)
    )''')
    
    # Class-to-station assignments for the multi-station finish sheet (feature 4).
    # class_key: 'c<class_id>' for a class column, 'open' for Open Category.
    # Server-truth, kept for the whole day (across races) until toggled again.
    c.execute('''CREATE TABLE IF NOT EXISTS class_station_assignments (
        class_key TEXT PRIMARY KEY,
        station INTEGER NOT NULL,
        updated_at TEXT
    )''')
    
    # Per-station capture log for the Step Back feature (feature 4): every
    # lap/finish is logged with the station that captured it, so each screen
    # reverses only its own most recent action. Nothing is hard-deleted -
    # undone actions stay in the log so Restore can re-apply them with the
    # ORIGINAL timestamp.
    c.execute('''CREATE TABLE IF NOT EXISTS capture_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_id INTEGER NOT NULL,
        uid TEXT NOT NULL,
        action TEXT NOT NULL,
        station INTEGER,
        timestamp TEXT NOT NULL,
        lap_number INTEGER,
        ref_id INTEGER,
        undone INTEGER DEFAULT 0,
        undone_at TEXT,
        FOREIGN KEY(race_id) REFERENCES races(race_id),
        FOREIGN KEY(uid) REFERENCES sailors(uid)
    )''')
    
    # Backward-compat: add sequence_number column if it doesn't exist
    c.execute("PRAGMA table_info(race_class_starts)")
    race_class_columns = [col[1] for col in c.fetchall()]
    if 'sequence_number' not in race_class_columns:
        c.execute('ALTER TABLE race_class_starts ADD COLUMN sequence_number INTEGER DEFAULT 1')
    
    conn.commit()
    conn.close()

init_finishsheet_tables()

def reconcile_sailor_class_ids():
    """Re-sync sailors.class_id with boat_classes, matched by boat_class name
    (case-insensitive). Fixes stale class_id values (e.g. left behind by an
    older Sailwave import) that would otherwise place sailors in the wrong
    finish-sheet class column. Sailors whose boat_class has no matching
    boat class get class_id NULL, which groups them into the Open Category.
    Idempotent - only updates rows where class_id currently disagrees."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE sailors
        SET class_id = (
            SELECT bc.class_id FROM boat_classes bc
            WHERE LOWER(bc.class_name) = LOWER(sailors.boat_class)
        )
        WHERE class_id IS NOT (
            SELECT bc.class_id FROM boat_classes bc
            WHERE LOWER(bc.class_name) = LOWER(sailors.boat_class)
        )
    ''')
    fixed = c.rowcount
    conn.commit()
    conn.close()
    if fixed:
        print(f"[registry] Reconciled class_id for {fixed} sailor(s)")

reconcile_sailor_class_ids()

# Some classes are known by a different flag filename than their class name
FLAG_NAME_ALIASES = {
    '37': 'farr3point7.png',  # '3.7' class -> Farr 3.7 flag
}

def reconcile_class_flag_images():
    """Scan the CLASS flag folder at startup and repair boat_classes.flag_image.
    For each boat class whose flag_image is NULL or does not exactly match
    a file in the flags folder, try to find an image whose name matches the
    class name (normalized: lowercase, ignore spaces/punctuation).
    Classes with no matching image keep flag_image NULL - their sailors
    group into the Open Category until a flag is added."""
    # Only class flags are scanned (plus the legacy flat folder): signal
    # flags (p.png, Dflag, ...) must never attach to a boat class.
    files = _scan_flag_folders().get('class', [])
    if not files:
        return

    def norm(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())

    files_by_norm = {norm(os.path.splitext(f)[0]): f for f in files}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT class_id, class_name, flag_image FROM boat_classes')
    fixed = 0
    for row in c.fetchall():
        fi = row['flag_image']
        if fi and fi in files:
            continue  # current flag exists on disk - leave it alone
        key = norm(row['class_name'])
        match = files_by_norm.get(key) or FLAG_NAME_ALIASES.get(key)
        if match:
            c.execute('UPDATE boat_classes SET flag_image = ? WHERE class_id = ?',
                      (match, row['class_id']))
            fixed += 1
            print(f"[flags] {row['class_name']}: flag_image -> {match}")
    conn.commit()
    conn.close()
    if fixed:
        print(f"[flags] Repaired flag images for {fixed} class(es)")


def find_class_flag_image(class_name):
    """Best-match CLASS flag image for a class name, or None. Only the class
    flag folder is considered (signal flags can never attach to a boat
    class), and openclass.png can never be a boat class flag - Open Category
    is a virtual column, not a class."""
    files = _scan_flag_folders().get('class', [])

    def norm(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())

    files_by_norm = {norm(os.path.splitext(f)[0]): f for f in files}
    key = norm(class_name)
    match = files_by_norm.get(key) or FLAG_NAME_ALIASES.get(key)
    if match and norm(os.path.splitext(match)[0]) == 'openclass':
        return None
    return match


def ensure_boat_class_id(c, class_name):
    """Look up a boat class by name (case-insensitive) on an open cursor,
    creating it when missing (with its class flag when one exists on disk).
    add/edit-sailor use this so a manually added class never strands its
    sailors in Open Category (bugs 33/34: 'Ilca 4' sailors had class_id NULL
    because no boat_classes row existed)."""
    class_name = (class_name or '').strip()
    if not class_name:
        return None
    row = c.execute('SELECT class_id FROM boat_classes WHERE LOWER(class_name) = LOWER(?)',
                    (class_name,)).fetchone()
    if row:
        return row['class_id']
    flag_image = find_class_flag_image(class_name)
    c.execute('INSERT INTO boat_classes (class_name, flag_image, color_hex) VALUES (?, ?, ?)',
              (class_name, flag_image, '#0369a1'))
    print(f"[classes] created '{class_name}' (flag: {flag_image or 'none'})")
    return c.lastrowid


def repair_missing_boat_classes():
    """Create boat_classes rows for sailor boat_class values that have none
    (bugs 33/34). Manually added sailors (add/edit sailor on the sheet) and
    tidied rosters can reference classes that were never created, so the RO
    can drag the class flag (e.g. ilca4.png) into a start event and it
    matches NO class - no column is created and the sailors' class_id stays
    NULL, grouping them into Open Category. Every distinct sailor boat_class
    gets a class row (flag image auto-matched from the class flag folder)
    and the sailors are linked to it. Classes with no flag image keep their
    sailors in Open Category, which is correct: no flag = no start."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT boat_class FROM sailors "
              "WHERE boat_class IS NOT NULL AND TRIM(boat_class) <> ''")
    names = [r['boat_class'].strip() for r in c.fetchall()]
    created = 0
    linked = 0
    for name in names:
        row = c.execute('SELECT class_id FROM boat_classes WHERE LOWER(class_name) = LOWER(?)',
                        (name,)).fetchone()
        if row:
            class_id = row['class_id']
        else:
            flag_image = find_class_flag_image(name)
            c.execute('INSERT INTO boat_classes (class_name, flag_image, color_hex) '
                      'VALUES (?, ?, ?)', (name, flag_image, '#0369a1'))
            class_id = c.lastrowid
            created += 1
            print(f"[classes] created '{name}' (flag: {flag_image or 'none'})")
        linked += c.execute(
            'UPDATE sailors SET class_id = ? '
            'WHERE class_id IS NULL AND LOWER(boat_class) = LOWER(?)',
            (class_id, name)).rowcount
    conn.commit()
    conn.close()
    if created or linked:
        print(f"[classes] repair: {created} class(es) created, {linked} sailor(s) linked")


reconcile_class_flag_images()
repair_missing_boat_classes()

def get_dynamic_asset_library():
    """Flag library for the RO picker: CLASS FLAGS first, then SIGNAL FLAGS,
    so the class/signal split is visible on screen (no P vs P-Class
    confusion). Each asset carries the bare filename (flag_image - used for
    all class matching and recorded sessions) plus its resolved flag_url."""
    assets = []
    for group in ('class', 'signal'):
        for filename in _scan_flag_folders().get(group, []):
            base_name, _ = os.path.splitext(filename)
            clean_label = base_name.replace('_', ' ').replace('-', ' ').title()
            # RO hotfix 2026-10-16: every row in a start event defaults to 1 minute
            default_minutes = 1
            assets.append({
                "label": clean_label,
                "flag_image": filename,
                "flag_url": flag_url(filename),
                "group": group,
                "default_minutes": default_minutes
            })
    return assets

app_state = {
    "master_start_time": "11:30",
    "status": "READY",
    "race_duration": "00:00:00",
    "active_grid": None,
    "sequence": [],
    "display_mode": "flags",
    "race_id": None,
    "race_start_timestamp": None,
    "class_start_times": {},
    "open_start_time": None,
    "race_ended": False,
    "race_end_timestamp": None,
    # Bug 31: when the RO pressed Start (epoch ms) so a reloaded RO page can
    # RESUME the countdown instead of resetting it; None = no countdown running
    "fm_countdown_started_ms": None,
    "sheet_version": 1
}

def _end_race_internal():
    """Shared logic: stop all timers, record end_time on the race, freeze state.
    Called from both Flag Machine's End Race button and Finish Sheet's End Race button.
    Idempotent - safe to call multiple times.
    """
    race_id = app_state.get('race_id')
    if not race_id or app_state.get('race_ended'):
        return
    
    now_iso = datetime.now().isoformat()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE races SET end_time = ?, status = ? WHERE race_id = ?', (now_iso, 'ENDED', race_id))
    conn.commit()
    conn.close()
    
    app_state['race_ended'] = True
    app_state['race_end_timestamp'] = now_iso

def get_active_class_ids_from_sequence():
    """Return the set of class_ids whose flag_image appears anywhere in the
    current Flag Machine Start Sequence (any grid). Case-insensitive match.
    """
    flag_images = set()
    for item in app_state.get('sequence', []):
        # Match ALL flags in the start event: primary + secondary + tertiary
        # (multiple classes can share one start, e.g. Ilca 6 + Ilca 7)
        for fi in (item.get('flag_image'), item.get('secondary_flag_image'), item.get('tertiary_flag_image')):
            if fi:
                flag_images.add(fi)
    if not flag_images:
        return set()
    
    conn = get_db_connection()
    c = conn.cursor()
    ids = set()
    for fi in flag_images:
        c.execute('SELECT class_id FROM boat_classes WHERE LOWER(flag_image) = LOWER(?)', (fi,))
        row = c.fetchone()
        if row:
            ids.add(row['class_id'])
    conn.close()
    return ids


def get_class_sequence_mapping():
    """Return a dict mapping class_id to sequence_number based on current Flag Machine sequence.
    For classes in the current sequence, use their grid_index as sequence_number.
    For classes that have already started (in race_class_starts), use their stored sequence_number.
    """
    mapping = {}
    
    # First, get sequence numbers from race_class_starts for classes that have already started
    race_id = app_state.get('race_id')
    if race_id:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT class_id, sequence_number FROM race_class_starts WHERE race_id = ?', (race_id,))
        for row in c.fetchall():
            if row['class_id'] is not None:
                mapping[row['class_id']] = row['sequence_number']
        conn.close()
    
    # Then, get sequence numbers from current Flag Machine sequence for classes that haven't started
    conn = get_db_connection()
    c = conn.cursor()
    for item in app_state.get('sequence', []):
        grid_index = item.get('grid_index', 1)
        # Match ALL flags in the start event: primary + secondary + tertiary
        for flag_image in (item.get('flag_image'), item.get('secondary_flag_image'), item.get('tertiary_flag_image')):
            if not flag_image:
                continue
            c.execute('SELECT class_id FROM boat_classes WHERE LOWER(flag_image) = LOWER(?)', (flag_image,))
            row = c.fetchone()
            if row and row['class_id'] not in mapping:  # Don't override already-started classes
                mapping[row['class_id']] = grid_index
    conn.close()
    
    return mapping

OPEN_FLAG_NAMES = {'openclass'}


def open_flag_in_sequence():
    """True if an open-class flag (openclass.*) appears in the current Flag
    Machine sequence (primary or secondary slot). When present, the RO
    controls when the Open Category starts: it activates when that start
    event fires. Without an open flag, the Open Category activates with the
    race's first start."""
    for item in app_state.get('sequence', []):
        for fi in (item.get('flag_image'), item.get('secondary_flag_image'), item.get('tertiary_flag_image')):
            if fi:
                base = os.path.splitext(os.path.basename(fi))[0].lower()
                if base in OPEN_FLAG_NAMES:
                    return True
    return False


def open_class_started():
    """Whether Open Category sailors may record laps/finishes yet."""
    if app_state.get('open_start_time'):
        return True
    if open_flag_in_sequence():
        return False
    return bool(app_state.get('race_id'))


def _race_last_activity(c, race_id):
    """Latest recorded activity time (local ISO) for a race: class starts,
    open start, laps. Used to tell a mid-race restart (minutes old, adopt it)
    from an abandoned crash (hours/days old, close it)."""
    latest = None
    c.execute('''SELECT MAX(start_time) AS t FROM race_class_starts WHERE race_id = ?''', (race_id,))
    row = c.fetchone()
    if row and row['t']:
        latest = row['t']
    c.execute('SELECT MAX(start_time) AS t FROM race_open_starts WHERE race_id = ?', (race_id,))
    row = c.fetchone()
    if row and row['t'] and (latest is None or row['t'] > latest):
        latest = row['t']
    c.execute('SELECT MAX(timestamp) AS t FROM lap_records WHERE race_id = ?', (race_id,))
    row = c.fetchone()
    if row and row['t'] and (latest is None or row['t'] > latest):
        latest = row['t']
    return latest


def recover_running_race(max_age_hours=12):
    """Bug 27: race state (race_id, class_start_times, open_start_time) is
    memory-only, so a mid-race server restart orphaned the RUNNING race -
    the finish sheet's manual Start Race then created a DUPLICATE race (24
    Oct: race 67 kept RUNNING while race 68 was started and ended), and the
    real race could never be ended or exported. Called at app start only
    (never at import - regression scripts swap DB_PATH after importing):
    - A RUNNING race with activity in the last max_age_hours is ADOPTED back
      into app_state, so End Race / laps / export all target the live race.
    - Older RUNNING races were abandoned by a crash (nobody pressed End
      Race) and are closed as ENDED so they stop blocking the new session.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT race_id FROM races WHERE status = 'RUNNING' ORDER BY race_id")
        running = [row['race_id'] for row in c.fetchall()]
        if not running:
            return None
        now = datetime.now()
        adopted = None
        for race_id in running:  # newest first
            last = _race_last_activity(c, race_id)
            try:
                age_hours = ((now - datetime.fromisoformat(last)).total_seconds() / 3600
                             if last else 999)
            except ValueError:
                age_hours = 999
            if age_hours > max_age_hours:
                # Abandoned mid-race crash: close it at its last activity time
                # (frozen, like a normal End Race) instead of dragging a stale
                # race into the new session.
                c.execute('UPDATE races SET end_time = ?, status = ? WHERE race_id = ?',
                          (last or now.isoformat(), 'ENDED', race_id))
                conn.commit()
                print(f"[race {race_id}] RUNNING but stale ({age_hours:.1f}h old) - "
                      f"marked ENDED (bug 27 recovery)")
                continue
            # Recent race: adopt it back into memory so the sheet keeps
            # scoring the SAME race after the restart.
            c.execute('''SELECT class_id, start_time FROM race_class_starts
                         WHERE race_id = ?''', (race_id,))
            class_start_times = {str(row['class_id']): row['start_time']
                                for row in c.fetchall() if row['class_id'] is not None}
            c.execute('''SELECT start_time FROM race_open_starts
                         WHERE race_id = ? ORDER BY start_time LIMIT 1''', (race_id,))
            orow = c.fetchone()
            app_state['race_id'] = race_id
            app_state['race_start_timestamp'] = (
                class_start_times and min(class_start_times.values())
                or (orow['start_time'] if orow else None)
                or now.isoformat())
            app_state['class_start_times'] = class_start_times
            app_state['open_start_time'] = orow['start_time'] if orow else None
            app_state['race_ended'] = False
            app_state['race_end_timestamp'] = None
            app_state['status'] = 'RUNNING'
            adopted = race_id
            print(f"[race {race_id}] RUNNING race recovered after restart "
                  f"(bug 27) - laps/finishes/export continue this race")
        return adopted
    finally:
        conn.close()


# ==================== FLAG MACHINE ROUTES ====================

@app.route('/')
def index():
    assets = get_dynamic_asset_library()
    flag_url_map = {a['flag_image']: a['flag_url'] for a in assets}
    return render_template(
        'index.html', state=app_state,
        class_assets=[a for a in assets if a['group'] == 'class'],
        signal_assets=[a for a in assets if a['group'] == 'signal'],
        flag_url_map=flag_url_map)

@app.route('/update-sequence', methods=['POST'])
def update_sequence():
    payload = request.get_json()
    if payload and 'sequence' in payload:
        app_state['sequence'] = payload['sequence']
        return jsonify({"status": "success", "sequence": app_state['sequence']})
    return jsonify({"status": "error"}), 400

@app.route('/update-settings', methods=['POST'])
def update_settings():
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "message": "No payload provided"}), 400
    if 'master_start_time' in payload:
        app_state['master_start_time'] = payload['master_start_time']
        return jsonify({"status": "success", "updated": "master_start_time"})
    if 'card_id' in payload and 'countdown_minutes' in payload:
        card_id = payload['card_id']
        try:
            mins = int(payload['countdown_minutes'])
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid duration value"}), 400
        for item in app_state["sequence"]:
            if item["id"] == card_id:
                item["countdown_minutes"] = mins
                return jsonify({"status": "success", "updated": f"card_{card_id}_duration"})
        return jsonify({"status": "error", "message": "Card not found"}), 404
    return jsonify({"status": "error", "message": "Unknown adjustment target"}), 400

@app.route('/update-status', methods=['POST'])
def update_status():
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error"}), 400
    if 'status' in payload and 'active_id' not in payload:
        app_state['status'] = payload['status']
        return jsonify({"status": "success", "global_status": app_state['status']})
    if 'active_id' in payload:
        active_id = payload['active_id']
        grid_index = payload.get('grid_index')
        app_state['active_grid'] = grid_index
        for item in app_state['sequence']:
            item['status'] = "ACTIVE" if item['id'] == active_id else "PENDING"
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/execute-control', methods=['POST'])
def execute_control():
    payload = request.get_json()
    if not payload or 'action' not in payload:
        return jsonify({"status": "error", "message": "Missing action directive"}), 400
    action = payload['action']
    if action == 'START':
        app_state['status'] = 'RUNNING'
        app_state['race_duration'] = '00:00:00'
        # Bug 31: remember when the countdown started (epoch ms, sent by the
        # RO page) so a reloaded/navigated-back RO page resumes the clock
        app_state['fm_countdown_started_ms'] = payload.get('countdown_started_ms')
    elif action == 'STOP':
        app_state['status'] = 'PAUSED'
        # Pause keeps the page's own timing; a later Start restarts the
        # countdown from zero (unchanged behaviour), so nothing to resume
        app_state['fm_countdown_started_ms'] = None
    elif action == 'RESET':
        app_state['status'] = 'READY'
        app_state['race_duration'] = '00:00:00'
        app_state['fm_countdown_started_ms'] = None
    elif action == 'END_RACE':
        app_state['status'] = 'ENDED'
        if 'duration' in payload:
            app_state['race_duration'] = payload['duration']
        app_state['fm_countdown_started_ms'] = None
        _end_race_internal()
    return jsonify({"status": "success", "current_state": app_state['status'], "race_duration": app_state['race_duration']})

@app.route('/set-display-mode', methods=['POST'])
def set_display_mode():
    payload = request.get_json()
    mode = payload.get('mode')
    if mode in ['flags', 'both', 'number']:
        app_state['display_mode'] = mode
        return jsonify({"status": "success", "display_mode": mode})
    return jsonify({"status": "error", "message": "Invalid mode"}), 400

@app.route('/display')
def outdoor_display():
    return render_template('display.html')

@app.route('/api/display-state')
def display_state():
    active_event = None
    for item in app_state.get('sequence', []):
        if item.get('status') == 'ACTIVE':
            active_event = item
            break
    display_mode = app_state.get('display_mode', 'flags')
    if active_event:
        grid_index = app_state.get('active_grid') or active_event.get('grid_index') or 1
        grid_name = f"Event Grid {grid_index}"
        return jsonify({
            "status": "RUNNING",
            "grid_name": grid_name,
            "flag_image": active_event.get('flag_image'),
            "secondary_flag_image": active_event.get('secondary_flag_image'),
            "flag_url": flag_url(active_event.get('flag_image')),
            "secondary_flag_url": flag_url(active_event.get('secondary_flag_image')),
            "live_timer": active_event.get('current_live_timer', '--:--'),
            "display_mode": display_mode
        })
    else:
        return jsonify({
            "status": "STANDBY", 
            "grid_name": "STANDBY", 
            "flag_image": "", 
            "secondary_flag_image": None,
            "flag_url": "",
            "secondary_flag_url": None,
            "live_timer": "--:--",
            "display_mode": display_mode
        })

@app.route('/update-live-timer', methods=['POST'])
def update_live_timer():
    payload = request.get_json()
    if payload and 'live_timer' in payload:
        for item in app_state.get('sequence', []):
            if item.get('status') == 'ACTIVE':
                item['current_live_timer'] = payload['live_timer']
                break
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

# ==================== FINISH SHEET ROUTES ====================

@app.route('/finishsheet')
def finishsheet():
    """Render finish sheet UI for race officer scoring. The station number
    (?station=1|2, default 1) is passed to the template for the tab title;
    the JS reads the same URL parameter for the station identity."""
    station = request.args.get('station', type=int)
    if station not in (1, 2):
        station = 1
    return render_template('finishsheet.html', station=station)

def column_class_key(col):
    """Stable key for station assignment: 'c<class_id>' for a class
    column, 'open' for the Open Category column."""
    return 'open' if col.get('class_id') is None else 'c{}'.format(col['class_id'])

def get_station_assignments(ordered_columns):
    """Class->station map for the CURRENT sheet (server truth).
    Stored assignments (kept for the day, across races) win; columns with
    no stored assignment default by sheet position: the first 3 columns
    go to station 1, the remainder to station 2. Open Category counts as
    a normal (trailing) column, so it defaults to station 2 whenever
    3+ columns are on the sheet."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT class_key, station FROM class_station_assignments')
    stored = {row['class_key']: row['station'] for row in c.fetchall()}
    conn.close()
    assignments = {}
    for idx, col in enumerate(ordered_columns):
        key = column_class_key(col)
        assignments[key] = stored.get(key, 1 if idx < 3 else 2)
    return assignments

@app.route('/api/sailors-for-onwater')
def sailors_for_onwater():
    """Get sailors for the Finish Sheet, grouped into DYNAMIC columns:
    - One column per boat class currently in the Flag Machine Start Sequence,
      ordered by sailor count descending (most sailors on the left).
    - Sailors whose class is NOT in the current sequence are bucketed into
      a trailing 'Open Category' column.
    - Only sailors marked 'racing_today' (via the registry sidebar) are included.
    - For classes that HAVE started, the roster is locked to whoever was
      signed on at that class's start moment (race_sailors). For classes that
      have NOT yet started, the list stays LIVE - reflecting registry checkbox
      changes in real time, even if a race has already been auto-created by
      another class starting.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    race_id = app_state.get('race_id')
    active_class_ids = get_active_class_ids_from_sequence()
    class_start_times = app_state.get('class_start_times', {})
    started_class_ids = {int(cid) for cid in class_start_times.keys()}
    
    # Get sequence number mapping for grouping classes by start sequence
    class_sequence_mapping = get_class_sequence_mapping()
    open_started = open_class_started()
    
    if race_id and started_class_ids:
        # Started classes: locked roster from race_sailors (whoever was signed on at start time)
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed, s.handicap,
                   rs.lap_count, rs.finish_time, rs.placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex,
                   rcs.sequence_number
            FROM sailors s
            JOIN race_sailors rs ON s.uid = rs.uid
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            LEFT JOIN race_class_starts rcs ON rcs.race_id = rs.race_id AND rcs.class_id = s.class_id
            WHERE rs.race_id = ? AND s.class_id IN ({})
            ORDER BY s.boat_class, s.seed
        '''.format(','.join('?' * len(started_class_ids))), (race_id, *started_class_ids))
        started_rows = c.fetchall()
    else:
        started_rows = []
    
    # Not-yet-started classes: LIVE from registry (racing_today), regardless of race_id.
    # Also includes sailors who signed on AFTER their class started (late sign-ons,
    # e.g. returning after boat repairs): their class is started but they are not in
    # the locked roster (race_sailors) yet, so they stay live until first lap/finish.
    # Bug 28: live rows must carry the REAL lap_count/finish_time from race_sailors
    # once the sailor has joined the roster (open-category sailors and late sign-ons
    # are ONLY ever served by this query - the started-classes query filters on
    # s.class_id, which is NULL for open sailors). A hardcoded 0 reset the on-sheet
    # lap counter on every poll/refresh, so scorers re-clicked and recorded
    # duplicate laps seconds apart (24 Oct: Gabrielle Marais, Europe/Open).
    if started_class_ids:
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed, s.handicap,
                   COALESCE(rs.lap_count, 0) as lap_count, rs.finish_time, rs.placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex,
                   NULL as sequence_number
            FROM sailors s
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            LEFT JOIN race_sailors rs ON rs.race_id = ? AND rs.uid = s.uid
            WHERE s.racing_today = 1
              AND (s.class_id IS NULL
                   OR s.class_id NOT IN ({})
                   OR s.uid NOT IN (SELECT uid FROM race_sailors WHERE race_id = ?))
            ORDER BY s.boat_class, s.seed
        '''.format(','.join('?' * len(started_class_ids))), (race_id, *started_class_ids, race_id))
    else:
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed, s.handicap,
                   COALESCE(rs.lap_count, 0) as lap_count, rs.finish_time, rs.placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex,
                   NULL as sequence_number
            FROM sailors s
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            LEFT JOIN race_sailors rs ON rs.race_id = ? AND rs.uid = s.uid
            WHERE s.racing_today = 1
            ORDER BY s.boat_class, s.seed
        ''', (race_id,))
    live_rows = c.fetchall()

    # Last lap timestamp per sailor for this race (tie-break for on-water ordering)
    last_lap_times = {}
    if race_id:
        c.execute('''
            SELECT uid, lap_number, timestamp FROM lap_records
            WHERE race_id = ? ORDER BY uid, lap_number
        ''', (race_id,))
        for lap_row in c.fetchall():
            last_lap_times[lap_row['uid']] = lap_row['timestamp']

    conn.close()
    
    rows = list(started_rows) + list(live_rows)
    
    sequence_groups = {}
    open_category_sailors = []
    
    # First, create empty groups for all classes in the current Flag Machine sequence
    # This ensures columns appear even for classes with no sailors.
    # Primary, secondary and tertiary flags all create a column (shared start).
    for item in app_state.get('sequence', []):
        grid_index = item.get('grid_index', 1)
        for flag_image in (item.get('flag_image'), item.get('secondary_flag_image'), item.get('tertiary_flag_image')):
            if not flag_image:
                continue
            conn_temp = get_db_connection()
            c_temp = conn_temp.cursor()
            c_temp.execute('SELECT class_id, class_name, flag_image, color_hex FROM boat_classes WHERE LOWER(flag_image) = LOWER(?)', (flag_image,))
            class_row = c_temp.fetchone()
            if class_row:
                class_id = class_row['class_id']
                group_key = (class_id, grid_index)
                if group_key not in sequence_groups:
                    sequence_groups[group_key] = {
                        'class_id': class_id,
                        'class_name': class_row['class_name'],
                        'flag_image': class_row['flag_image'],
                        'color_hex': class_row['color_hex'],
                        'sequence_number': grid_index,
                        'sailors': []
                    }
            conn_temp.close()
    
    for row in rows:
        class_id = row['class_id']
        start_time = class_start_times.get(str(class_id)) if class_id is not None else None
        sailor_dict = {
            'uid': row['uid'],
            'sail_no': row['sail_no'],
            'short_name': row['short_name'],
            'boat_class': row['boat_class'],
            'seed': row['seed'],
            'handicap': row['handicap'],
            'last_lap_time': last_lap_times.get(row['uid']),
            'lap_count': row['lap_count'],
            'finish_time': row['finish_time'],
            'placement': row['placement'],
            'class_id': class_id,
            'flag_image': row['flag_image'],
            'color_hex': row['color_hex'],
            'class_started': start_time is not None,
            'class_start_time': start_time,
            'open_category': False
        }
        
        # Get sequence number for this class
        sequence_number = row['sequence_number'] if row['sequence_number'] is not None else class_sequence_mapping.get(class_id, 1)
        
        # Add sequence_number to sailor dict
        sailor_dict['sequence_number'] = sequence_number
        
        # Determine if this sailor should be in a class column or open category
        # If class_id is None, always go to open category
        if class_id is None:
            sailor_dict['open_category'] = True
            sailor_dict['class_started'] = open_started
            open_category_sailors.append(sailor_dict)
        # If there are active classes in the sequence, only include classes that are in the sequence
        elif active_class_ids and class_id in active_class_ids:
            # Group by class + sequence for sequence-aware display
            group_key = (class_id, sequence_number)
            if group_key not in sequence_groups:
                sequence_groups[group_key] = {
                    'class_id': class_id,
                    'class_name': row['class_name'],
                    'flag_image': row['flag_image'],
                    'color_hex': row['color_hex'],
                    'sequence_number': sequence_number,
                    'sailors': []
                }
            sequence_groups[group_key]['sailors'].append(sailor_dict)
        # If no active classes in sequence (empty sequence), show all classes grouped by class only
        elif not active_class_ids:
            # When no flags in sequence, group by class only (original behavior)
            group_key = (class_id, 1)  # Use sequence 1 for all
            if group_key not in sequence_groups:
                sequence_groups[group_key] = {
                    'class_id': class_id,
                    'class_name': row['class_name'],
                    'flag_image': row['flag_image'],
                    'color_hex': row['color_hex'],
                    'sequence_number': 1,
                    'sailors': []
                }
            sequence_groups[group_key]['sailors'].append(sailor_dict)
        else:
            # Class exists but not in current sequence - goes to open category
            sailor_dict['open_category'] = True
            sailor_dict['class_started'] = open_started
            open_category_sailors.append(sailor_dict)
    
    # Order sequence-class columns: by sequence number first, then by sailor count (most on left within same sequence)
    ordered_columns = sorted(sequence_groups.values(), key=lambda g: (g.get('sequence_number', 1), -len(g['sailors'])))
    
    if open_category_sailors:
        ordered_columns.append({
            'class_id': None,
            'class_name': 'Open Category',
            'flag_image': 'openclass.png',
            'color_hex': '#64748b',
            'sequence_number': 0,  # Open category has no sequence
            'sailors': open_category_sailors
        })
    
    # Multi-station finish sheet (feature 4): assign every column to a
    # station (stored toggle assignments win; default = first 3 columns
    # to station 1, remainder to station 2). A ?station=1/2 request
    # returns only that station's columns; without the parameter all
    # columns are returned (station=None).
    assignments = get_station_assignments(ordered_columns)
    for col in ordered_columns:
        col['class_key'] = column_class_key(col)
        col['station'] = assignments[col['class_key']]
    
    station = request.args.get('station', type=int)
    if station in (1, 2):
        ordered_columns = [col for col in ordered_columns if col['station'] == station]
    
    return jsonify({
        "status": "success",
        "columns": ordered_columns,
        "station": station,
        "assignments": assignments
    })

@app.route('/api/assign-class-station', methods=['POST'])
def assign_class_station():
    """Move a class column to the other station (finish-sheet column
    header toggle). Server-truth and kept for the whole day, across
    races, until toggled again. Bumping assignments_version makes every
    station's 500ms poller re-render its columns sub-second."""
    payload = request.get_json() or {}
    class_key = payload.get('class_key')
    try:
        station = int(payload.get('station'))
    except (TypeError, ValueError):
        station = 0
    if not class_key or station not in (1, 2):
        return jsonify({"status": "error",
                        "message": "class_key and station (1 or 2) required"}), 400
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO class_station_assignments (class_key, station, updated_at)
                 VALUES (?, ?, ?)
                 ON CONFLICT(class_key) DO UPDATE
                 SET station = excluded.station, updated_at = excluded.updated_at''',
              (class_key, station, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    # Bump the sheet version so every station's poller re-renders.
    app_state['sheet_version'] = app_state.get('sheet_version', 1) + 1
    return jsonify({"status": "success", "class_key": class_key, "station": station})

@app.route('/api/sailors-registry')
def sailors_registry():
    """Return the full sailor fleet with racing_today flag for the registry sidebar."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT uid, sailor_name, short_name, sail_no, boat_class, handicap, seed, racing_today
        FROM sailors
        ORDER BY racing_today ASC, boat_class ASC, short_name ASC
    ''')
    rows = c.fetchall()
    conn.close()
    
    sailors = [dict(row) for row in rows]
    return jsonify({"status": "success", "sailors": sailors})

@app.route('/api/toggle-racing', methods=['POST'])
def toggle_racing():
    """Mark/unmark a sailor as racing today (registry checkbox)."""
    payload = request.get_json() or {}
    uid = payload.get('uid')
    racing_today = 1 if payload.get('racing_today') else 0
    
    if not uid:
        return jsonify({"status": "error", "message": "uid required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE sailors SET racing_today = ? WHERE uid = ?', (racing_today, uid))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/add-sailor', methods=['POST'])
def add_sailor():
    """Add a new sailor to the registry. UID is optional - auto-generated as
    SL-<sail_no> (Sailwave convention), suffixed -2/-3... if already taken."""
    payload = request.get_json() or {}
    uid = (payload.get('uid') or '').strip()
    sailor_name = (payload.get('sailor_name') or '').strip()
    short_name = (payload.get('short_name') or '').strip()
    sail_no = (payload.get('sail_no') or '').strip()
    boat_class = (payload.get('boat_class') or '').strip()
    handicap = payload.get('handicap', 1.0)
    seed = payload.get('seed', 0)
    
    if not sailor_name or not sail_no:
        return jsonify({"status": "error", "message": "Sailor Name and Sail No are required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # A duplicate sail number means the sailor is almost certainly already
    # registered (sail_no is UNIQUE). Point the RO at the existing row instead
    # of creating a confusing duplicate.
    c.execute('SELECT uid, short_name FROM sailors WHERE sail_no = ?', (sail_no,))
    dup_sail = c.fetchone()
    if dup_sail:
        conn.close()
        return jsonify({"status": "error",
                        "message": f"Sail number {sail_no} is already in the registry "
                                   f"({dup_sail['short_name']}, UID {dup_sail['uid']}). Sign them on "
                                   f"from the list instead of adding again - clear the search box "
                                   f"if you cannot see them."}), 400
    
    if uid:
        c.execute('SELECT short_name FROM sailors WHERE uid = ?', (uid,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error",
                            "message": f"UID '{uid}' already exists. Leave the UID box blank "
                                       f"and one will be chosen automatically."}), 400
    else:
        base = f'SL-{sail_no}'
        uid = base
        n = 2
        while c.execute('SELECT 1 FROM sailors WHERE uid = ?', (uid,)).fetchone():
            uid = f'{base}-{n}'
            n += 1
    
    try:
        # Get-or-create the class (bugs 33/34): a class typed here that does
        # not exist yet is created immediately with its class flag, so the
        # sailor can never be stranded classless in Open Category.
        class_id = ensure_boat_class_id(c, boat_class) if boat_class else None

        c.execute('''
            INSERT INTO sailors (uid, sailor_name, short_name, sail_no, boat_class, handicap, seed, class_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uid, sailor_name, short_name, sail_no, boat_class, float(handicap or 1.0), int(seed or 0), class_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": f"A sailor with UID '{uid}' already exists"}), 400

@app.route('/api/edit-sailor/<uid>', methods=['PUT'])
def edit_sailor(uid):
    """Edit an existing sailor's details."""
    payload = request.get_json() or {}
    sailor_name = (payload.get('sailor_name') or '').strip()
    short_name = (payload.get('short_name') or '').strip()
    sail_no = (payload.get('sail_no') or '').strip()
    boat_class = (payload.get('boat_class') or '').strip()
    handicap = payload.get('handicap', 1.0)
    seed = payload.get('seed', 0)
    
    if not sailor_name or not short_name or not sail_no or not boat_class:
        return jsonify({"status": "error", "message": "All fields required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    # Get-or-create the class (bugs 33/34) - see add_sailor
    class_id = ensure_boat_class_id(c, boat_class)

    c.execute('''
        UPDATE sailors
        SET sailor_name=?, short_name=?, sail_no=?, boat_class=?, handicap=?, seed=?, class_id=?
        WHERE uid=?
    ''', (sailor_name, short_name, sail_no, boat_class, float(handicap or 1.0), int(seed or 0), class_id, uid))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/delete-sailor/<uid>', methods=['DELETE'])
def delete_sailor(uid):
    """Remove a sailor from the registry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM sailors WHERE uid=?', (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/start-race', methods=['POST'])
def start_race():
    """Manual backup: Start a new race with selected sailors, starting ALL classes immediately."""
    conn = get_db_connection()
    c = conn.cursor()
    
    payload = request.get_json()
    selected_sailors = payload.get('selected_sailors', [])
    
    try:
        # Create race record if none active (locked - bug 21)
        with RACE_STATE_LOCK:
            race_id = app_state.get('race_id')
            if not race_id:
                c.execute('INSERT INTO races (status) VALUES (?)', ('RUNNING',))
                conn.commit()
                race_id = c.lastrowid
                app_state['race_id'] = race_id
                app_state['race_start_timestamp'] = datetime.now().isoformat()
        
        # If no explicit selection passed, default to all sailors marked racing_today
        if not selected_sailors:
            c.execute('SELECT uid FROM sailors WHERE racing_today = 1')
            selected_sailors = [r['uid'] for r in c.fetchall()]
        
        # Add sailors to race (skip if already present)
        for uid in selected_sailors:
            c.execute('''
                SELECT id FROM race_sailors WHERE race_id = ? AND uid = ?
            ''', (race_id, uid))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO race_sailors (race_id, uid, lap_count, placement)
                    VALUES (?, ?, 0, NULL)
                ''', (race_id, uid))
        conn.commit()
        
        # Manual backup override: start ALL boat classes immediately
        now_iso = datetime.now().isoformat()
        c.execute('SELECT class_id FROM boat_classes')
        all_class_ids = [row['class_id'] for row in c.fetchall()]
        
        for class_id in all_class_ids:
            c.execute('''
                INSERT OR IGNORE INTO race_class_starts (race_id, class_id, start_time, source)
                VALUES (?, ?, ?, 'manual_backup')
            ''', (race_id, class_id, now_iso))
            # Only set in-memory value if not already started (don't clobber earlier flag-machine start)
            if str(class_id) not in app_state['class_start_times']:
                c.execute('''
                    SELECT start_time FROM race_class_starts WHERE race_id = ? AND class_id = ?
                ''', (race_id, class_id))
                app_state['class_start_times'][str(class_id)] = c.fetchone()['start_time']

        # Manual backup starts the Open Category immediately too
        if not app_state.get('open_start_time'):
            app_state['open_start_time'] = now_iso
        
        # Bug 4: a race is RUNNING no matter which page started it - the
        # manual backup is a full start of every class, so the shared
        # control state (fm_status in /api/race-status) must say RUNNING,
        # keeping every page's start/end/reset buttons in sync.
        app_state['status'] = 'RUNNING'
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "race_id": race_id})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/class-start', methods=['POST'])
def class_start():
    """Called by the Flag Machine when a start event (grid) countdown FULLY
    completes - i.e. after the last sub-timer of the flag sequence. Accepts
    flag_image (single flag, backward compatible) or flag_images (all flags
    of the start event). Each flag that matches a boat class records that
    class's start; openclass.* records the Open Category start; signal flags
    with no boat class behind them (p.png, Dflag, postpone...) are ignored.
    Auto-creates the race if none is active - under a lock, so simultaneous
    starts never create two races (bug 21).
    """
    payload = request.get_json() or {}
    sequence_number = payload.get('sequence_number', 1)

    # Bug 31: the RO page may reload mid-countdown; catching up on rows that
    # completed while it was away, it sends the TRUE crossing time so late
    # class starts are recorded accurately. Only accept the past (a
    # future/garbage value falls back to now).
    start_iso = datetime.now().isoformat()
    try:
        started_ms = int(payload.get('started_at_ms'))
        if 0 < started_ms <= time.time() * 1000 + 5000:
            start_iso = datetime.fromtimestamp(started_ms / 1000).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        pass

    flags = payload.get('flag_images')
    if not flags and payload.get('flag_image'):
        flags = [payload['flag_image']]
    # Dedupe, preserve order, drop empties
    flags = [f for f in dict.fromkeys(flags) if f] if flags else []

    if not flags:
        return jsonify({"status": "error", "message": "flag_image required"}), 400

    conn = get_db_connection()
    c = conn.cursor()
    results = []
    try:
        with RACE_STATE_LOCK:
            # Auto-create race if none active (locked - bug 21)
            race_id = app_state.get('race_id')
            if not race_id:
                c.execute('INSERT INTO races (status) VALUES (?)', ('RUNNING',))
                conn.commit()
                race_id = c.lastrowid
                app_state['race_id'] = race_id
                app_state['race_start_timestamp'] = datetime.now().isoformat()

            for flag_image in flags:
                # Open-class flag: no boat class behind it - the Open Category
                # starts when this start event fires. First trigger wins.
                flag_base = os.path.splitext(os.path.basename(flag_image))[0].lower()
                if flag_base in OPEN_FLAG_NAMES:
                    if not app_state.get('open_start_time'):
                        app_state['open_start_time'] = start_iso
                        # Persist the open start so CSV exports keep the open
                        # fleet's start time (UNIQUE(race_id) -> idempotent)
                        c.execute('''
                            INSERT OR IGNORE INTO race_open_starts (race_id, start_time, sequence_number)
                            VALUES (?, ?, ?)
                        ''', (race_id, app_state['open_start_time'], sequence_number))
                    results.append({
                        "flag_image": flag_image,
                        "open_start": True,
                        "start_time": app_state['open_start_time']
                    })
                    continue

                # Look up boat class by flag_image (case-insensitive)
                c.execute('SELECT class_id, class_name FROM boat_classes WHERE LOWER(flag_image) = LOWER(?)', (flag_image,))
                row = c.fetchone()
                if not row:
                    # Signal flag (preparatory, D flag, postpone...) - not a class start
                    results.append({"flag_image": flag_image, "skipped": True})
                    continue

                class_id = row['class_id']
                class_name = row['class_name']

                # Lock in the roster ONLY for this class's sailors who are
                # racing_today right now (late sign-ons stay live - bug 14)
                c.execute('SELECT uid FROM sailors WHERE racing_today = 1 AND class_id = ?', (class_id,))
                class_uids = [r['uid'] for r in c.fetchall()]
                for uid in class_uids:
                    c.execute('SELECT id FROM race_sailors WHERE race_id = ? AND uid = ?', (race_id, uid))
                    if not c.fetchone():
                        c.execute('''
                            INSERT INTO race_sailors (race_id, uid, lap_count, placement)
                            VALUES (?, ?, 0, NULL)
                        ''', (race_id, uid))

                # Record class start time (idempotent - first trigger wins;
                # bug 31: backdated to the true crossing when catching up
                # after a reload)
                now_iso = start_iso
                c.execute('''
                    INSERT OR IGNORE INTO race_class_starts (race_id, class_id, start_time, sequence_number, source)
                    VALUES (?, ?, ?, ?, 'flag_machine')
                ''', (race_id, class_id, now_iso, sequence_number))
                c.execute('''
                    SELECT start_time FROM race_class_starts WHERE race_id = ? AND class_id = ?
                ''', (race_id, class_id))
                actual_start = c.fetchone()['start_time']
                app_state['class_start_times'][str(class_id)] = actual_start

                results.append({
                    "class_id": class_id,
                    "class_name": class_name,
                    "start_time": actual_start
                })

            conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

    conn.close()
    return jsonify({
        "status": "success",
        "race_id": app_state.get('race_id'),
        "open_start": any(r.get('open_start') for r in results),
        "starts": results
    })


@app.route('/api/race-status')
def race_status():
    """Return current race/class-start status for Finish Sheet polling."""
    return jsonify({
        "status": "success",
        "race_id": app_state.get('race_id'),
        "race_start_timestamp": app_state.get('race_start_timestamp'),
        "class_start_times": app_state.get('class_start_times', {}),
        "open_started": open_class_started(),
        "open_start_time": app_state.get('open_start_time'),
        "open_flag_in_sequence": open_flag_in_sequence(),
        "race_ended": app_state.get('race_ended', False),
        "race_end_timestamp": app_state.get('race_end_timestamp'),
        "fm_status": app_state.get('status'),
        "fm_countdown_started_ms": app_state.get('fm_countdown_started_ms'),
        "sheet_version": app_state.get('sheet_version', 1)
    })


@app.route('/api/race-calendar-event')
def race_calendar_event():
    """Regatta/series name for a date from the HYC race calendar (feature 6).
    ?date=YYYY-MM-DD (default today). Used to name the Sailwave results export;
    also handy in the browser to sanity-check the calendar lookup."""
    date_param = request.args.get('date')
    target = None
    if date_param:
        try:
            target = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"status": "error",
                            "message": "date must be YYYY-MM-DD"}), 400
    if target is None:
        target = datetime.now().date()
    event = get_calendar_event_for_date(target)
    return jsonify({
        "status": "success" if event else "not_found",
        "date": target.isoformat(),
        "event": event,
        "calendar_file": find_calendar_file()
    })

@app.route('/api/lap-times/<uid>')
def get_lap_times(uid):
    """Get lap times for a specific sailor in the current race."""
    race_id = app_state.get('race_id')
    if not race_id:
        return jsonify({"status": "error", "message": "No active race"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT lap_number, timestamp 
        FROM lap_records 
        WHERE race_id = ? AND uid = ? 
        ORDER BY lap_number
    ''', (race_id, uid))
    
    lap_records = c.fetchall()
    conn.close()
    
    lap_times = [{'lap_number': row['lap_number'], 'timestamp': row['timestamp']} for row in lap_records]
    
    return jsonify({"status": "success", "uid": uid, "lap_times": lap_times})

@app.route('/api/end-race', methods=['POST'])
def end_race():
    """Stop all timers and record the race's end time. Idempotent."""
    if not app_state.get('race_id'):
        return jsonify({"status": "error", "message": "No active race"}), 400
    
    _end_race_internal()
    app_state['status'] = 'ENDED'
    
    return jsonify({
        "status": "success",
        "race_id": app_state.get('race_id'),
        "race_end_timestamp": app_state.get('race_end_timestamp')
    })

@app.route('/api/reset-race', methods=['POST'])
def reset_race():
    """Fully reset race state - clears race_id, class_start_times, end flags.
    This is the only action that actually zeroes the elapsed/duration timers.
    """
    app_state['race_id'] = None
    app_state['race_start_timestamp'] = None
    app_state['class_start_times'] = {}
    app_state['open_start_time'] = None
    app_state['race_ended'] = False
    app_state['race_end_timestamp'] = None
    app_state['status'] = 'READY'
    app_state['race_duration'] = '00:00:00'
    return jsonify({"status": "success"})


@app.route('/api/clear-registry', methods=['POST'])
def clear_registry():
    """Clear all racing_today flags for all sailors."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE sailors SET racing_today = 0")
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "All checkboxes cleared"})

@app.route('/api/reset-finish-sheet', methods=['POST'])
def reset_finish_sheet():
    """Reset the finish sheet for the next race of the day (bug 22).
    Clears the race state so the sheet is READY again. Recorded results
    (laps, finishes, race history) are kept in the database, and the Flag
    Machine sequence is never touched (Q3 decision). Requires the race to
    be ended first."""
    if app_state.get('race_id') and not app_state.get('race_ended'):
        return jsonify({
            "status": "error",
            "message": "Race is still running - end the race before resetting the finish sheet"
        }), 400
    app_state['race_id'] = None
    app_state['race_start_timestamp'] = None
    app_state['class_start_times'] = {}
    app_state['open_start_time'] = None
    app_state['race_ended'] = False
    app_state['race_end_timestamp'] = None
    app_state['status'] = 'READY'
    return jsonify({"status": "success", "message": "Finish sheet reset - ready for the next race"})


@app.route('/api/export-race-csv')
def export_race_csv():
    """Export current/last race as CSV for DIRECT SAILWAVE IMPORT (features
    6+7). Column names follow the Sailwave competitor-list conventions the
    club already uses (Fleet, Class, SailNo, HelmName, Handicap - as in
    Boats_master.htm) plus result columns (Race, StartTime, FinishTime,
    Elapsed, Laps). The filename is named by the regatta/series matched from
    the HYC race calendar by the race date (Wednesdays: the Twilight race
    only, from 6pm); without a calendar match it falls back to
    race_<id>_results.csv. ?format=detailed keeps the legacy human-readable
    layout for the club's own record keeping."""
    import csv
    import io
    from flask import Response
    
    race_id = app_state.get('race_id')
    if not race_id:
        return jsonify({"status": "error", "message": "No race to export"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT s.uid, bc.class_name, s.boat_class, s.sail_no, s.short_name,
               s.sailor_name, s.handicap,
               rcs.start_time as class_start_time,
               rs.lap_count, rs.finish_time,
               r.end_time as race_end_time,
               rcs.sequence_number
        FROM race_sailors rs
        JOIN sailors s ON rs.uid = s.uid
        LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
        LEFT JOIN race_class_starts rcs ON rcs.race_id = rs.race_id AND rcs.class_id = s.class_id
        JOIN races r ON r.race_id = rs.race_id
        WHERE rs.race_id = ?
        ORDER BY rcs.sequence_number, bc.class_name, s.sail_no
    ''', (race_id,))
    rows = c.fetchall()
    
    # Get lap times for all sailors in this race
    # Open-category sailors have no class start row - their start is the open
    # start (class_id NULL in race_class_starts), or the race's first start
    # when no open flag was used
    c.execute('''SELECT start_time, sequence_number FROM race_open_starts
                 WHERE race_id = ? ORDER BY start_time LIMIT 1''', (race_id,))
    open_start = c.fetchone()
    if not open_start:
        c.execute('''SELECT start_time, sequence_number FROM race_class_starts
                     WHERE race_id = ? ORDER BY start_time LIMIT 1''', (race_id,))
        open_start = c.fetchone()
    c.execute('SELECT uid, lap_number, timestamp FROM lap_records WHERE race_id = ? ORDER BY uid, lap_number', (race_id,))
    lap_records = c.fetchall()
    conn.close()
    
    # Organize lap times by uid
    lap_times_by_uid = {}
    for lr in lap_records:
        uid = lr['uid']
        if uid not in lap_times_by_uid:
            lap_times_by_uid[uid] = []
        lap_times_by_uid[uid].append(lr['timestamp'])
    
    def fmt_elapsed(finish_iso, start_iso):
        """Elapsed sail time as mm:ss.s (club convention, e.g. '32:56.3')."""
        if not finish_iso or not start_iso:
            return ''
        try:
            secs = (datetime.fromisoformat(finish_iso) - datetime.fromisoformat(start_iso)).total_seconds()
        except ValueError:
            return ''
        if secs < 0:
            secs = 0
        return f'{int(secs) // 60:02d}:{secs % 60:04.1f}'

    def fmt_clock(iso):
        """Lap/capture timestamps as a 24h clock (HH:MM:SS) for the
        human-readable sheet - raw ISO strings with microseconds are hard
        to read for the scorers."""
        try:
            return datetime.fromisoformat(iso).strftime('%H:%M:%S')
        except (ValueError, TypeError):
            return iso or ''
    
    race_date = _race_date(race_id)
    regatta = get_calendar_event_for_date(race_date)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if request.args.get('format') == 'detailed':
        # Legacy human-readable layout (club record keeping)
        writer.writerow(['Series', 'Sequence', 'Class', 'Sailor', 'Sail No', 'Start Time', 'Laps', 'Lap Times', 'Finish Time', 'Race End Time'])
        for row in rows:
            uid = row['uid']
            lap_times = lap_times_by_uid.get(uid, [])
            lap_times_str = '; '.join(fmt_clock(t) for t in lap_times) if lap_times else ''
            writer.writerow([
                regatta or '',
                row['sequence_number'] if row['sequence_number'] is not None else ((open_start['sequence_number'] if open_start else '') or ''),
                row['class_name'] or 'Unknown',
                row['short_name'],
                row['sail_no'],
                row['class_start_time'] or (open_start['start_time'] if open_start else ''),
                row['lap_count'],
                lap_times_str,
                row['finish_time'] or '',
                row['race_end_time'] or ''
            ])
        filename = f"race_{race_id}_results.csv"
    else:
        # Sailwave import format (feature 7). Series = the calendar-matched
        # series/regatta name (blank when the race date has no calendar
        # event); Race = the stable race identifier; LapTimes = the 24h
        # clock of every recorded lap.
        writer.writerow(['Fleet', 'Class', 'SailNo', 'HelmName', 'Handicap',
                         'Series', 'Race', 'StartTime', 'FinishTime', 'Elapsed',
                         'Laps', 'LapTimes'])
        series_name = regatta or ''
        # Sailwave race number: incremental WITHIN the series across the
        # whole season (Twilight Series runs R1, R2... every Wednesday),
        # not the DB race id. Without a calendar series the race-of-day
        # number keeps same-day exports distinguishable.
        race_number = _series_race_number(race_id) or _race_ordinal_of_day(race_id, race_date)
        race_label = f'Race {race_number}'
        for row in rows:
            uid = row['uid']
            start = row['class_start_time'] or (open_start['start_time'] if open_start else '')
            fleet = row['class_name'] or row['boat_class'] or 'Open'
            lap_times = '; '.join(fmt_clock(t) for t in lap_times_by_uid.get(uid, []))
            writer.writerow([
                fleet,
                fleet,
                row['sail_no'],
                row['sailor_name'] or row['short_name'],
                row['handicap'] if row['handicap'] is not None else '',
                series_name,
                race_label,
                start,
                row['finish_time'] or '',
                fmt_elapsed(row['finish_time'], start),
                row['lap_count'],
                lap_times
            ])
        filename = _export_filename(regatta, race_id, race_date, race_number)
    
    csv_data = output.getvalue()
    
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/api/record-lap', methods=['POST'])
def record_lap():
    """Increment lap counter for a sailor. Requires sailor's class to have started."""
    conn = get_db_connection()
    c = conn.cursor()
    
    payload = request.get_json()
    race_id = app_state.get('race_id')
    uid = payload.get('uid')
    # Station that captured this (feature 4) - logged for per-screen Step Back
    try:
        station = int(payload.get('station'))
    except (TypeError, ValueError):
        station = None
    
    if not race_id or not uid:
        conn.close()
        return jsonify({"status": "error", "message": "No active race or invalid sailor"}), 400
    
    if app_state.get('race_ended'):
        conn.close()
        return jsonify({"status": "error", "message": "Race has ended"}), 400
    
    # Enforce: sailor's class must have started. Open-category sailors
    # (class not in the current Flag Machine sequence) are exempt - the
    # race start is their start.
    c.execute('SELECT class_id FROM sailors WHERE uid = ?', (uid,))
    srow = c.fetchone()
    class_id = srow['class_id'] if srow else None
    active_class_ids = get_active_class_ids_from_sequence()
    class_in_sequence = class_id is not None and class_id in active_class_ids
    if class_in_sequence and str(class_id) not in app_state.get('class_start_times', {}):
        conn.close()
        return jsonify({"status": "error", "message": "Class has not started yet"}), 400
    if not class_in_sequence and not open_class_started():
        conn.close()
        return jsonify({"status": "error", "message": "Open class has not started yet"}), 400
    
    # Double-capture guard (feature 4): the same sailor lapped twice within
    # 2 seconds is a double tap or both operators - reject it. Boats need
    # minutes per lap, so this never blocks a real lap.
    guard = c.execute('''SELECT timestamp FROM lap_records
                         WHERE race_id = ? AND uid = ?
                         ORDER BY lap_number DESC LIMIT 1''', (race_id, uid)).fetchone()
    if guard and guard['timestamp']:
        try:
            if (datetime.now() - datetime.fromisoformat(guard['timestamp'])).total_seconds() < 2:
                conn.close()
                return jsonify({"status": "error",
                                "message": "Lap already recorded for this sailor less than 2 seconds ago"}), 400
        except ValueError:
            pass
    
    try:
        # Ensure the sailor belongs to this race (open-category sailors are
        # not locked in by any class start, so join them on first interaction).
        # Locked: concurrent taps must not double-insert the sailor (bug 21).
        with RACE_STATE_LOCK:
            c.execute('SELECT id FROM race_sailors WHERE race_id = ? AND uid = ?', (race_id, uid))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO race_sailors (race_id, uid, lap_count, placement)
                    VALUES (?, ?, 0, NULL)
                ''', (race_id, uid))

        # Increment lap count
        c.execute('''
            UPDATE race_sailors
            SET lap_count = lap_count + 1
            WHERE race_id = ? AND uid = ?
        ''', (race_id, uid))
        
        # Get new lap count
        lap_number = c.execute('''
            SELECT lap_count FROM race_sailors WHERE race_id = ? AND uid = ?
        ''', (race_id, uid)).fetchone()['lap_count']
        
        # Record lap
        lap_time = datetime.now().isoformat()
        cur = c.execute('''
            INSERT INTO lap_records (race_id, uid, lap_number, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (race_id, uid, lap_number, lap_time))
        # Log the capture for per-station Step Back (feature 4)
        c.execute('''INSERT INTO capture_actions
                      (race_id, uid, action, station, timestamp, lap_number, ref_id)
                      VALUES (?, ?, 'lap', ?, ?, ?, ?)''',
                  (race_id, uid, station, lap_time, lap_number, cur.lastrowid))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "lap_count": lap_number, "last_lap_time": lap_time})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/mark-finish', methods=['POST'])
def mark_finish():
    """Mark a sailor as finished. Requires sailor's class to have started."""
    conn = get_db_connection()
    c = conn.cursor()
    
    payload = request.get_json()
    race_id = app_state.get('race_id')
    uid = payload.get('uid')
    # Station that captured this (feature 4) - logged for per-screen Step Back
    try:
        station = int(payload.get('station'))
    except (TypeError, ValueError):
        station = None
    
    if not race_id or not uid:
        conn.close()
        return jsonify({"status": "error", "message": "No active race or invalid sailor"}), 400
    
    if app_state.get('race_ended'):
        conn.close()
        return jsonify({"status": "error", "message": "Race has ended"}), 400
    
    # Enforce: sailor's class must have started. Open-category sailors
    # (class not in the current Flag Machine sequence) are exempt - the
    # race start is their start.
    c.execute('SELECT class_id FROM sailors WHERE uid = ?', (uid,))
    srow = c.fetchone()
    class_id = srow['class_id'] if srow else None
    active_class_ids = get_active_class_ids_from_sequence()
    class_in_sequence = class_id is not None and class_id in active_class_ids
    if class_in_sequence and str(class_id) not in app_state.get('class_start_times', {}):
        conn.close()
        return jsonify({"status": "error", "message": "Class has not started yet"}), 400
    if not class_in_sequence and not open_class_started():
        conn.close()
        return jsonify({"status": "error", "message": "Open class has not started yet"}), 400
    
    try:
        # Ensure the sailor belongs to this race (open-category sailors are
        # not locked in by any class start, so join them on first interaction).
        # Locked: concurrent taps must not double-insert the sailor (bug 21).
        with RACE_STATE_LOCK:
            c.execute('SELECT id FROM race_sailors WHERE race_id = ? AND uid = ?', (race_id, uid))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO race_sailors (race_id, uid, lap_count, placement)
                    VALUES (?, ?, 0, NULL)
                ''', (race_id, uid))

        finish_time = datetime.now().isoformat()
        c.execute('''
            UPDATE race_sailors
            SET finish_time = ?
            WHERE race_id = ? AND uid = ?
        ''', (finish_time, race_id, uid))
        # Log the capture for per-station Step Back (feature 4)
        c.execute('''INSERT INTO capture_actions
                      (race_id, uid, action, station, timestamp)
                      VALUES (?, ?, 'finish', ?, ?)''',
                  (race_id, uid, station, finish_time))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "finish_time": finish_time})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

def _normalize_station(payload):
    """Station param for undo/restore: must be 1 or 2."""
    try:
        station = int(payload.get('station'))
    except (TypeError, ValueError):
        station = 0
    return station if station in (1, 2) else None

@app.route('/api/undo-last', methods=['POST'])
def undo_last():
    """Step Back (feature 4): reverse THIS station's most recent capture.
    Lap: the logged lap record is removed and the lap count decremented.
    Finish: the finish time is cleared and the sailor returns to racing.
    The action stays in the log (undone=1) so /api/restore-last can
    re-apply it with the ORIGINAL timestamp. The undone action's time
    drops off the live sheet; all other times keep exact timestamps
    (agreed with the RO 2026-10-16)."""
    station = _normalize_station(request.get_json() or {})
    if station is None:
        return jsonify({"status": "error", "message": "station (1 or 2) required"}), 400
    race_id = app_state.get('race_id')
    if not race_id:
        return jsonify({"status": "error", "message": "No active race"}), 400
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT ca.*, s.short_name FROM capture_actions ca
                 JOIN sailors s ON s.uid = ca.uid
                 WHERE ca.race_id = ? AND ca.station = ? AND ca.undone = 0
                 ORDER BY ca.id DESC LIMIT 1''', (race_id, station))
    action = c.fetchone()
    if not action:
        conn.close()
        return jsonify({"status": "error",
                        "message": "Nothing to step back for this station"}), 404
    if action['action'] == 'lap':
        if not c.execute('SELECT id FROM lap_records WHERE id = ?',
                         (action['ref_id'],)).fetchone():
            conn.close()
            return jsonify({"status": "error",
                            "message": "That lap was already reversed"}), 409
        c.execute('DELETE FROM lap_records WHERE id = ?', (action['ref_id'],))
        c.execute('''UPDATE race_sailors SET lap_count = MAX(lap_count - 1, 0)
                     WHERE race_id = ? AND uid = ?''', (race_id, action['uid']))
    else:  # finish
        row = c.execute('''SELECT finish_time FROM race_sailors
                           WHERE race_id = ? AND uid = ?''',
                         (race_id, action['uid'])).fetchone()
        if (row['finish_time'] if row else None) != action['timestamp']:
            conn.close()
            return jsonify({"status": "error",
                            "message": "That finish was superseded by a later finish"}), 409
        c.execute('''UPDATE race_sailors SET finish_time = NULL
                     WHERE race_id = ? AND uid = ?''', (race_id, action['uid']))
    c.execute('UPDATE capture_actions SET undone = 1, undone_at = ? WHERE id = ?',
              (datetime.now().isoformat(), action['id']))
    conn.commit()
    conn.close()
    app_state['sheet_version'] = app_state.get('sheet_version', 1) + 1
    return jsonify({
        "status": "success",
        "action": action['action'],
        "uid": action['uid'],
        "sailor": action['short_name'],
        "lap_number": action['lap_number'],
        "timestamp": action['timestamp'],
    })

@app.route('/api/restore-last', methods=['POST'])
def restore_last():
    """Restore this station's most recently undone capture with its
    ORIGINAL timestamp - the safety net behind instant Step Back."""
    station = _normalize_station(request.get_json() or {})
    if station is None:
        return jsonify({"status": "error", "message": "station (1 or 2) required"}), 400
    race_id = app_state.get('race_id')
    if not race_id:
        return jsonify({"status": "error", "message": "No active race"}), 400
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT ca.*, s.short_name FROM capture_actions ca
                 JOIN sailors s ON s.uid = ca.uid
                 WHERE ca.race_id = ? AND ca.station = ? AND ca.undone = 1
                 ORDER BY ca.undone_at DESC LIMIT 1''', (race_id, station))
    action = c.fetchone()
    if not action:
        conn.close()
        return jsonify({"status": "error",
                        "message": "Nothing undone to restore for this station"}), 404
    if action['action'] == 'lap':
        cur = c.execute('''INSERT INTO lap_records (race_id, uid, lap_number, timestamp)
                           VALUES (?, ?, ?, ?)''',
                         (race_id, action['uid'], action['lap_number'], action['timestamp']))
        c.execute('UPDATE capture_actions SET ref_id = ? WHERE id = ?',
                  (cur.lastrowid, action['id']))
        c.execute('''UPDATE race_sailors SET lap_count = lap_count + 1
                     WHERE race_id = ? AND uid = ?''', (race_id, action['uid']))
    else:  # finish
        row = c.execute('''SELECT finish_time FROM race_sailors
                           WHERE race_id = ? AND uid = ?''',
                         (race_id, action['uid'])).fetchone()
        if row and row['finish_time'] is not None:
            conn.close()
            return jsonify({"status": "error",
                            "message": "That sailor has finished again since - nothing restored"}), 409
        c.execute('''UPDATE race_sailors SET finish_time = ?
                     WHERE race_id = ? AND uid = ?''',
                  (action['timestamp'], race_id, action['uid']))
    c.execute('UPDATE capture_actions SET undone = 0, undone_at = NULL WHERE id = ?',
              (action['id'],))
    conn.commit()
    conn.close()
    app_state['sheet_version'] = app_state.get('sheet_version', 1) + 1
    return jsonify({
        "status": "success",
        "action": action['action'],
        "uid": action['uid'],
        "sailor": action['short_name'],
        "lap_number": action['lap_number'],
        "timestamp": action['timestamp'],
    })

@app.route('/api/get-elapsed-time')
def get_elapsed_time():
    """Get elapsed time since the EARLIEST class start time (first flag to hit 00:00).
    Freezes at race_end_timestamp once the race has ended.
    """
    class_start_times = app_state.get('class_start_times', {})
    race_ended = app_state.get('race_ended', False)
    race_end_timestamp = app_state.get('race_end_timestamp')
    
    end_reference = datetime.fromisoformat(race_end_timestamp) if (race_ended and race_end_timestamp) else datetime.now()
    
    if class_start_times:
        earliest = min(class_start_times.values())
        start = datetime.fromisoformat(earliest)
        elapsed = end_reference - start
        seconds = max(0, int(elapsed.total_seconds()))
        return jsonify({
            "status": "success",
            "elapsed_seconds": seconds,
            "formatted": f"{seconds // 60:02d}:{seconds % 60:02d}",
            "frozen": race_ended
        })
    
    # Fallback: legacy race_start_timestamp (manual button before any class starts)
    if app_state.get('race_start_timestamp'):
        start = datetime.fromisoformat(app_state['race_start_timestamp'])
        elapsed = end_reference - start
        seconds = max(0, int(elapsed.total_seconds()))
        return jsonify({
            "status": "success",
            "elapsed_seconds": seconds,
            "formatted": f"{seconds // 60:02d}:{seconds % 60:02d}",
            "frozen": race_ended
        })
    return jsonify({"status": "error", "message": "No active race"}), 400

# ==================== SAILWAVE INTEGRATION ====================

def find_sailwave_source():
    """Locate the Sailwave competitor source file.
    Prefer the boat_master.htm listing (the club's actual Sailwave export,
    agreed with the RO 2026-10-16 - the 'Import Sailwave sailors' button
    reads it); fall back to Boats_Master.xml, then tempref/."""
    candidates = [
        # Sailwave writes Boats_master.htm; include case variants (some
        # setups match these case-sensitively)
        os.path.join(SAILWAVE_DB_FOLDER, 'Boats_master.htm'),
        os.path.join(SAILWAVE_DB_FOLDER, 'boat_master.htm'),
        os.path.join(os.path.dirname(__file__), 'tempref', 'boat_master.htm'),
        os.path.join(SAILWAVE_DB_FOLDER, 'Boats_Master.xml'),
        os.path.join(SAILWAVE_DB_FOLDER, 'boat_master.xml'),
        os.path.join(os.path.dirname(__file__), 'tempref', 'Boats_Master.xml'),
        os.path.join(os.path.dirname(__file__), 'tempref', 'boat_master.xml'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


@app.route('/api/refresh-sailwave', methods=['POST'])
def refresh_sailwave():
    """
    Import/refresh sailor and boat class data from the Sailwave export.
    
    Reads boat_master.htm (the club's Sailwave HTML competitor list) when
    present, falling back to Boats_Master.xml, and updates score.db.
    
    Returns:
        {"status": "success", "message": "...", "imported": {...}}
    """
    import subprocess
    import sys
    
    # Path to the import script
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'import_sailwave.py')
    
    # Check if import script exists
    if not os.path.exists(script_path):
        return jsonify({
            "status": "error",
            "message": f"Import script not found: {script_path}"
        }), 404
    
    # Locate the Sailwave XML source file (public folder first, then tempref)
    xml_path = find_sailwave_source()
    if not xml_path:
        return jsonify({
            "status": "error",
            "message": f"No boat_master.htm or Boats_Master.xml found in "
                       f"{SAILWAVE_DB_FOLDER} or the tempref/ folder."
        }), 404
    
    try:
        # Run the import script against the located source file
        result = subprocess.run(
            [sys.executable, script_path, '--xml-path', xml_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            # Parse the output to get statistics
            output_lines = result.stdout.split('\n')
            summary = {}
            
            for line in output_lines:
                if 'Boat Classes:' in line:
                    parts = line.strip().split(',')
                    for part in parts:
                        if 'new' in part:
                            summary['classes_new'] = int(part.split()[0])
                        elif 'updated' in part:
                            summary['classes_updated'] = int(part.split()[0])
                elif 'Sailors:' in line:
                    parts = line.strip().split(',')
                    for part in parts:
                        if 'new' in part:
                            summary['sailors_new'] = int(part.split()[0])
                        elif 'updated' in part:
                            summary['sailors_updated'] = int(part.split()[0])
                        elif 'skipped' in part:
                            summary['sailors_skipped'] = int(part.split()[0])
                elif 'Total Sailors in DB:' in line:
                    summary['total_sailors'] = int(line.strip().split(':')[-1].strip())
            
            return jsonify({
                "status": "success",
                "message": "Sailwave data refreshed successfully",
                "imported": summary,
                "output": result.stdout
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Import failed",
                "error": result.stderr,
                "output": result.stdout
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Import failed: {str(e)}"
        }), 500


@app.route('/api/refresh-sailwave-status', methods=['GET'])
def refresh_sailwave_status():
    """
    Check if the Sailwave export (boat_master.htm preferred, else
    Boats_Master.xml) is available for import.
    
    Returns:
        {"status": "available" or "not_found", "path": "..."}
    """
    xml_path = find_sailwave_source()
    
    if xml_path:
        # Get file info
        stat = os.stat(xml_path)
        return jsonify({
            "status": "available",
            "path": xml_path,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    else:
        return jsonify({
            "status": "not_found",
            "path": SAILWAVE_DB_FOLDER,
            "message": "boat_master.htm / Boats_Master.xml not found in the Sailwave database folder or tempref/."
        })


if __name__ == '__main__':
    # Bug 27: after a mid-race restart, adopt the RUNNING race from the DB
    # (recent) or close abandoned ones (stale) before serving. Runs in the
    # real entry point only - regression scripts import the module and swap
    # DB_PATH afterwards, so no import-time DB access may happen here.
    recover_running_race()
    app.run(host='localhost', port=5000, debug=True)
