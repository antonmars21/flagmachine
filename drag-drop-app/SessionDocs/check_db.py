import sqlite3

conn = sqlite3.connect('score.db')
c = conn.cursor()

# Get all tables
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])

# Check sailors count
try:
    sailors = c.execute("SELECT COUNT(*) FROM sailors").fetchone()
    print("Sailors count:", sailors[0])
except Exception as e:
    print("Error checking sailors:", e)

# Show schema
for table in tables:
    print(f"\n{table[0]} schema:")
    schema = c.execute(f"PRAGMA table_info({table[0]})").fetchall()
    for col in schema:
        print(f"  {col[1]} ({col[2]})")

conn.close()
