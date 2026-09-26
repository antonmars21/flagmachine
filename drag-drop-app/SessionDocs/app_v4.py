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
    
    c.execute('''CREATE TABLE IF NOT EXISTS races (
        race_id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time TEXT,
        status TEXT DEFAULT 'READY',
        class_groups TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sailors (
        uid TEXT PRIMARY KEY,
        sailor_name TEXT,
        short_name TEXT,
        sail_no TEXT UNIQUE,
        boat_class TEXT,
        handicap REAL,
        seed INTEGER
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
    "race_start_timestamp": None
}

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
    """Get sailors grouped by class for 4-column display."""
    conn = get_db_connection()
    c = conn.cursor()
    
    race_id = app_state.get('race_id')
    
    if race_id:
        # Active race: get sailors from race_sailors join table
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed, 
                   rs.lap_count, rs.finish_time, rs.placement
            FROM sailors s
            JOIN race_sailors rs ON s.uid = rs.uid
            WHERE rs.race_id = ?
            ORDER BY s.boat_class, s.seed
        ''', (race_id,))
    else:
        # Pre-race: get all sailors
        c.execute('''
            SELECT uid, sail_no, short_name, boat_class, seed, 
                   0 as lap_count, NULL as finish_time, NULL as placement
            FROM sailors
            ORDER BY boat_class, seed
        ''')
    
    rows = c.fetchall()
    conn.close()
    
    # Group by class
    class_groups = {}
    for row in rows:
        boat_class = row['boat_class']
        if boat_class not in class_groups:
            class_groups[boat_class] = []
        class_groups[boat_class].append({
            'uid': row['uid'],
            'sail_no': row['sail_no'],
            'short_name': row['short_name'],
            'boat_class': boat_class,
            'seed': row['seed'],
            'lap_count': row['lap_count'],
            'finish_time': row['finish_time'],
            'placement': row['placement']
        })
    
    # Sort by class count (descending)
    sorted_classes = sorted(class_groups.items(), key=lambda x: len(x[1]), reverse=True)
    class_names = [cls[0] for cls in sorted_classes]
    
    # Build 4-column layout
    columns = {}
    for i in range(1, 5):
        columns[str(i)] = []
    
    # Top 3 classes get their own column
    for i, (cls_name, sailors_list) in enumerate(sorted_classes[:3]):
        columns[str(i + 1)] = sailors_list
    
    # Remaining sailors go to column 4 (Open)
    if len(sorted_classes) > 3:
        for cls_name, sailors_list in sorted_classes[3:]:
            columns['4'].extend(sailors_list)
    
    return jsonify({
        "status": "success",
        "columns": columns,
        "class_groups": class_names[:3] + (['Open'] if len(sorted_classes) > 3 else [])
    })

@app.route('/api/start-race', methods=['POST'])
def start_race():
    """Start a new race with selected sailors."""
    conn = get_db_connection()
    c = conn.cursor()
    
    payload = request.get_json()
    selected_sailors = payload.get('selected_sailors', [])
    
    try:
        # Create race record
        c.execute('INSERT INTO races (status) VALUES (?)', ('RUNNING',))
        conn.commit()
        race_id = c.lastrowid
        
        app_state['race_id'] = race_id
        app_state['race_start_timestamp'] = datetime.now().isoformat()
        
        # Add sailors to race
        for uid in selected_sailors:
            c.execute('''
                INSERT INTO race_sailors (race_id, uid, lap_count, placement)
                VALUES (?, ?, 0, NULL)
            ''', (race_id, uid))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "race_id": race_id})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/record-lap', methods=['POST'])
def record_lap():
    """Increment lap counter for a sailor."""
    conn = get_db_connection()
    c = conn.cursor()
    
    payload = request.get_json()
    race_id = app_state.get('race_id')
    uid = payload.get('uid')
    
    if not race_id or not uid:
        conn.close()
        return jsonify({"status": "error", "message": "No active race or invalid sailor"}), 400
    
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
    """Mark a sailor as finished."""
    conn = get_db_connection()
    c = conn.cursor()
    
    payload = request.get_json()
    race_id = app_state.get('race_id')
    uid = payload.get('uid')
    
    if not race_id or not uid:
        conn.close()
        return jsonify({"status": "error", "message": "No active race or invalid sailor"}), 400
    
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
    """Get elapsed time since race start."""
    if app_state.get('race_start_timestamp'):
        start = datetime.fromisoformat(app_state['race_start_timestamp'])
        elapsed = datetime.now() - start
        seconds = int(elapsed.total_seconds())
        return jsonify({
            "status": "success",
            "elapsed_seconds": seconds,
            "formatted": f"{seconds // 60:02d}:{seconds % 60:02d}"
        })
    return jsonify({"status": "error", "message": "No active race"}), 400

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
