import sqlite3
conn = sqlite3.connect('score.db')
c = conn.cursor()
c.execute("SELECT uid, short_name, boat_class, class_id FROM sailors WHERE boat_class LIKE '%tarling%' OR boat_class LIKE '%Starling%'")
print("=== Starling sailors ===")
for row in c.fetchall():
    print(row)
c.execute("SELECT DISTINCT boat_class FROM sailors")
print("\n=== distinct boat_class values (check for case/whitespace variants) ===")
for row in c.fetchall():
    print(repr(row[0]))
conn.close()
