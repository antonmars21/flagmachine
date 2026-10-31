#!/usr/bin/env python3
import sqlite3
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app to access app_state and functions
import app
from app import app_state, get_db_connection, get_active_class_ids_from_sequence, get_class_sequence_mapping

def test_finish_sheet_logic():
    print("=== Testing Finish Sheet Logic ===\n")
    
    # Initialize a test app_state with some sequence data
    app_state['sequence'] = [
        {'id': 'row_1', 'label': 'ILCA 6', 'flag_image': 'ilca6.png', 'grid_index': 1, 'status': 'PENDING'},
        {'id': 'row_2', 'label': 'Starling', 'flag_image': 'starling.png', 'grid_index': 1, 'status': 'PENDING'},
        {'id': 'row_3', 'label': 'Optimist', 'flag_image': 'optimist.png', 'grid_index': 2, 'status': 'PENDING'},
    ]
    
    app_state['race_id'] = None
    app_state['class_start_times'] = {}
    
    print("1. Testing get_active_class_ids_from_sequence():")
    active_class_ids = get_active_class_ids_from_sequence()
    print(f"   Active class IDs: {active_class_ids}")
    
    print("\n2. Testing get_class_sequence_mapping():")
    class_sequence_mapping = get_class_sequence_mapping()
    print(f"   Class sequence mapping: {class_sequence_mapping}")
    
    print("\n3. Database check - boat_classes:")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT class_id, class_name, flag_image FROM boat_classes')
    classes = c.fetchall()
    print(f"   Found {len(classes)} boat classes:")
    for cls in classes:
        print(f"     {cls['class_id']}: {cls['class_name']} ({cls['flag_image']})")
    
    print("\n4. Database check - sailors with racing_today=1:")
    c.execute('SELECT uid, sail_no, short_name, boat_class, class_id FROM sailors WHERE racing_today = 1')
    sailors = c.fetchall()
    print(f"   Found {len(sailors)} sailors marked as racing today:")
    for sailor in sailors[:5]:  # Show first 5
        print(f"     {sailor['uid']}: {sailor['short_name']} ({sailor['boat_class']}, class_id={sailor['class_id']})")
    if len(sailors) > 5:
        print(f"     ... and {len(sailors) - 5} more")
    
    conn.close()
    
    print("\n5. Testing sailors_for_onwater logic:")
    # Simulate the grouping logic
    race_id = app_state.get('race_id')
    active_class_ids_test = get_active_class_ids_from_sequence()
    class_start_times = app_state.get('class_start_times', {})
    started_class_ids = {int(cid) for cid in class_start_times.keys()}
    class_sequence_mapping_test = get_class_sequence_mapping()
    
    print(f"   Active class IDs: {active_class_ids_test}")
    print(f"   Started class IDs: {started_class_ids}")
    print(f"   Class sequence mapping: {class_sequence_mapping_test}")
    
    # Check what sailors would be returned
    conn = get_db_connection()
    c = conn.cursor()
    
    if race_id and started_class_ids:
        print("   Would query started classes...")
    else:
        print("   No race started yet, would query live sailors...")
    
    # Get live sailors
    if started_class_ids:
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed,
                   0 as lap_count, NULL as finish_time, NULL as placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex,
                   NULL as sequence_number
            FROM sailors s
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            WHERE s.racing_today = 1 AND (s.class_id IS NULL OR s.class_id NOT IN ({}))
            ORDER BY s.boat_class, s.seed
        '''.format(','.join('?' * len(started_class_ids))), tuple(started_class_ids))
    else:
        c.execute('''
            SELECT s.uid, s.sail_no, s.short_name, s.boat_class, s.seed,
                   0 as lap_count, NULL as finish_time, NULL as placement,
                   bc.class_id, bc.class_name, bc.flag_image, bc.color_hex,
                   NULL as sequence_number
            FROM sailors s
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            WHERE s.racing_today = 1
            ORDER BY s.boat_class, s.seed
        ''')
    
    live_rows = c.fetchall()
    print(f"   Live rows: {len(live_rows)}")
    
    # Test grouping logic
    sequence_groups = {}
    open_category_sailors = []
    
    for row in live_rows:
        class_id = row['class_id']
        print(f"   Processing sailor: {row['short_name']} (class_id={class_id})")
        
        if class_id is None:
            print(f"     -> Open category (class_id is None)")
            open_category_sailors.append({'uid': row['uid'], 'short_name': row['short_name']})
        elif active_class_ids_test and class_id in active_class_ids_test:
            sequence_number = row['sequence_number'] if row['sequence_number'] is not None else class_sequence_mapping_test.get(class_id, 1)
            group_key = (class_id, sequence_number)
            print(f"     -> Sequence group {group_key} (class in active sequence)")
            if group_key not in sequence_groups:
                sequence_groups[group_key] = {
                    'class_id': class_id,
                    'class_name': row['class_name'],
                    'sequence_number': sequence_number,
                    'sailors': []
                }
            sequence_groups[group_key]['sailors'].append({'uid': row['uid'], 'short_name': row['short_name']})
        elif not active_class_ids_test:
            sequence_number = row['sequence_number'] if row['sequence_number'] is not None else class_sequence_mapping_test.get(class_id, 1)
            group_key = (class_id, 1)
            print(f"     -> Sequence group {group_key} (no active sequence, class only)")
            if group_key not in sequence_groups:
                sequence_groups[group_key] = {
                    'class_id': class_id,
                    'class_name': row['class_name'],
                    'sequence_number': 1,
                    'sailors': []
                }
            sequence_groups[group_key]['sailors'].append({'uid': row['uid'], 'short_name': row['short_name']})
        else:
            print(f"     -> Open category (class {class_id} not in active sequence)")
            open_category_sailors.append({'uid': row['uid'], 'short_name': row['short_name']})
    
    conn.close()
    
    print(f"\n   Result: {len(sequence_groups)} sequence groups, {len(open_category_sailors)} in open category")
    for key, group in sequence_groups.items():
        print(f"     Group {key}: {len(group['sailors'])} sailors")
    
    if open_category_sailors:
        print(f"     Open Category: {len(open_category_sailors)} sailors")

if __name__ == "__main__":
    test_finish_sheet_logic()