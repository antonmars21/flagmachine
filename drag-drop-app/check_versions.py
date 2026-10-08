#!/usr/bin/env python3
"""
Version Check Script for Drag-Drop App
Checks code versions and database schema consistency
"""
import os
import sqlite3
from datetime import datetime

def check_file_versions():
    """Check modification times of key files"""
    print("=== FILE VERSIONS (Last Modified) ===\n")
    
    key_files = [
        'app.py',
        'templates/index.html',
        'templates/finishsheet.html',
        'static/js/app.js',
        'static/js/finishsheet.js',
        'static/css/style.css',
        'score.db'
    ]
    
    for file_path in key_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            mtime = os.path.getmtime(full_path)
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = os.path.getsize(full_path)
            print(f"  {file_path:30} {date_str} ({size:,} bytes)")
        else:
            print(f"  {file_path:30} NOT FOUND")
    print()

def check_database_schema():
    """Check database schema and data"""
    print("=== DATABASE SCHEMA ===\n")
    
    try:
        conn = sqlite3.connect('score.db')
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  Tables: {', '.join(tables)}")
        
        # Check boat_classes
        cursor.execute("PRAGMA table_info(boat_classes)")
        columns = cursor.fetchall()
        print(f"\n  boat_classes columns:")
        for col in columns:
            print(f"    - {col[1]} ({col[2]})")
        
        cursor.execute("SELECT COUNT(*) FROM boat_classes")
        count = cursor.fetchone()[0]
        print(f"    Row count: {count}")
        
        # Check race_class_starts
        cursor.execute("PRAGMA table_info(race_class_starts)")
        columns = cursor.fetchall()
        print(f"\n  race_class_starts columns:")
        for col in columns:
            print(f"    - {col[1]} ({col[2]})")
        
        cursor.execute("SELECT COUNT(*) FROM race_class_starts")
        count = cursor.fetchone()[0]
        print(f"    Row count: {count}")
        
        # Check sailors
        cursor.execute("SELECT COUNT(*) FROM sailors")
        count = cursor.fetchone()[0]
        print(f"\n  sailors total: {count}")
        
        cursor.execute("SELECT COUNT(*) FROM sailors WHERE racing_today = 1")
        count = cursor.fetchone()[0]
        print(f"  sailors with racing_today=1: {count}")
        
        # Check class_id distribution
        cursor.execute("SELECT class_id, COUNT(*) as cnt FROM sailors WHERE racing_today = 1 GROUP BY class_id")
        class_dist = cursor.fetchall()
        print(f"  racing sailors by class: {dict(class_dist)}")
        
        conn.close()
        
    except Exception as e:
        print(f"  ERROR: {e}")
    print()

def check_session_5_features():
    """Check if Session 5 features are implemented"""
    print("=== SESSION 5 FEATURE CHECK ===\n")
    
    features = {
        "Dynamic grid creation": "templates/index.html" in open("templates/index.html").read() and "btn-add-grid" in open("templates/index.html").read(),
        "Grid removal buttons": "btn-remove-grid" in open("templates/index.html").read(),
        "Dynamic CSS grid": "repeat(auto-fit" in open("templates/finishsheet.html").read(),
        "Sequence number in API": "sequence_number" in open("app.py").read(),
        "Lap times API": "/api/lap-times" in open("app.py").read(),
        "Enhanced CSV export": "Lap Times" in open("app.py").read(),
        "Sequence grouping": "get_class_sequence_mapping" in open("app.py").read()
    }
    
    for feature, implemented in features.items():
        status = "✅" if implemented else "❌"
        print(f"  {status} {feature}")
    print()

def check_code_consistency():
    """Check for common issues in the code"""
    print("=== CODE CONSISTENCY CHECK ===\n")
    
    # Check for .get() on Row objects
    with open("app.py", "r") as f:
        content = f.read()
        if "row.get(" in content:
            print("  ⚠️  Potential issue: Found row.get() calls (should use row['col'])")
        else:
            print("  ✅ No row.get() calls found")
    
    # Check for sequence_number usage
    if "sequence_number" in content:
        print("  ✅ sequence_number implemented")
    else:
        print("  ❌ sequence_number not found")
    
    # Check for grid_index usage
    if "grid_index" in content:
        print("  ✅ grid_index implemented")
    else:
        print("  ❌ grid_index not found")
    
    print()

def main():
    print("Drag-Drop App Version Check")
    print("=" * 50)
    print()
    
    check_file_versions()
    check_database_schema()
    check_session_5_features()
    check_code_consistency()
    
    print("Version check complete!")

if __name__ == "__main__":
    main()