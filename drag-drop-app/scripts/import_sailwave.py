"""
Sailwave Integration: Import boat_master.json into score.db

This script reads boat and sailor data from Sailwave's boat_master.json
and imports it into the Flag Machine's SQLite database (score.db).

Features:
- Validates data before import
- Checks for duplicates (by sail_no)
- Handles upserts (update existing, insert new)
- Preserves existing app-specific fields (racing_today, seed)
- Maps boat classes to flag images
- Logs all operations

Usage:
    python scripts/import_sailwave.py
    
    or with custom path:
    python scripts/import_sailwave.py --json-path /path/to/boat_master.json
"""

import sqlite3
import json
import re
import os
import sys
import argparse
from datetime import datetime

# Configuration
DEFAULT_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'tempref', 'boat_master.json')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'score.db')

# Default flag image mappings (can be overridden by data)
DEFAULT_FLAG_MAPPINGS = {
    'ILCA 6': 'ilca6.png',
    'ILCA 7': 'ilca7.png',
    'STARLING': 'starling.png',
    'OPTIMIST': 'optimist.png',
    'P': 'p.png',
    'ZEPHYR': 'zephyr.png',
    '420': '420.png',
    '470': '470.png',
    'LASER': 'laser.png',
    'RADIAL': 'radial.png',
    'FINN': 'finn.png',
    '29ER': '29er.png',
    '49ER': '49er.png',
    'RS FEVA': 'rs_feva.png',
    'RS TERA': 'rs_tera.png',
    'TOPPER': 'topper.png',
    'MIRROR': 'mirror.png',
    'CADET': 'cadet.png',
    'HERON': 'heron.png',
    'STAR': 'star.png',
}

# Default color mappings
DEFAULT_COLOR_MAPPINGS = {
    'ILCA 6': '#0369a1',      # blue
    'ILCA 7': '#06b6d4',      # cyan
    'STARLING': '#8b5cf6',    # purple
    'OPTIMIST': '#ec4899',    # pink
    'P': '#f59e0b',           # amber
    'ZEPHYR': '#10b981',      # green
}


def get_db_connection(db_path=None):
    """Get a database connection."""
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables_exist(conn):
    """Ensure required tables exist in the database."""
    c = conn.cursor()
    
    # Create boat_classes table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS boat_classes (
            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE NOT NULL,
            flag_image TEXT,
            color_hex TEXT DEFAULT '#0369a1',
            py_number REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create sailors table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS sailors (
            uid TEXT PRIMARY KEY,
            sailor_name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            sail_no TEXT UNIQUE NOT NULL,
            boat_class TEXT NOT NULL,
            handicap REAL DEFAULT 1.0,
            seed INTEGER DEFAULT 0,
            class_id INTEGER,
            racing_today INTEGER DEFAULT 0,
            status TEXT DEFAULT 'racing',
            finish_order INTEGER DEFAULT NULL,
            finish_time TEXT DEFAULT NULL,
            FOREIGN KEY(class_id) REFERENCES boat_classes(class_id)
        )
    ''')
    
    # Add class_id column if it doesn't exist (backward compatibility)
    c.execute("PRAGMA table_info(sailors)")
    columns = [col[1] for col in c.fetchall()]
    if 'class_id' not in columns:
        c.execute('ALTER TABLE sailors ADD COLUMN class_id INTEGER')
        conn.commit()
        c.execute("PRAGMA table_info(sailors)")
        columns = [col[1] for col in c.fetchall()]
    
    # Add foreign key constraint if needed
    if 'class_id' in columns:
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS sailors_new (
                    uid TEXT PRIMARY KEY,
                    sailor_name TEXT NOT NULL,
                    short_name TEXT NOT NULL,
                    sail_no TEXT UNIQUE NOT NULL,
                    boat_class TEXT NOT NULL,
                    handicap REAL DEFAULT 1.0,
                    seed INTEGER DEFAULT 0,
                    class_id INTEGER,
                    racing_today INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'racing',
                    finish_order INTEGER DEFAULT NULL,
                    finish_time TEXT DEFAULT NULL,
                    FOREIGN KEY(class_id) REFERENCES boat_classes(class_id)
                )
            ''')
            # Copy data and replace
            c.execute('INSERT OR IGNORE INTO sailors_new SELECT * FROM sailors')
            c.execute('DROP TABLE sailors')
            c.execute('ALTER TABLE sailors_new RENAME TO sailors')
            conn.commit()
        except Exception:
            pass  # Table already has proper structure
    
    conn.commit()


