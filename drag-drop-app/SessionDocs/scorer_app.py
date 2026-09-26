import os
import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roster.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create the persistent master profile table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sailors (
            uid TEXT PRIMARY KEY,
            sailor_name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            sail_no TEXT NOT NULL,
            boat_class TEXT NOT NULL,
            handicap REAL DEFAULT 1.0,
            seed INTEGER DEFAULT 0,
            racing_today INTEGER DEFAULT 0,
            status TEXT DEFAULT 'racing',
            finish_order INTEGER DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    # Fetch all registered sailors for the data profile listing
    all_sailors = conn.execute('SELECT * FROM sailors ORDER BY sailor_name ASC').fetchall()
    
    # Fetch active racers for the Kanban board
    active_racers = conn.execute('SELECT * FROM sailors WHERE racing_today = 1').fetchall()
    conn.close()
    
    # Process Kanban column organization
    # 1. Racing Lane: Grouped by Boat Class and ordered strictly by Seed value
    racing_lane = {}
    finished_lane = []
    
    for sailor in active_racers:
        s_dict = dict(sailor)
        if s_dict['status'] == 'finished':
            finished_lane.append(s_dict)
        else:
            b_class = s_dict['boat_class']
            if b_class not in racing_lane:
                racing_lane[b_class] = []
            racing_lane[b_class].append(s_dict)
            
    # Sort the grouped classes entries internally by seed value
    for b_class in racing_lane:
        racing_lane[b_class].sort(key=lambda x: x['seed'])
        
    # Sort the finished lane entries by their registered drop completion sequence
    finished_lane.sort(key=lambda x: (x['finish_order'] if x['finish_order'] is not None else 9999))
    
    return render_template('roster.html', all_sailors=all_sailors, racing_lane=racing_lane, finished_lane=finished_lane)

@app.route('/add-sailor', methods=['POST'])
def add_sailor():
    uid = request.form.get('uid', '').strip()
    sailor_name = request.form.get('sailor_name', '').strip()
    short_name = request.form.get('short_name', '').strip()
    sail_no = request.form.get('sail_no', '').strip()
    boat_class = request.form.get('boat_class', '').strip()
    handicap = request.form.get('handicap', '1.0').strip()
    seed = request.form.get('seed', '0').strip()
    
    if not uid or not sailor_name:
        return "Error: UID and Sailor Name are required properties.", 400
        
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO sailors (uid, sailor_name, short_name, sail_no, boat_class, handicap, seed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (uid, sailor_name, short_name, sail_no, boat_class, float(handicap or 1.0), int(seed or 0)))
        conn.commit()
    except sqlite3.IntegrityError:
        return f"Error: A sailor record with UID '{uid}' already exists.", 400
    finally:
        conn.close()
        
    return index()

@app.route('/toggle-racing', methods=['POST'])
def toggle_racing():
    payload = request.get_json() or {}
    uid = payload.get('uid')
    racing_today = 1 if payload.get('racing_today') else 0
    
    conn = get_db_connection()
    if racing_today == 0:
        # If removing from today's race, flush Kanban state details back to defaults
        conn.execute('UPDATE sailors SET racing_today = 0, status = "racing", finish_order = NULL WHERE uid = ?', (uid,))
    else:
        conn.execute('UPDATE sailors SET racing_today = 1 WHERE uid = ?', (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/update-kanban', methods=['POST'])
def update_kanban():
    payload = request.get_json() or {}
    lane = payload.get('lane') # 'racing' or 'finished'
    ordered_uids = payload.get('ordered_uids', [])
    
    conn = get_db_connection()
    if lane == 'finished':
        # Re-index drop completion sequencing accurately
        for index, uid in enumerate(ordered_uids):
            conn.execute('UPDATE sailors SET status = "finished", finish_order = ? WHERE uid = ?', (index, uid))
    else:
        # Reverting element state back to execution lane properties
        for uid in ordered_uids:
            conn.execute('UPDATE sailors SET status = "racing", finish_order = NULL WHERE uid = ?', (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
    app.run(port=5001, debug=True)