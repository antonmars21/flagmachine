# app.py
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 1. Expand the global state structure near the top of app.py
app_state = {
    "master_start_time": "12:00",
    "status": "READY",
    "sequence": [],
    "race_duration": "00:00:00" # Persistent duration tracker field
}

# 2. Update your /execute-control route logic to capture the parameter values
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

# Define the absolute local path to your flags folder
FLAGS_FOLDER = r"C:\Users\anton\flagmachine\drag-drop-app\static\flags"

def get_dynamic_asset_library():
    """Scans the flags directory for image assets and generates labels automatically."""
    assets = []
    # Supported file extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.svg')
    
    if os.path.exists(FLAGS_FOLDER):
        for filename in os.listdir(FLAGS_FOLDER):
            if filename.lower().endswith(valid_extensions):
                # Split the name and extension (e.g., 'ilca 6.png' -> 'ilca 6')
                base_name, _ = os.path.splitext(filename)
                
                # Replace underscores or hyphens with spaces and fix capitalization
                clean_label = base_name.replace('_', ' ').replace('-', ' ').title()
                
                # Default countdown value
                default_minutes = 5
                if "prep" in clean_label.lower() or "p flag" in clean_label.lower():
                    default_minutes = 2
                
                assets.append({
                    "label": clean_label,
                    "flag_image": filename,
                    "default_minutes": default_minutes
                })
    else:
        # Fallback if the folder is missing or paths differ during deployment
        assets = [
            {"label": "ILCA 6", "flag_image": "ilca6.png", "default_minutes": 5},
            {"label": "P Flag (Prep)", "flag_image": "p_flag.png", "default_minutes": 2},
            {"label": "Starling", "flag_image": "starling.png", "default_minutes": 3}
        ]
    
    return assets

# Master Data State Layer held in memory context
app_state = {
    "master_start_time": "11:30",
    "status": "READY",  # READY, RUNNING, FINISHED
    "sequence": [
        {
            "id": "seq_initial_1",
            "label": "ILCA 6",
            "flag_image": "ilca6.png",
            "countdown_minutes": 5,
            "status": "PENDING"
        },
        {
            "id": "seq_initial_2",
            "label": "P Flag (Prep)",
            "flag_image": "p_flag.png",
            "countdown_minutes": 2,
            "status": "PENDING"
        },
        {
            "id": "seq_initial_3",
            "label": "Starling",
            "flag_image": "starling.png",
            "countdown_minutes": 3,
            "status": "PENDING"
        }
    ]
}

@app.route('/')
def index():
    # Fetch assets dynamically right when rendering the page
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
    if payload and 'status' in payload:
        app_state['status'] = payload['status']
        return jsonify({"status": "success", "global_status": app_state['status']})
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(debug=True)