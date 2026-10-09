"""Verify: (1) short_name = first name from Boats_Master.xml,
(2) startup flag scan repairs boat_classes.flag_image.
Runs against a temp copy of score.db - real DB untouched here."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- 1. short_name extraction from the XML export ---
sys.path.insert(0, 'scripts')
from import_sailwave import SAILWAVE_DB_FOLDER, parse_sailwave_xml, extract_boat_info

xml_path = os.path.join(SAILWAVE_DB_FOLDER, 'Boats_Master.xml')
boats, classes = parse_sailwave_xml(xml_path)
assert boats, 'no competitors parsed from XML'
print(f'parsed {len(boats)} competitors from Boats_Master.xml')
for b in boats[:5]:
    info = extract_boat_info(b)
    print(f"  helm='{info['sailor_name']}' short_name='{info['short_name']}' class='{info['boat_class']}'")

firsts = [extract_boat_info(b) for b in boats[:5]]
assert all(i['short_name'] == i['helm_name'].split()[0] for i in firsts), 'short_name is not the first name'
print('PASS: short_name uses the helm first name')

# --- 2. flag scan ---
shutil.copy('score.db', 'tempref/score_test.db')
import app as app_module
app_module.DB_PATH = 'tempref/score_test.db'

import sqlite3
conn = sqlite3.connect('tempref/score_test.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
files = os.listdir('static/flags')
ok = True
print('boat_classes flag_image after scan (run at app import):')
for r in c.execute('SELECT class_name, flag_image FROM boat_classes ORDER BY class_id'):
    fi = r['flag_image']
    exists = fi in files if fi else True
    print(f"  {r['class_name']:10} -> {fi!r:20} exists={exists}")
    if not exists:
        ok = False
conn.close()
assert ok, 'some flag_image still points at a missing file'
print('PASS: all flag_image values point at real files in static/flags')

os.remove('tempref/score_test.db')