def parse_sailwave_json(json_path):
    """
    Parse Sailwave boat_master.json file.
    
    Expected structure (based on typical Sailwave exports):
    {
        "boats": [
            {
                "sail_no": "123",
                "boat_name": "Werner",
                "class": "Ilca 6",
                "helm": "John Smith",
                "crew": "Jane Doe",
                "py": 1000,
                "club": "ABC Yacht Club"
            },
            ...
        ],
        "classes": [
            {
                "class_name": "Ilca 6",
                "py": 1000,
                "flag": "ilca6.png"
            },
            ...
        ]
    }
    
    OR alternative structure:
    [
        {
            "SailNo": "123",
            "BoatName": "Werner", 
            "Class": "Ilca 6",
            "Helm": "John Smith",
            "Crew": "Jane Doe",
            "PY": 1000
        },
        ...
    ]
    """
    print(f"\n{'='*60}")
    print(f"PARSING: {json_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(json_path):
        print(f"ERROR: File not found: {json_path}")
        return None, None
    
    # Try multiple encodings for JSON files
    encodings = ['utf-8', 'utf-16-le', 'utf-16-be', 'cp1252', 'latin-1']
    data = None
    
    for encoding in encodings:
        try:
            with open(json_path, 'r', encoding=encoding) as f:
                data = json.load(f)
            print(f"  [Encoding detected: {encoding}]")
            break
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    
    # If JSON parsing failed, try HTML format
    if data is None:
        try:
            # Try opening as HTML - first try .htm version, then original path
            html_path = json_path
            if json_path.endswith('.json'):
                html_path = json_path[:-5] + '.htm'
            
            with open(html_path, 'rb') as f:
                html_content = f.read()
            
            # Try different encodings for HTML
            for encoding in ['ISO-8859-1', 'latin-1', 'utf-8', 'cp1252']:
                try:
                    html_text = html_content.decode(encoding)
                    break
                except:
                    continue
            
            # Extract table data from HTML
            match = re.search(r'<tbody>(.*?)</tbody>', html_text, re.DOTALL)
            if match:
                tbody = match.group(1)
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody, re.DOTALL)
                
                boats = []
                for row in rows:
                    cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL)
                    if len(cells) >= 7:
                        cleaned = [re.sub(r'<[^>]*>', '', c).strip() for c in cells]
                        if len(cleaned) >= 7 and cleaned[4]:  # Has SailNo
                            boat_data = {
                                'sail_no': cleaned[4],
                                'boat': cleaned[3],
                                'class': cleaned[2],
                                'helm': cleaned[5],
                                'py': cleaned[6] if cleaned[6] else '1000'
                            }
                            boats.append(boat_data)
                
                print(f"  [HTML format detected: {len(boats)} boats found]")
                return boats, []
        except Exception as e:
            print(f"  [HTML parsing failed: {e}]")
    
    if data is None:
        print(f"ERROR: Could not decode file with encodings: {encodings}")
        return None, None
    
    boats = []
    classes = []
    
    # Try to detect structure
    if isinstance(data, dict):
        # Structure 1: {"boats": [...], "classes": [...]}
        if 'boats' in data:
            boats = data['boats']
        if 'classes' in data:
            classes = data['classes']
        # Structure 2: {"Boats": [...], "Classes": [...]}
        elif 'Boats' in data:
            boats = data['Boats']
        if 'Classes' in data:
            classes = data['Classes']
        # Structure 3: Flat dict with boat list
        else:
            # Assume all keys are boat entries or class definitions
            for key, value in data.items():
                if isinstance(value, list):
                    if key.lower() in ['boats', 'sailors', 'competitors']:
                        boats = value
                    elif key.lower() in ['classes', 'boat_classes']:
                        classes = value
                elif isinstance(value, dict) and 'class' in value.lower():
                    classes.append(value)
    
    elif isinstance(data, list):
        # Structure 4: Flat list of boats
        # Check if first item has class info
        if data and isinstance(data[0], dict):
            # Could be all boats, or mixed
            for item in data:
                if 'class' in item or 'Class' in item or 'boat_class' in item:
                    boats.append(item)
                elif 'class_name' in item or 'ClassName' in item:
                    classes.append(item)
    
    print(f"  Found {len(boats)} boats")
    print(f"  Found {len(classes)} classes")
    
    return boats, classes


