# app.py
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

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

# Standard Asset Palette Library Definitions (Left Sidebar Source)
ASSET_LIBRARY = [
    {"label": "ILCA 6", "flag_image": "ilca6.png", "default_minutes": 5},
    {"label": "Starling", "flag_image": "starling.png", "default_minutes": 3},
    {"label": "Optimist", "flag_image": "optimist.png", "default_minutes": 5},
    {"label": "P Class", "flag_image": "pclass.png", "default_minutes": 1},
    {"label": "P Flag (Prep)", "flag_image": "p_flag.png", "default_minutes": 2}
]

@app.route('/')
def index():
    return render_template('index.html', state=app_state, library=ASSET_LIBRARY)

@app.route('/update-sequence', methods=['POST'])
def update_sequence():
    """
    Ingests a JSON payload containing the ordered list of sequence cards.
    Rebuilds the active sequence in memory context.
    """
    payload = request.get_json()
    if not payload or 'sequence' not in payload:
        return jsonify({"status": "error", "message": "Invalid sequence data"}), 400
        
    if app_state["status"] == "RUNNING":
        return jsonify({"status": "error", "message": "Sequence locked. Race is running!"}), 403

    app_state["sequence"] = payload['sequence']
    return jsonify({"status": "success", "sequence_count": len(app_state["sequence"])})

@app.route('/update-settings', methods=['POST'])
def update_settings():
    """
    Ingests localized configuration mutations on the fly without full page reloads.
    Handles global updates (master_start_time) and individual row duration adjustments.
    """
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "message": "Missing payload"}), 400

    if app_state["status"] == "RUNNING":
        return jsonify({"status": "error", "message": "Configuration is locked while race is active"}), 403

    # Handle global master start time modification
    if 'master_start_time' in payload:
        app_state['master_start_time'] = payload['master_start_time']
        return jsonify({"status": "success", "updated": "master_start_time"})

    # Handle single card countdown duration adjustments
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
    """Updates global execution state machine status (READY, RUNNING, FINISHED)"""
    payload = request.get_json()
    if payload and 'status' in payload:
        app_state['status'] = payload['status']
        return jsonify({"status": "success", "global_status": app_state['status']})
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    # Network Endpoint Binding matching constraints
    app.run(host='127.0.0.1', port=5000, debug=True)