import sqlite3

conn = sqlite3.connect('score.db')
c = conn.cursor()

# Simulate the exact query from the code
race_id = None

if race_id:
    print("Using active race query")
else:
    print("Using no-active-race query")
    c.execute('''
        SELECT uid, sail_no, short_name, boat_class, seed, 0 as lap_count, NULL as finish_time, NULL as placement
        FROM sailors
        ORDER BY boat_class, seed
    ''')

rows = c.fetchall()
print(f"Query returned {len(rows)} rows")

if len(rows) > 0:
    print(f"First row: {rows[0]}")

# Now group by class
class_groups = {}
for row in rows:
    boat_class = row[3]  # boat_class is 4th column
    if boat_class not in class_groups:
        class_groups[boat_class] = []
    class_groups[boat_class].append({
        'uid': row[0],
        'sail_no': row[1],
        'short_name': row[2],
        'boat_class': boat_class,
        'seed': row[4],
        'lap_count': row[5],
        'finish_time': row[6],
        'placement': row[7]
    })

print(f"\nGrouped into {len(class_groups)} classes:")
for cls, sailors in class_groups.items():
    print(f"  {cls}: {len(sailors)}")

# Get top 3 classes
sorted_classes = sorted(class_groups.items(), key=lambda x: len(x[1]), reverse=True)
print(f"\nTop 3 classes: {[c[0] for c in sorted_classes[:3]]}")

# Build columns
columns = {1: [], 2: [], 3: [], 4: []}
col_index = 1
for cls_name, sailors_list in sorted_classes[:3]:
    columns[col_index] = sailors_list
    col_index += 1

if len(sorted_classes) > 3:
    for cls_name, sailors_list in sorted_classes[3:]:
        columns[4].extend(sailors_list)

print("\nColumn distribution:")
for col_num in [1, 2, 3, 4]:
    print(f"  Column {col_num}: {len(columns[col_num])} sailors")

conn.close()
