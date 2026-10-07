"""
Session 4: Finish Sheet v1.1 - Race Officer Control + Sailor Tracking
Runs on localhost:5000 with Flag Machine and Finish Sheet integrated
"""
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DB_PATH = 'score.db'
FLAGS_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'flags')

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
        source TEXT DEFAULT 'flag_machine',
        FOREIGN KEY(race_id) REFERENCES races(race_id),
        FOREIGN KEY(class_id) REFERENCES boat_classes(class_id),
        UNIQUE(race_id, class_id)
    )''')
    
    conn.commit()
    conn.close()

init_finishsheet_tables()

def get_dynamic_asset_library():
    assets = []
    valid_extensions = ('.png', '.jpg', '.jpeg', '.svg')
    
    if os.path.exists(FLAGS_FOLDER):
        for filename in os.listdir(FLAGS_FOLDER):
            if filename.lower().endswith(valid_extensions):
                base_name, _ = os.path.splitext(filename)
                clean_label = base_name.replace('_', ' ').replace('-', ' ').title()
                default_minutes = 2
                if "prep" in clean_label.lower() or "p flag" in clean_label.lower():
                    default_minutes = 1
                
                assets.append({
                    "label": clean_label,
                    "flag_image": filename,
                    "default_minutes": default_minutes
                })
    else:
        assets = [
            {"label": "ILCA 6", "flag_image": "ilca6.png", "default_minutes": 2},
            {"label": "P Flag (Prep)", "flag_image": "p_flag.png", "default_minutes": 1},
            {"label": "Starling", "flag_image": "starling.png", "default_minutes": 2}
        ]
    
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
    "race_ended": False,
    "race_end_timestamp": None
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
        fi = item.get('flag_image')
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

# ==================== FLAG MACHINE ROUTES ====================

@app.route('/')
def index():
    assets = get_dynamic_asset_library()
    return render_template('index.html', state=app_state, assets=assets)

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
    elif action == 'STOP':
        app_state['status'] = 'PAUSED'
    elif action == 'RESET':
        app_state['status'] = 'READY'
        app_state['race_duration'] = '00:00:00'
    elif action == 'END_RACE':
        app_state['status'] = 'ENDED'
        if 'duration' in payload:
            app_state['race_duration'] = payload['duration']
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
            "live_timer": active_event.get('current_live_timer', '--:--'),
            "display_mode": display_mode
        })
    else:
        return jsonify({
            "status": "STANDBY", 
            "grid_name": "STANDBY", 
            "flag_image": "", 
            "secondary_flag_image": None,
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
    """Render finish sheet UI for race officer scoring."""
    return render_template('finishsheet.html')

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
    
    if race_id and started_class_ids:
        # Started classes: locked roster from race_sailors (whoever was signed on at start time)
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed, 
                   rs.lap_count, rs.finish_time, rs.placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex
            FROM sailors s
            JOIN race_sailors rs ON s.uid = rs.uid
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            WHERE rs.race_id = ? AND s.class_id IN ({})
            ORDER BY s.boat_class, s.seed
        '''.format(','.join('?' * len(started_class_ids))), (race_id, *started_class_ids))
        started_rows = c.fetchall()
    else:
        started_rows = []
    
    # Not-yet-started classes: LIVE from registry (racing_today), regardless of race_id
    if started_class_ids:
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed,
                   0 as lap_count, NULL as finish_time, NULL as placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex
            FROM sailors s
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            WHERE s.racing_today = 1 AND (s.class_id IS NULL OR s.class_id NOT IN ({}))
            ORDER BY s.boat_class, s.seed
        '''.format(','.join('?' * len(started_class_ids))), tuple(started_class_ids))
    else:
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed,
                   0 as lap_count, NULL as finish_time, NULL as placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex
            FROM sailors s
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            WHERE s.racing_today = 1
            ORDER BY s.boat_class, s.seed
        ''')
    live_rows = c.fetchall()
    conn.close()
    
    rows = list(started_rows) + list(live_rows)
    
    sequence_groups = {}
    open_category_sailors = []
    
    for row in rows:
        class_id = row['class_id']
        start_time = class_start_times.get(str(class_id)) if class_id is not None else None
        sailor_dict = {
            'uid': row['uid'],
            'sail_no': row['sail_no'],
            'short_name': row['short_name'],
            'boat_class': row['boat_class'],
            'seed': row['seed'],
            'lap_count': row['lap_count'],
            'finish_time': row['finish_time'],
            'placement': row['placement'],
            'class_id': class_id,
            'flag_image': row['flag_image'],
            'color_hex': row['color_hex'],
            'class_started': start_time is not None,
            'class_start_time': start_time
        }
        
        if class_id is not None and class_id in active_class_ids:
            if class_id not in sequence_groups:
                sequence_groups[class_id] = {
                    'class_id': class_id,
                    'class_name': row['class_name'],
                    'flag_image': row['flag_image'],
                    'color_hex': row['color_hex'],
                    'sailors': []
                }
            sequence_groups[class_id]['sailors'].append(sailor_dict)
        else:
            open_category_sailors.append(sailor_dict)
    
    # Order sequence-class columns: most sailors on the left
    ordered_columns = sorted(sequence_groups.values(), key=lambda g: len(g['sailors']), reverse=True)
    
    if open_category_sailors:
        ordered_columns.append({
            'class_id': None,
            'class_name': 'Open Category',
            'flag_image': 'openclass.png',
            'color_hex': '#64748b',
            'sailors': open_category_sailors
        })
    
    return jsonify({
        "status": "success",
        "columns": ordered_columns
    })

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
    """Add a new sailor to the registry."""
    payload = request.get_json() or {}
    uid = (payload.get('uid') or '').strip()
    sailor_name = (payload.get('sailor_name') or '').strip()
    short_name = (payload.get('short_name') or '').strip()
    sail_no = (payload.get('sail_no') or '').strip()
    boat_class = (payload.get('boat_class') or '').strip()
    handicap = payload.get('handicap', 1.0)
    seed = payload.get('seed', 0)
    
    if not uid or not sailor_name:
        return jsonify({"status": "error", "message": "UID and Sailor Name are required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT class_id FROM boat_classes WHERE LOWER(class_name) = LOWER(?)', (boat_class,))
        class_row = c.fetchone()
        class_id = class_row['class_id'] if class_row else None
        
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
    c.execute('SELECT class_id FROM boat_classes WHERE LOWER(class_name) = LOWER(?)', (boat_class,))
    class_row = c.fetchone()
    class_id = class_row['class_id'] if class_row else None
    
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
        # Create race record if none active
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
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "race_id": race_id})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/class-start', methods=['POST'])
def class_start():
    """Called by Flag Machine when a countdown row hits 00:00 for a given flag.
    Auto-creates race if none active (using all currently loaded sailors),
    then records the start time for that boat class.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    payload = request.get_json()
    flag_image = payload.get('flag_image') if payload else None
    
    if not flag_image:
        conn.close()
        return jsonify({"status": "error", "message": "flag_image required"}), 400
    
    try:
        # Look up boat class by flag_image (case-insensitive, defense in depth)
        c.execute('SELECT class_id, class_name FROM boat_classes WHERE LOWER(flag_image) = LOWER(?)', (flag_image,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({"status": "error", "message": f"No boat class found for flag_image={flag_image}"}), 404
        
        class_id = row['class_id']
        class_name = row['class_name']
        
        # Auto-create race if none active
        race_id = app_state.get('race_id')
        if not race_id:
            c.execute('INSERT INTO races (status) VALUES (?)', ('RUNNING',))
            conn.commit()
            race_id = c.lastrowid
            app_state['race_id'] = race_id
            app_state['race_start_timestamp'] = datetime.now().isoformat()
        
        # Lock in the roster ONLY for this class's sailors who are racing_today right now
        # (other not-yet-started classes remain live/editable via the registry sidebar)
        c.execute('SELECT uid FROM sailors WHERE racing_today = 1 AND class_id = ?', (class_id,))
        class_uids = [r['uid'] for r in c.fetchall()]
        for uid in class_uids:
            c.execute('SELECT id FROM race_sailors WHERE race_id = ? AND uid = ?', (race_id, uid))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO race_sailors (race_id, uid, lap_count, placement)
                    VALUES (?, ?, 0, NULL)
                ''', (race_id, uid))
        conn.commit()
        
        # Record class start time (idempotent - first trigger wins)
        now_iso = datetime.now().isoformat()
        c.execute('''
            INSERT OR IGNORE INTO race_class_starts (race_id, class_id, start_time, source)
            VALUES (?, ?, ?, 'flag_machine')
        ''', (race_id, class_id, now_iso))
        conn.commit()
        
        # Update in-memory state (use existing DB value if already set)
        c.execute('''
            SELECT start_time FROM race_class_starts WHERE race_id = ? AND class_id = ?
        ''', (race_id, class_id))
        actual_start = c.fetchone()['start_time']
        app_state['class_start_times'][str(class_id)] = actual_start
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "race_id": race_id,
            "class_id": class_id,
            "class_name": class_name,
            "start_time": actual_start
        })
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/race-status')
def race_status():
    """Return current race/class-start status for Finish Sheet polling."""
    return jsonify({
        "status": "success",
        "race_id": app_state.get('race_id'),
        "race_start_timestamp": app_state.get('race_start_timestamp'),
        "class_start_times": app_state.get('class_start_times', {}),
        "race_ended": app_state.get('race_ended', False),
        "race_end_timestamp": app_state.get('race_end_timestamp')
    })

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
    """Reset finish sheet - clear all finish times and orders."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE sailors SET finish_order = NULL, finish_time = NULL")
    c.execute("UPDATE race_sailors SET finish_time = NULL, placement = NULL")
    conn.commit()
    conn.close()
    # Also clear in-memory sequence
    app_state['sequence'] = []
    app_state['status'] = 'READY'
    return jsonify({"status": "success", "message": "Finish sheet reset"})

