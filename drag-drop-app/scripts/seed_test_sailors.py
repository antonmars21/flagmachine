"""Hermetic fixture sailors for regression tests.

The live score.db registry is user-managed (sailors get tidied/removed and
refreshed from Sailwave), so tests must not depend on particular sailors
being present. Each test works on a scratch COPY of the live DB; seeding
these fixtures into the scratch makes the test pass whatever the live
roster looks like. Fixture uids deliberately reuse the ones the tests
reference (SL-1091 etc.) so INSERT OR REPLACE is enough.

Usage inside a test, after copying score.db to a scratch path:
    from scripts.seed_test_sailors import seed_fixture_sailors
    conn = sqlite3.connect(SCRATCH)
    seed_fixture_sailors(conn)
    conn.commit()
"""

# (uid, sailor_name, short_name, sail_no, boat_class, boat_classes.class_name)
FIXTURES = [
    ('SL-1091',  'Reg Test One',   'TestOne',  '1091',  'Starling',  'Starling'),
    ('SL-955',   'Reg Test Two',   'TestTwo',  '955',   'Starling',  'Starling'),
    ('SL-15',    'Reg Test Three', 'TestThree', '15',   'Ilca 6',    'Ilca 6'),
    ('SL-18789', 'Reg Test Four',  'TestFour', '18789', 'Ilca 6',    'Ilca 6'),
    ('SL-12',    'Reg Test Five',  'TestFive', '12',    'Zephyr',    'Zephyr'),
    ('SL-141',   'Reg Test Six',   'TestSix',  '141',   'Frostbite', 'Frostbite'),
]


def seed_fixture_sailors(conn):
    """Upsert the fixture sailors into a scratch DB (never the live one)."""
    for uid, name, short, sail_no, boat_class, class_name in FIXTURES:
        row = conn.execute(
            'SELECT class_id FROM boat_classes WHERE class_name = ?',
            (class_name,)).fetchone()
        class_id = row[0] if row else None
        conn.execute(
            '''INSERT OR REPLACE INTO sailors
               (uid, sailor_name, short_name, sail_no, boat_class, handicap,
                seed, class_id, racing_today, status, finish_order, finish_time)
               VALUES (?, ?, ?, ?, ?, 1.0, 0, ?, 0, 'racing', NULL, NULL)''',
            (uid, name, short, sail_no, boat_class, class_id))
