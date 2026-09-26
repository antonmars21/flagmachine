"""
Session 5: Migrate to boat_classes table with class_id foreign key.
Eliminates hardcoded class names, enforces class reference via ID.
"""
import sqlite3
import sys

DB_PATH = 'score.db'

def migrate():
    """Run migration: create boat_classes, seed data, backfill sailors.class_id"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        print("=" * 60)
        print("BOAT CLASS MIGRATION")
        print("=" * 60)
        
        # Step 1: Create boat_classes table
        print("\n[1] Creating boat_classes table...")
        c.execute('''
            CREATE TABLE IF NOT EXISTS boat_classes (
                class_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name   TEXT UNIQUE NOT NULL,
                flag_image   TEXT,
                color_hex    TEXT DEFAULT '#0369a1',
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("    [OK] boat_classes table created")
        
        # Step 2: Seed class data
        print("\n[2] Seeding boat class data...")
        boat_classes_data = [
            ('Ilca 6', 'ilca6.png', '#0369a1'),      # blue
            ('Ilca 7', 'ilca7.png', '#06b6d4'),      # cyan
            ('Starling', 'starling.png', '#8b5cf6'), # purple
            ('Optimist', 'optimist.png', '#ec4899'), # pink
            ('P', 'p.png', '#f59e0b'),                # amber
            ('Zephyr', 'zephyr.png', '#10b981'),     # green
        ]
        
        for class_name, flag_image, color_hex in boat_classes_data:
            c.execute('''
                INSERT OR IGNORE INTO boat_classes (class_name, flag_image, color_hex)
                VALUES (?, ?, ?)
            ''', (class_name, flag_image, color_hex))
            print(f"    [OK] {class_name} -> {flag_image} ({color_hex})")
        
        conn.commit()
        
        # Step 3: Add class_id column to sailors (if not exists)
        print("\n[3] Adding class_id column to sailors table...")
        c.execute("PRAGMA table_info(sailors)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'class_id' not in columns:
            c.execute('''ALTER TABLE sailors ADD COLUMN class_id INTEGER''')
            print("    [OK] class_id column added")
        else:
            print("    [OK] class_id column already exists")
        
        # Step 4: Backfill class_id from boat_class lookup
        print("\n[4] Backfilling class_id from boat_class...")
        c.execute('''
            SELECT DISTINCT boat_class FROM sailors
        ''')
        unique_classes = [row[0] for row in c.fetchall()]
        print(f"    Found {len(unique_classes)} unique boat classes:")
        
        for boat_class in unique_classes:
            c.execute('''
                SELECT class_id FROM boat_classes WHERE class_name = ?
            ''', (boat_class,))
            result = c.fetchone()
            if result:
                class_id = result[0]
                c.execute('''
                    UPDATE sailors SET class_id = ? WHERE boat_class = ?
                ''', (class_id, boat_class))
                count = c.rowcount
                print(f"    [OK] {boat_class:15} -> class_id={class_id} ({count} sailors)")
            else:
                print(f"    [ERROR] {boat_class:15} -> NOT FOUND in boat_classes")
                return False
        
        conn.commit()
        
        # Step 5: Verify backfill
        print("\n[5] Verification...")
        c.execute('''SELECT COUNT(*) FROM sailors''')
        total_sailors = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM sailors WHERE class_id IS NOT NULL''')
        backfilled = c.fetchone()[0]
        
        print(f"    Total sailors: {total_sailors}")
        print(f"    Backfilled:    {backfilled}")
        
        if backfilled == total_sailors:
            print(f"    [OK] All {total_sailors} sailors backfilled successfully")
        else:
            orphaned = total_sailors - backfilled
            print(f"    [ERROR] {orphaned} sailors missing class_id")
            return False
        
        # Step 6: Sample verification query
        print("\n[6] Sample data (first 5 sailors):")
        c.execute('''
            SELECT s.sail_no, s.short_name, s.boat_class, bc.class_id, bc.flag_image, bc.color_hex
            FROM sailors s
            LEFT JOIN boat_classes bc ON s.class_id = bc.class_id
            LIMIT 5
        ''')
        for row in c.fetchall():
            sail_no, short_name, boat_class, class_id, flag_image, color_hex = row
            print(f"    {sail_no:5} | {short_name:15} | {boat_class:10} | ID={class_id} | {flag_image:15} | {color_hex}")
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("[OK] MIGRATION COMPLETE")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] MIGRATION FAILED: {str(e)}")
        conn.rollback()
        conn.close()
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
