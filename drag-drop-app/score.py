import os
import csv
import sqlite3
import io
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'score.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sailors (
            uid          TEXT PRIMARY KEY,
            sailor_name  TEXT NOT NULL,
            short_name   TEXT NOT NULL,
            sail_no      TEXT NOT NULL,
            boat_class   TEXT NOT NULL,
            handicap     REAL DEFAULT 1.0,
            seed         INTEGER DEFAULT 0,
            racing_today INTEGER DEFAULT 0,
            status       TEXT DEFAULT 'racing',
            finish_order INTEGER DEFAULT NULL,
            finish_time  TEXT DEFAULT NULL
        )
    ''')
    # Migrate: add finish_time if it doesn't exist yet
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sailors)").fetchall()]
    if 'finish_time' not in cols:
        conn.execute("ALTER TABLE sailors ADD COLUMN finish_time TEXT DEFAULT NULL")
    conn.commit()
    conn.close()

@app.route('/score')
def index():
    conn = get_db_connection()
    all_sailors = conn.execute(
        'SELECT * FROM sailors ORDER BY racing_today ASC, short_name ASC'
    ).fetchall()
    active_racers = conn.execute(
        'SELECT * FROM sailors WHERE racing_today = 1'
    ).fetchall()
    conn.close()

    racing_lane  = []
    finished_lane = []
    dnf_lane     = []
    dq_lane      = []

    for sailor in active_racers:
        s = dict(sailor)
        if s['status'] == 'finished':
            finished_lane.append(s)
        elif s['status'] == 'dnf':
            dnf_lane.append(s)
        elif s['status'] == 'dq':
            dq_lane.append(s)
        else:
            racing_lane.append(s)

    racing_lane.sort(key=lambda x: x['seed'])
    finished_lane.sort(key=lambda x: x['finish_order'] if x['finish_order'] is not None else 9999)
    dnf_lane.sort(key=lambda x: x['short_name'])
    dq_lane.sort(key=lambda x: x['short_name'])

    return render_template('score.html',
        sailors=all_sailors,
        racing_lane=racing_lane,
        finished_lane=finished_lane,
        dnf_lane=dnf_lane,
        dq_lane=dq_lane
    )

@app.route('/add-sailor', methods=['POST'])
def add_sailor():
    uid        = request.form.get('uid', '').strip()
    sailor_name= request.form.get('sailor_name', '').strip()
    short_name = request.form.get('short_name', '').strip()
    sail_no    = request.form.get('sail_no', '').strip()
    boat_class = request.form.get('boat_class', '').strip()
    handicap   = request.form.get('handicap', '1.0').strip()
    seed       = request.form.get('seed', '0').strip()

    if not uid or not sailor_name:
        return "Error: UID and Sailor Name are required.", 400

    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO sailors (uid, sailor_name, short_name, sail_no, boat_class, handicap, seed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (uid, sailor_name, short_name, sail_no, boat_class,
              float(handicap or 1.0), int(seed or 0)))
        conn.commit()
    except sqlite3.IntegrityError:
        return f"Error: A sailor with UID '{uid}' already exists.", 400
    finally:
        conn.close()
    return index()

@app.route('/toggle-racing', methods=['POST'])
def toggle_racing():
    payload      = request.get_json() or {}
    uid          = payload.get('uid')
    racing_today = 1 if payload.get('racing_today') else 0

    conn = get_db_connection()
    if racing_today == 0:
        conn.execute(
            'UPDATE sailors SET racing_today=0, status="racing", finish_order=NULL, finish_time=NULL WHERE uid=?',
            (uid,)
        )
    else:
        conn.execute('UPDATE sailors SET racing_today=1 WHERE uid=?', (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/edit-sailor/<uid>', methods=['PUT'])
def edit_sailor(uid):
    payload    = request.get_json() or {}
    sailor_name= payload.get('sailor_name', '').strip()
    short_name = payload.get('short_name', '').strip()
    sail_no    = payload.get('sail_no', '').strip()
    boat_class = payload.get('boat_class', '').strip()
    seed       = payload.get('seed', 0)
    handicap   = payload.get('handicap', 1.0)

    if not sailor_name or not short_name or not sail_no or not boat_class:
        return jsonify({"status": "error", "message": "All fields required"}), 400

    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE sailors
            SET sailor_name=?, short_name=?, sail_no=?, boat_class=?, handicap=?, seed=?
            WHERE uid=?
        ''', (sailor_name, short_name, sail_no, boat_class,
              float(handicap or 1.0), int(seed or 0), uid))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})

