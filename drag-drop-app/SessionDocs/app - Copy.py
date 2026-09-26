import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

FLAGS_FOLDER = r"C:\Users\anton\flagmachine\drag-drop-app\static\flags"

def get_dynamic_asset_library():
    assets = []
    valid_extensions = ('.png', '.jpg', '.jpeg', '.svg')
    
    if os.path.exists(FLAGS_FOLDER):
        for filename in os.listdir(FLAGS_FOLDER):
            if filename.lower().endswith(valid_extensions):
                base_name, _ = os.path.splitext(filename)
                clean_label = base_name.replace('_', ' ').replace('-', ' ').title()
                
                default_minutes = 5
                if "prep" in clean_label.lower() or "p flag" in clean_label.lower():
                    default_minutes = 2
                
                assets.append({
                    "label": clean_label,
                    "flag_image": filename,
                    "default_minutes": default_minutes
                })
    else:
        assets = [
            {"label": "ILCA 6", "flag_image": "ilca6.png", "default_minutes": 5},
            {"label": "P Flag (Prep)", "flag_image": "p_flag.png", "default_minutes": 2},
            {"label": "Starling", "flag_image": "starling.png", "default_minutes": 3}
        ]
    
    return assets

app_state = {
    "master_start_time": "11:30",
    "status": "READY",  # READY, RUNNING, FINISHED, ENDED
    "race_duration": "00:00:00",
    "active_grid": None,
    "sequence": []
}

@app.route('/')
def index():
    assets = get_dynamic_asset_library()
    return render_template('index.html', state=app_state, assets=assets)

@app.route('/update-sequence', methods=['POST'])
def update_sequence():
    payload = request.get_json()
    if payload and 'ordered_ids' in payload:
        ordered_ids = payload['ordered_ids']
        ordered_lookup = {item['id']: item for item in app_state['sequence']}
        
        new_sequence = []
        for seq_id in ordered_ids:
            if seq_id in ordered_lookup:
                new_sequence.append(ordered_lookup[seq_id])
                
        app_state['sequence'] = new_sequence
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

    # global status only
    if 'status' in payload and 'active_id' not in payload:
        app_state['status'] = payload['status']
        return jsonify({"status": "success", "global_status": app_state['status']})

    # row-level active status
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
            
    return jsonify({
        "status": "success", 
        "current_state": app_state['status'], 
        "race_duration": app_state['race_duration']
    })

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

    if active_event:
        grid_index = app_state.get('active_grid') or active_event.get('grid_index') or 1
        grid_name = f"Event Grid {grid_index}"
        return jsonify({
            "status": "RUNNING",
            "grid_name": grid_name,
            "flag_image": active_event.get('flag_image'),
            "live_timer": active_event.get('current_live_timer', '--:--')
        })
    else:
        return jsonify({
            "status": "STANDBY", 
            "grid_name": "STANDBY", 
            "flag_image": "", 
            "live_timer": "--:--"
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

if __name__ == '__main__':
    app.run(debug=True)
