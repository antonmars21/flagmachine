import sqlite3

conn = sqlite3.connect('score.db')
c = conn.cursor()

# Normalize class names
c.execute("UPDATE sailors SET boat_class = 'Ilca 6' WHERE boat_class = 'ILCA6'")
c.execute("UPDATE sailors SET boat_class = 'Ilca 7' WHERE boat_class IN ('Ilca 7', 'ILCA7')")

# Check result
classes = c.execute("SELECT DISTINCT boat_class FROM sailors ORDER BY boat_class").fetchall()
print("Normalized classes:", [c[0] for c in classes])

# Group by class to see distribution
print("\nSailors per class:")
for cls in classes:
    count = c.execute("SELECT COUNT(*) FROM sailors WHERE boat_class = ?", (cls[0],)).fetchone()[0]
    print(f"  {cls[0]}: {count}")

conn.commit()
conn.close()
