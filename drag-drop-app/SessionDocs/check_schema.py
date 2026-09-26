import sqlite3
conn = sqlite3.connect('score.db')
c = conn.cursor()
c.execute("PRAGMA table_info(sailors)")
print("=== sailors table columns ===")
for col in c.fetchall():
    print(col)
c.execute("SELECT uid, short_name, boat_class, class_id FROM sailors LIMIT 3")
print("\n=== sample rows ===")
for row in c.fetchall():
    print(row)
conn.close()