@app.route('/api/export-race-csv')
def export_race_csv():
    """Export current/last race as CSV: class, sailor, start time, laps, end time."""
    import csv
    import io
    from flask import Response
    
    race_id = app_state.get('race_id')
    if not race_id:
        return jsonify({"status": "error", "message": "No race to export"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT bc.class_name, s.sail_no, s.short_name,
               rcs.start_time as class_start_time,
               rs.lap_count, rs.finish_time,
               r.end_time as race_end_time
        FROM race_sailors rs
        JOIN sailors s ON rs.uid = s.uid
        LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
        LEFT JOIN race_class_starts rcs ON rcs.race_id = rs.race_id AND rcs.class_id = s.class_id
        JOIN races r ON r.race_id = rs.race_id
        WHERE rs.race_id = ?
        ORDER BY bc.class_name, s.sail_no
    ''', (race_id,))
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Class', 'Sailor', 'Sail No', 'Start Time', 'Laps', 'Finish Time', 'Race End Time'])
    
    for row in rows:
        writer.writerow([
            row['class_name'] or 'Unknown',
            row['short_name'],
            row['sail_no'],
            row['class_start_time'] or '',
            row['lap_count'],
            row['finish_time'] or '',
            row['race_end_time'] or ''
        ])
    
    csv_data = output.getvalue()
    filename = f"race_{race_id}_results.csv"
    
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
    
    if not race_id or not uid:
        conn.close()
        return jsonify({"status": "error", "message": "No active race or invalid sailor"}), 400
    
    if app_state.get('race_ended'):
        conn.close()
        return jsonify({"status": "error", "message": "Race has ended"}), 400
    
    # Enforce: sailor's class must have started
    c.execute('SELECT class_id FROM sailors WHERE uid = ?', (uid,))
    srow = c.fetchone()
    class_id = srow['class_id'] if srow else None
    if class_id is None or str(class_id) not in app_state.get('class_start_times', {}):
        conn.close()
        return jsonify({"status": "error", "message": "Class has not started yet"}), 400
    
    try:
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
        c.execute('''
            INSERT INTO lap_records (race_id, uid, lap_number, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (race_id, uid, lap_number, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "lap_count": lap_number})
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
    
    if not race_id or not uid:
        conn.close()
        return jsonify({"status": "error", "message": "No active race or invalid sailor"}), 400
    
    if app_state.get('race_ended'):
        conn.close()
        return jsonify({"status": "error", "message": "Race has ended"}), 400
    
    # Enforce: sailor's class must have started
    c.execute('SELECT class_id FROM sailors WHERE uid = ?', (uid,))
    srow = c.fetchone()
    class_id = srow['class_id'] if srow else None
    if class_id is None or str(class_id) not in app_state.get('class_start_times', {}):
        conn.close()
        return jsonify({"status": "error", "message": "Class has not started yet"}), 400
    
    try:
        finish_time = datetime.now().isoformat()
        c.execute('''
            UPDATE race_sailors
            SET finish_time = ?
            WHERE race_id = ? AND uid = ?
        ''', (finish_time, race_id, uid))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "finish_time": finish_time})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

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

@app.route('/api/refresh-sailwave', methods=['POST'])
def refresh_sailwave():
    """
    Import/refresh sailor and boat class data from Sailwave boat_master.json.
    
    This endpoint triggers the import script to read from boat_master.json
    and update the score.db with the latest data from Sailwave.
    
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
    
    # Check if boat_master.json exists
    json_path = os.path.join(os.path.dirname(__file__), 'tempref', 'boat_master.json')
    if not os.path.exists(json_path):
        return jsonify({
            "status": "error",
            "message": f"boat_master.json not found: {json_path}. "
                       f"Please copy it from Sailwave to the tempref/ folder."
        }), 404
    
    try:
        # Run the import script
        result = subprocess.run(
            [sys.executable, script_path],
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
    Check if boat_master.json is available for import.
    
    Returns:
        {"status": "available" or "not_found", "path": "..."}
    """
    json_path = os.path.join(os.path.dirname(__file__), 'tempref', 'boat_master.json')
    
    if os.path.exists(json_path):
        # Get file info
        stat = os.stat(json_path)
        return jsonify({
            "status": "available",
            "path": json_path,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    else:
        return jsonify({
            "status": "not_found",
            "path": json_path,
            "message": "boat_master.json not found. Please copy from Sailwave."
        })


if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
