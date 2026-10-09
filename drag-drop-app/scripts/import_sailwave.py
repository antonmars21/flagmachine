"""
Sailwave Integration: Import Boats_Master.xml into score.db

This script reads competitor data from Sailwave's Boats_Master.xml export
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
    python scripts/import_sailwave.py --xml-path /path/to/Boats_Master.xml
"""

import sqlite3
import xml.etree.ElementTree as ET
import os
import sys
import argparse
from datetime import datetime

# Configuration
SAILWAVE_DB_FOLDER = r'C:\Users\Public\Documents\Sailwave\Flagmachine_database'
DEFAULT_XML_PATH = os.path.join(SAILWAVE_DB_FOLDER, 'Boats_Master.xml')
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


def parse_sailwave_xml(xml_path):
    """
    Parse a Sailwave Boats_Master.xml export.

    Expected structure:
    <sailwave-data>
      <header>...</header>
      <competitors>
        <competitor handle="111">
          <compboat>Philomene</compboat>
          <compsailno>54</compsailno>
          <compclass>Zephyr</compclass>
          <comphelmname>Ray Oxborrow</comphelmname>
          <comprating>4</comprating>
          ...
        </competitor>
      </competitors>
    </sailwave-data>

    Returns (boats, classes). Each boat is a dict keyed by child tag name,
    which extract_boat_info maps onto sailor fields. Strict XML: a malformed
    file raises a ParseError instead of being silently patched up.
    """
    print(f"\n{'='*60}")
    print(f"PARSING: {xml_path}")
    print(f"{'='*60}")

    if not os.path.exists(xml_path):
        print(f"ERROR: File not found: {xml_path}")
        return None, None

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        print(f"ERROR: XML is not well-formed: {e}")
        return None, None

    root = tree.getroot()

    boats = []
    for comp in root.findall('./competitors/competitor'):
        fields = {child.tag: (child.text or '').strip() for child in comp}
        fields['handle'] = comp.get('handle')
        boats.append(fields)

    print(f"  Found {len(boats)} competitors")
    return boats, []


def extract_boat_info(boat):
    """Extract standardized boat info from Sailwave competitor fields."""
    info = {
        'uid': None,
        'sail_no': None,
        'sailor_name': None,
        'short_name': None,
        'helm_name': None,
        'boat_class': None,
        'handicap': 1.0,
        'py_number': None
    }
    
    # Handle different field naming conventions
    for key, value in boat.items():
        # Skip empty tags (Sailwave XML exports many unused fields)
        if value is None or not str(value).strip():
            continue
        key_lower = key.lower()
        
        if key_lower in ['sailno', 'sail_no', 'sailnumber', 'id', 'compsailno']:
            info['sail_no'] = str(value).strip()
            info['uid'] = f"SL-{info['sail_no']}"
        elif key_lower in ['compboat']:
            # Sailwave competitor boat name - kept for reference only
            info['boat_name'] = str(value).strip()
        elif key_lower in ['boatname', 'boat_name', 'name']:
            info['short_name'] = str(value).strip()
            info['sailor_name'] = info['short_name']
        elif key_lower in ['helm', 'helmsman', 'skipper', 'sailor', 'comphelmname']:
            info['helm_name'] = str(value).strip()
            if info['sailor_name']:
                info['sailor_name'] = f"{info['sailor_name']} ({value})"
            else:
                info['sailor_name'] = str(value).strip()
        elif key_lower in ['crew', 'compcrewname']:
            if info['sailor_name']:
                info['sailor_name'] = f"{info['sailor_name']} + {value}"
        elif key_lower in ['class', 'boat_class', 'classname', 'boatclass', 'compclass']:
            # compclass holds the division (e.g. 'ILCA 6'); compfleet is the
            # coarse fleet (e.g. 'ILCA') and is deliberately not used
            info['boat_class'] = str(value).strip()
        elif key_lower in ['py', 'handicap', 'rating', 'pn', 'comprating']:
            try:
                info['handicap'] = float(value)
                info['py_number'] = float(value)
            except (ValueError, TypeError):
                pass
    
    # Use the sailor's first name as the short_name
    name_source = info['helm_name'] or info['sailor_name']
    if name_source:
        parts = name_source.split()
        info['short_name'] = parts[0] if parts else name_source[:15]
    
    # Generate UID if not set
    if not info['uid'] and info['sail_no']:
        info['uid'] = f"SL-{info['sail_no']}"
    
    return info


def extract_class_info(class_data):
    """Extract standardized class info from Sailwave class fields."""
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


def import_sailwave_data(xml_path=None, db_path=None, cleanup_orphans=False):
    """
    Main import function.
    
    Returns dict with import statistics.
    """
    if xml_path is None:
        xml_path = DEFAULT_XML_PATH
    if db_path is None:
        db_path = DB_PATH
    
    print(f"\n{'#'*60}")
    print(f"# SAILWAVE DATA IMPORT")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# XML: {xml_path}")
    print(f"# DB:   {db_path}")
    print(f"{'#'*60}\n")
    
    # Verify files exist
    if not os.path.exists(xml_path):
        print(f"ERROR: XML file not found: {xml_path}")
        print(f"       Expected at: {DEFAULT_XML_PATH}")
        print(f"       Or specify path with --xml-path")
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
        
        # Parse the Sailwave XML export
        boats, classes = parse_sailwave_xml(xml_path)
        
        if boats is None:
            print("ERROR: Failed to parse XML file")
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
        description='Import Sailwave Boats_Master.xml into Flag Machine score.db'
    )
    parser.add_argument(
        '--xml-path',
        default=None,
        help=f'Path to Boats_Master.xml (default: {DEFAULT_XML_PATH})'
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
    
    if args.xml_path:
        xml_path = args.xml_path
    else:
        # Seek the Sailwave XML export - public database folder first
        for p in [
            os.path.join(SAILWAVE_DB_FOLDER, 'Boats_Master.xml'),
            os.path.join(SAILWAVE_DB_FOLDER, 'boat_master.xml'),
            os.path.join(project_dir, 'tempref', 'Boats_Master.xml'),
        ]:
            if os.path.exists(p):
                xml_path = p
                break
        else:
            xml_path = DEFAULT_XML_PATH
    
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = DB_PATH
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made to the database")
        # For dry run, we'd need to modify the import functions
        # For now, just show what we would do
        boats, classes = parse_sailwave_xml(xml_path)
        if boats:
            print(f"\nWould import {len(boats)} boats")
            print(f"Would import {len(classes)} classes")
        return
    
    success = import_sailwave_data(xml_path, db_path, args.cleanup_orphans)
    
    if success:
        print("\n[OK] Import completed successfully")
        sys.exit(0)
    else:
        print("\n[FAILED] Import failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