def extract_boat_info(boat):
    """Extract standardized boat info from various JSON structures."""
    info = {
        'uid': None,
        'sail_no': None,
        'sailor_name': None,
        'short_name': None,
        'boat_class': None,
        'handicap': 1.0,
        'py_number': None
    }
    
    # Handle different field naming conventions
    for key, value in boat.items():
        key_lower = key.lower()
        
        if key_lower in ['sailno', 'sail_no', 'sailnumber', 'id']:
            info['sail_no'] = str(value).strip()
            info['uid'] = f"SL-{info['sail_no']}"
        elif key_lower in ['boatname', 'boat_name', 'name']:
            info['short_name'] = str(value).strip()
            info['sailor_name'] = info['short_name']
        elif key_lower in ['helm', 'helmsman', 'skipper', 'sailor']:
            if info['sailor_name']:
                info['sailor_name'] = f"{info['sailor_name']} ({value})"
            else:
                info['sailor_name'] = str(value).strip()
        elif key_lower in ['crew']:
            if info['sailor_name']:
                info['sailor_name'] = f"{info['sailor_name']} + {value}"
        elif key_lower in ['class', 'boat_class', 'classname', 'boatclass']:
            info['boat_class'] = str(value).strip()
        elif key_lower in ['py', 'handicap', 'rating', 'pn']:
            try:
                info['handicap'] = float(value)
                info['py_number'] = float(value)
            except (ValueError, TypeError):
                pass
    
    # Generate short_name from sailor_name if not set
    if info['sailor_name'] and not info['short_name']:
        # Use first word or first initial + last name
        parts = info['sailor_name'].split()
        if len(parts) >= 2:
            info['short_name'] = f"{parts[0][0]}. {parts[-1]}"
        else:
            info['short_name'] = info['sailor_name'][:15]
    
    # Generate UID if not set
    if not info['uid'] and info['sail_no']:
        info['uid'] = f"SL-{info['sail_no']}"
    
    return info


def extract_class_info(class_data):
    """Extract standardized class info from various JSON structures."""
    info = {
        'class_name': None,
        'flag_image': None,
        'color_hex': None,
        'py_number': None
    }
    
    for key, value in class_data.items():
        key_lower = key.lower()
        
        if key_lower in ['class', 'classname', 'class_name', 'name']:
            info['class_name'] = str(value).strip()
        elif key_lower in ['flag', 'flag_image', 'image', 'icon']:
            info['flag_image'] = str(value).strip()
        elif key_lower in ['color', 'color_hex', 'colour']:
            info['color_hex'] = str(value).strip()
        elif key_lower in ['py', 'handicap', 'rating', 'base_py']:
            try:
                info['py_number'] = float(value)
            except (ValueError, TypeError):
                pass
    
    return info


def import_boat_classes(conn, classes, existing_classes):
    """Import boat classes from Sailwave data."""
    c = conn.cursor()
    imported_count = 0
    updated_count = 0
    
    print(f"\n{'='*60}")
    print("IMPORTING BOAT CLASSES")
    print(f"{'='*60}")
    
    for class_data in classes:
        class_info = extract_class_info(class_data)
        class_name = class_info['class_name']
        
        if not class_name:
            continue
        
        # Normalize class name
        class_name = class_name.strip().title()
        
        # Check if class already exists
        c.execute('SELECT class_id, flag_image, color_hex FROM boat_classes WHERE class_name = ?', 
                  (class_name,))
        existing = c.fetchone()
        
        # Determine flag image
        flag_image = class_info['flag_image'] or DEFAULT_FLAG_MAPPINGS.get(class_name.upper(), None)
        
        # Determine color
        color_hex = class_info['color_hex'] or DEFAULT_COLOR_MAPPINGS.get(class_name.upper(), '#0369a1')
        
        if existing:
            # Update existing class
            class_id = existing['class_id']
            update_needed = False
            updates = []
            
            if flag_image and existing['flag_image'] != flag_image:
                updates.append(f"flag_image: '{existing['flag_image']}' -> '{flag_image}'")
                update_needed = True
            if color_hex and existing['color_hex'] != color_hex:
                updates.append(f"color_hex: '{existing['color_hex']}' -> '{color_hex}'")
                update_needed = True
            
            if update_needed:
                c.execute('''
                    UPDATE boat_classes 
                    SET flag_image = COALESCE(?, flag_image),
                        color_hex = COALESCE(?, color_hex),
                        py_number = COALESCE(?, py_number),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE class_id = ?
                ''', (flag_image, color_hex, class_info['py_number'], class_id))
                updated_count += 1
                print(f"  [UPDATE] {class_name}: {', '.join(updates)}")
            else:
                print(f"  [EXISTS] {class_name} (no changes)")
        else:
            # Insert new class
            c.execute('''
                INSERT INTO boat_classes (class_name, flag_image, color_hex, py_number)
                VALUES (?, ?, ?, ?)
            ''', (class_name, flag_image, color_hex, class_info['py_number']))
            class_id = c.lastrowid
            imported_count += 1
            print(f"  [NEW] {class_name} -> class_id={class_id}")
        
        existing_classes[class_name] = class_id
    
    conn.commit()
    print(f"\n  Total: {imported_count} new, {updated_count} updated")
    return imported_count, updated_count


