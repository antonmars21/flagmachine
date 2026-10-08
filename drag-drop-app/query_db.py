#!/usr/bin/env python3
import sqlite3
import sys

def query_database():
    try:
        conn = sqlite3.connect('score.db')
        cursor = conn.cursor()
        
        print("=== BOAT_CLASSES TABLE ===")
        cursor.execute('PRAGMA table_info(boat_classes)')
        columns = cursor.fetchall()
        print("Columns:", [col[1] for col in columns])
        
        cursor.execute('SELECT * FROM boat_classes')
        rows = cursor.fetchall()
        if rows:
            print(f"\nData ({len(rows)} rows):")
            for row in rows:
                print(f"  {row}")
        else:
            print("\nNo data in boat_classes table")
            
        print("\n=== RACE_CLASS_STARTS TABLE ===")
        cursor.execute('PRAGMA table_info(race_class_starts)')
        columns = cursor.fetchall()
        print("Columns:", [col[1] for col in columns])
        
        cursor.execute('SELECT * FROM race_class_starts')
        rows = cursor.fetchall()
        if rows:
            print(f"\nData ({len(rows)} rows):")
            for row in rows:
                print(f"  {row}")
        else:
            print("\nNo data in race_class_starts table")
            
        print("\n=== SAILORS TABLE ===")
        cursor.execute('SELECT sailor_name, boat_class, class_id, uid FROM sailors LIMIT 5')
        rows = cursor.fetchall()
        if rows:
            print(f"Sample data ({len(rows)} rows):")
            for row in rows:
                print(f"  {row}")
        else:
            print("\nNo data in sailors table")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    query_database()