@app.route('/delete-sailor/<uid>', methods=['DELETE'])
def delete_sailor(uid):
    conn = get_db_connection()
    conn.execute('DELETE FROM sailors WHERE uid=?', (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/update-kanban', methods=['POST'])
def update_kanban():
    payload      = request.get_json() or {}
    lane         = payload.get('lane')          # 'racing' | 'finished' | 'dnf' | 'dq'
    ordered_uids = payload.get('ordered_uids', [])
    # finish_times: dict uid -> "HH:MM:SS" sent by client for newly-dropped tiles
    finish_times = payload.get('finish_times', {})

    conn = get_db_connection()
    if lane == 'finished':
        for index, uid in enumerate(ordered_uids):
            ft = finish_times.get(uid)  # None if already had a time
            if ft:
                conn.execute(
                    'UPDATE sailors SET status="finished", finish_order=?, finish_time=? WHERE uid=?',
                    (index, ft, uid)
                )
            else:
                conn.execute(
                    'UPDATE sailors SET status="finished", finish_order=? WHERE uid=?',
                    (index, uid)
                )
    elif lane == 'dnf':
        for uid in ordered_uids:
            conn.execute(
                'UPDATE sailors SET status="dnf", finish_order=NULL, finish_time=NULL WHERE uid=?',
                (uid,)
            )
    elif lane == 'dq':
        for uid in ordered_uids:
            conn.execute(
                'UPDATE sailors SET status="dq", finish_order=NULL, finish_time=NULL WHERE uid=?',
                (uid,)
            )
    else:  # back to racing
        for uid in ordered_uids:
            conn.execute(
                'UPDATE sailors SET status="racing", finish_order=NULL, finish_time=NULL WHERE uid=?',
                (uid,)
            )
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/export-csv')
def export_csv():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT short_name, sailor_name, sail_no, boat_class, seed,
               status, finish_order, finish_time
        FROM sailors
        WHERE racing_today = 1
        ORDER BY
            CASE status
                WHEN 'finished' THEN 0
                WHEN 'dnf'      THEN 1
                WHEN 'dq'       THEN 2
                ELSE                 3
            END,
            finish_order ASC,
            short_name ASC
    ''').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Place', 'Short Name', 'Full Name', 'Sail No',
                     'Boat Class', 'Seed', 'Status', 'Finish Time'])

    place = 1
    for r in rows:
        status = r['status']
        if status == 'finished':
            place_str = str(place)
            place += 1
        elif status == 'dnf':
            place_str = 'DNF'
        elif status == 'dq':
            place_str = 'DQ'
        else:
            place_str = 'DNS'

        writer.writerow([
            place_str,
            r['short_name'],
            r['sailor_name'],
            r['sail_no'],
            r['boat_class'],
            r['seed'],
            status.upper(),
            r['finish_time'] or ''
        ])

    csv_bytes = output.getvalue().encode('utf-8')
    return Response(
        csv_bytes,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=race_results.csv'}
    )

@app.route('/clear-registry', methods=['POST'])
def clear_registry():
    """Clear all racing_today flags for all sailors."""
    conn = get_db_connection()
    conn.execute("UPDATE sailors SET racing_today = 0")
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "All checkboxes cleared"})

@app.route('/reset-finish-sheet', methods=['POST'])
def reset_finish_sheet():
    """Reset finish sheet - clear all finish times and orders."""
    conn = get_db_connection()
    conn.execute("UPDATE sailors SET finish_order = NULL, finish_time = NULL")
    conn.execute("UPDATE sailors SET status = 'racing' WHERE status IN ('finished', 'dnf', 'dq')")
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Finish sheet reset"})

@app.route('/reset-day', methods=['POST'])
def reset_day():
    """Clear all racing_today flags and finish data for a fresh race."""
    conn = get_db_connection()
    conn.execute(
        'UPDATE sailors SET racing_today=0, status="racing", finish_order=NULL, finish_time=NULL'
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    init_db()
    print("Score DB initialised at:", DB_PATH)
    app.run(host='localhost', port=5001, debug=False)