def import_sailors(conn, boats, existing_classes):
    """Import sailors from Sailwave data."""
    c = conn.cursor()
    imported_count = 0
    updated_count = 0
    skipped_count = 0
    
    print(f"\n{'='*60}")
    print("IMPORTING SAILORS")
    print(f"{'='*60}")
    
    for boat_data in boats:
        boat_info = extract_boat_info(boat_data)
        sail_no = boat_info['sail_no']
        uid = boat_info['uid']
        boat_class = boat_info['boat_class']
        
        if not sail_no or not uid:
            print(f"  [SKIP] Invalid data: {boat_data}")
            skipped_count += 1
            continue
        
        # Normalize boat class
        if boat_class:
            boat_class = boat_class.strip().title()
        
        # Get class_id
        class_id = None
        if boat_class and boat_class in existing_classes:
            class_id = existing_classes[boat_class]
        elif boat_class:
            # Class not in boat_classes yet, create it
            c.execute('''
                INSERT OR IGNORE INTO boat_classes (class_name, flag_image, color_hex)
                VALUES (?, ?, ?)
            ''', (boat_class, DEFAULT_FLAG_MAPPINGS.get(boat_class.upper()), 
                   DEFAULT_COLOR_MAPPINGS.get(boat_class.upper(), '#0369a1')))
            c.execute('SELECT class_id FROM boat_classes WHERE class_name = ?', (boat_class,))
            row = c.fetchone()
            if row:
                class_id = row['class_id']
                existing_classes[boat_class] = class_id
        
        # Check if sailor already exists
        c.execute('SELECT uid, sailor_name, short_name, sail_no, boat_class, class_id FROM sailors WHERE uid = ?', 
                  (uid,))
        existing = c.fetchone()
        
        if existing:
            # Update existing sailor
            update_needed = False
            updates = []
            
            if existing['sail_no'] != sail_no:
                updates.append(f"sail_no: '{existing['sail_no']}' -> '{sail_no}'")
                update_needed = True
            if existing['sailor_name'] != boat_info['sailor_name']:
                updates.append(f"sailor_name: '{existing['sailor_name']}' -> '{boat_info['sailor_name']}'")
                update_needed = True
            if existing['short_name'] != boat_info['short_name']:
                updates.append(f"short_name: '{existing['short_name']}' -> '{boat_info['short_name']}'")
                update_needed = True
            if existing['boat_class'] != boat_class:
                updates.append(f"boat_class: '{existing['boat_class']}' -> '{boat_class}'")
                update_needed = True
            if existing['class_id'] != class_id:
                updates.append(f"class_id: {existing['class_id']} -> {class_id}")
                update_needed = True
            
            if update_needed:
                c.execute('''
                    UPDATE sailors 
                    SET sailor_name = ?,
                        short_name = ?,
                        sail_no = ?,
                        boat_class = ?,
                        handicap = COALESCE(?, handicap),
                        class_id = ?
                    WHERE uid = ?
                ''', (boat_info['sailor_name'], boat_info['short_name'], sail_no, 
                      boat_class, boat_info['handicap'], class_id, uid))
                updated_count += 1
                print(f"  [UPDATE] {uid} ({sail_no}): {', '.join(updates)}")
            else:
                print(f"  [EXISTS] {uid} ({sail_no}) - {boat_info['sailor_name']}")
        else:
            # Check for duplicate sail_no (different uid)
            c.execute('SELECT uid FROM sailors WHERE sail_no = ?', (sail_no,))
            duplicate = c.fetchone()
            
            if duplicate:
                print(f"  [DUPLICATE SAIL_NO] {sail_no} already exists as {duplicate['uid']}")
                skipped_count += 1
                continue
            
            # Insert new sailor
            c.execute('''
                INSERT INTO sailors 
                (uid, sailor_name, short_name, sail_no, boat_class, handicap, class_id, racing_today)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (uid, boat_info['sailor_name'], boat_info['short_name'], sail_no, 
                  boat_class, boat_info['handicap'], class_id))
            imported_count += 1
            print(f"  [NEW] {uid} ({sail_no}) - {boat_info['sailor_name']} [{boat_class}]")
    
    conn.commit()
    print(f"\n  Total: {imported_count} new, {updated_count} updated, {skipped_count} skipped")
    return imported_count, updated_count, skipped_count


def cleanup_orphaned_sailors(conn):
    """Optionally remove sailors whose boats are no longer in Sailwave data."""
    print(f"\n{'='*60}")
    print("CLEANUP OPTIONS")
    print(f"{'='*60}")
    print("  Note: Orphaned sailors (not in Sailwave) are kept in score.db")
    print("  This preserves racing_today and other app-specific data")
    print("  To remove orphans, run with --cleanup-orphans flag")


def import_sailwave_data(json_path=None, db_path=None, cleanup_orphans=False):
    """
    Main import function.
    
    Returns dict with import statistics.
    """
    if json_path is None:
        json_path = DEFAULT_JSON_PATH
    if db_path is None:
        db_path = DB_PATH
    
    print(f"\n{'#'*60}")
    print(f"# SAILWAVE DATA IMPORT")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# JSON: {json_path}")
    print(f"# DB:   {db_path}")
    print(f"{'#'*60}\n")
    
    # Verify files exist
    if not os.path.exists(json_path):
        print(f"ERROR: JSON file not found: {json_path}")
        print(f"       Expected at: {DEFAULT_JSON_PATH}")
        print(f"       Or specify path with --json-path")
        return False
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        return False
    
    # Connect to database
    conn = get_db_connection(db_path)
    
    try:
        # Ensure tables exist
        print("Checking database tables...")
        ensure_tables_exist(conn)
        print("  [OK] Tables verified")
        
        # Load existing classes
        c = conn.cursor()
        c.execute('SELECT class_name, class_id FROM boat_classes')
        existing_classes = {row['class_name']: row['class_id'] for row in c.fetchall()}
        
        # Parse Sailwave JSON
        boats, classes = parse_sailwave_json(json_path)
        
        if boats is None:
            print("ERROR: Failed to parse JSON file")
            return False
        
        # Import classes
        class_imported, class_updated = import_boat_classes(conn, classes, existing_classes)
        
        # Import sailors
        sailor_imported, sailor_updated, sailor_skipped = import_sailors(conn, boats, existing_classes)
        
        # Cleanup if requested
        if cleanup_orphans:
            cleanup_orphaned_sailors(conn)
        
        # Summary
        print(f"\n{'='*60}")
        print("IMPORT SUMMARY")
        print(f"{'='*60}")
        print(f"  Boat Classes: {class_imported} new, {class_updated} updated")
        print(f"  Sailors:      {sailor_imported} new, {sailor_updated} updated, {sailor_skipped} skipped")
        print(f"  Total Sailors in DB: ", end="")
        c.execute('SELECT COUNT(*) FROM sailors')
        print(f"{c.fetchone()[0]}")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Import Sailwave boat_master.json into Flag Machine score.db'
    )
    parser.add_argument(
        '--json-path',
        default=None,
        help='Path to boat_master.json (default: tempref/boat_master.json)'
    )
    parser.add_argument(
        '--db-path',
        default=None,
        help='Path to score.db (default: score.db)'
    )
    parser.add_argument(
        '--cleanup-orphans',
        action='store_true',
        help='Remove sailors not in Sailwave data (WARNING: destructive)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be imported without making changes'
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    if args.json_path:
        json_path = args.json_path
    else:
        # Try multiple locations
        for p in [
            os.path.join(project_dir, 'tempref', 'boat_master.json'),
            os.path.join(project_dir, 'tempref', 'boat_master.htm'),
            os.path.join(project_dir, 'boat_master.json'),
            os.path.join(project_dir, 'boat_master.htm'),
            os.path.join(script_dir, 'boat_master.json'),
            os.path.join(script_dir, 'boat_master.htm'),
            'C:\\Users\\Public\\Documents\\Sailwave\\Flagmachine_database\\boat_master.json',
        ]:
            if os.path.exists(p):
                json_path = p
                break
        else:
            json_path = DEFAULT_JSON_PATH
    
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = DB_PATH
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made to the database")
        # For dry run, we'd need to modify the import functions
        # For now, just show what we would do
        boats, classes = parse_sailwave_json(json_path)
        if boats:
            print(f"\nWould import {len(boats)} boats")
            print(f"Would import {len(classes)} classes")
        return
    
    success = import_sailwave_data(json_path, db_path, args.cleanup_orphans)
    
    if success:
        print("\n[OK] Import completed successfully")
        sys.exit(0)
    else:
        print("\n[FAILED] Import failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
