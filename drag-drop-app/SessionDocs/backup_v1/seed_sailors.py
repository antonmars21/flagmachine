import sqlite3
import time
import random

DB_PATH = 'score.db'

sailors = [
    ("Rose Jackson Liew", "Rose",    "1111", "Ilca 6",   1.0,  5),
    ("Werner Hennig",     "Werner",  "1111", "Ilca 6",   1.0,  1),
    ("Helen Spencer",     "Helen",   "1111", "Ilca 6",   1.0,  4),
    ("Rick Spencer",      "Rick",    "1111", "Ilca 6",   1.0,  5),
    ("Carly Trelemer",    "Carly",   "2222", "Ilca 6",   1.0,  6),
    ("David Hawkins",     "Dave",    "2222", "Ilca 6",   1.0, 10),
    ("Scott McDougal",    "Scott",   "2222", "Ilca 6",   1.0,  2),
    ("Reuben Feist",      "Reuben",  "2222", "Ilca 6",   1.0,  6),
    ("Bruno Feist",       "Bruno",   "2223", "Ilca 6",   1.0,  6),
    ("Bridget Gordon",    "Bridget", "2223", "Ilca 6",   1.0,  4),
    ("Jake Miller",       "Jake",    "3333", "Ilca 7",   1.0,  3),
    ("Aiden Lee",         "Aiden",   "5555", "Ilca 7",   1.0,  3),
    ("Graham Hunter",     "Graham",  "2224", "Ilca 6",   1.0,  4),
    ("Benjie Dawson",     "Benjie",  "2225", "Ilca 6",   1.0, 10),
    ("Scott Dawson (Opt1)", "Scotty","1000", "Optimist", 1.0,  1),
    ("Scott Dawson (Opt2)", "Scotty","2000", "Optimist", 1.0,  1),
    ("Duncan Carter",     "Duncan",  "2000", "Optimist", 1.0,  2),
    ("Scott Dawson (P)",  "Scotty",  "101",  "P",        1.0,  1),
    ("Gabrielle Marais",  "Gabrielle","2057","Starling",  1.0,  2),
    ("Eoghan Harris",     "Eoghan",  "1056", "Starling",  1.0,  1),
    ("Zoe Moran",         "Zoe",     "1056", "Starling",  1.0,  3),
    ("Seren Dark",        "Seren",   "1057", "Starling",  1.0,  3),
    ("John Barnard",      "John",    "51",   "Zephyr",    1.0,  2),
    ("Ray Oxborrow",      "Ray",     "10",   "Zephyr",    1.0,  1),
]

def make_uid():
    ts = str(int(time.time()))[-6:]
    salt = random.randint(100, 999)
    time.sleep(0.01)   # ensure unique timestamps
    return f"SL-{ts}{salt}"

conn = sqlite3.connect(DB_PATH)
inserted = 0
skipped = 0

for (sailor_name, short_name, sail_no, boat_class, handicap, seed) in sailors:
    uid = make_uid()
    try:
        conn.execute('''
            INSERT INTO sailors (uid, sailor_name, short_name, sail_no, boat_class, handicap, seed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (uid, sailor_name, short_name, sail_no, boat_class, handicap, seed))
        conn.commit()
        print(f"  Inserted: {sailor_name} [{uid}]")
        inserted += 1
    except sqlite3.IntegrityError as e:
        print(f"  Skipped (duplicate): {sailor_name} — {e}")
        skipped += 1

conn.close()
print(f"\nDone. Inserted: {inserted}, Skipped: {skipped}")
