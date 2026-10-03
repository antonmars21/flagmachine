import sqlite3

conn = sqlite3.connect('score.db')
c = conn.cursor()

# Query sailors directly from DB
print("=== Direct DB Query ===")
sailors = c.execute("SELECT uid, sail_no, short_name, boat_class, seed FROM sailors ORDER BY boat_class, seed LIMIT 10").fetchall()
print(f"Found {len(sailors)} sailors:")
for s in sailors:
    print(f"  {s[4]}: {s[2]} ({s[1]}) - {s[3]}")

# Check class distribution
print("\n=== Class Distribution ===")
classes = c.execute("SELECT boat_class, COUNT(*) as cnt FROM sailors GROUP BY boat_class ORDER BY cnt DESC").fetchall()
for cls, cnt in classes:
    print(f"  {cls}: {cnt} sailors")

conn.close()

# Now test API
print("\n=== Testing API ===")
import requests
import json

r = requests.get('http://localhost:5000/api/sailors-for-onwater')
data = r.json()
print(f"API Status: {data.get('status')}")
print(f"Class groups: {data.get('class_groups')}")

# Check if columns have data
for col_num in [1, 2, 3, 4]:
    col_key = col_num  # Try integer key
    sailors_in_col = data.get('columns', {}).get(col_key, [])
    print(f"Column {col_num}: {len(sailors_in_col)} sailors")
    if sailors_in_col:
        print(f"  First: {sailors_in_col[0]['short_name']} ({sailors_in_col[0]['boat_class']})")
