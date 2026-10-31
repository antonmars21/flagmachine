#!/usr/bin/env python3
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app to access functions
import app
from app import app as flask_app

def test_sailors_for_onwater():
    print("=== Testing sailors_for_onwater function ===\n")
    
    # Set up test data in app_state
    app.app_state['sequence'] = [
        {'id': 'row_1', 'label': 'ILCA 6', 'flag_image': 'ilca6.png', 'grid_index': 1, 'status': 'PENDING'},
        {'id': 'row_2', 'label': 'Starling', 'flag_image': 'Starling.png', 'grid_index': 1, 'status': 'PENDING'},
        {'id': 'row_3', 'label': 'Optimist', 'flag_image': 'optimist.png', 'grid_index': 2, 'status': 'PENDING'},
    ]
    
    app.app_state['race_id'] = None
    app.app_state['class_start_times'] = {}
    
    # Import and call the function directly
    with flask_app.test_client() as client:
        # Make the GET request to the endpoint
        response = client.get('/api/sailors-for-onwater')
        data = response.get_json()
        
        print(f"Status: {data.get('status')}")
        if data.get('status') == 'success':
            columns = data.get('columns', [])
            print(f"Number of columns: {len(columns)}")
            for i, col in enumerate(columns):
                sailors = col.get('sailors', [])
                print(f"Column {i+1}: '{col.get('class_name')}' (seq={col.get('sequence_number', 'N/A')}, color={col.get('color_hex', 'N/A')})")
                print(f"  Sailors: {len(sailors)}")
                for sailor in sailors:
                    print(f"    - {sailor.get('short_name')} ({sailor.get('boat_class')})")
        else:
            print(f"Error: {data}")

if __name__ == "__main__":
    test_sailors_for_onwater()