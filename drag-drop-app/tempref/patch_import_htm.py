"""One-off patch: import sailors from Sailwave boat_master.htm (same button on
all pages). Safe to delete after use."""
import io

def load(path):
    with io.open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()

def save(path, content):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)

def apply(content, old, new, label):
    for o, n in ((old, new), (old.replace('\n', '\r\n'), new.replace('\n', '\r\n'))):
        if content.count(o) == 1:
            print('OK  :', label)
            return content.replace(o, n)
    raise SystemExit('FAIL: %s (LF=%d CRLF=%d)' % (
        label, content.count(old), content.count(old.replace('\n', '\r\n'))))

# ---------- scripts/import_sailwave.py ----------
p = 'scripts/import_sailwave.py'
c = load(p)

# 1. HTM parser after the XML parser
c = apply(c,
    "    print(f\"  Found {len(boats)} competitors\")\n    return boats, []",
    "    print(f\"  Found {len(boats)} competitors\")\n    return boats, []\n\n"
    "\n"
    "def parse_sailwave_htm(htm_path):\n"
    "    \"\"\"\n"
    "    Parse a Sailwave boat_master.htm export (the HTML competitor list\n"
    "    Sailwave writes alongside its .blw database - the club's source file\n"
    "    for the 'Import Sailwave sailors' button).\n"
    "\n"
    "    Expected table columns: [x] Fleet, Class, Boat, SailNo, HelmName,\n"
    "    Handicap. Returns (boats, classes) in the same shape as\n"
    "    parse_sailwave_xml, so extract_boat_info / import_sailors work\n"
    "    unchanged: compclass holds the division (e.g. 'ILCA 6'), compboat is\n"
    "    the boat name, compsailno the sail number, comphelmname the helm and\n"
    "    comprating the handicap.\n"
    "    \"\"\"\n"
    "    import html as html_mod\n"
    "    print(f\"\\n{'='*60}\")\n"
    "    print(f\"PARSING: {htm_path}\")\n"
    "    print(f\"{'='*60}\")\n"
    "\n"
    "    if not os.path.exists(htm_path):\n"
    "        print(f\"ERROR: File not found: {htm_path}\")\n"
    "        return None, None\n"
    "\n"
    "    try:\n"
    "        with open(htm_path, 'r', encoding='ISO-8859-1') as f:\n"
    "            content = f.read()\n"
    "    except OSError as e:\n"
    "        print(f\"ERROR: Cannot read file: {e}\")\n"
    "        return None, None\n"
    "\n"
    "    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.S)\n"
    "    header_idx = {}\n"
    "    for row in rows:\n"
    "        heads = [html_mod.unescape(re.sub(r'<[^>]+>', '', h)).strip()\n"
    "                 for h in re.findall(r'<th[^>]*>(.*?)</th>', row, re.S)]\n"
    "        norm = [h.lower().replace(' ', '') for h in heads]\n"
    "        if 'sailno' in norm and 'helmname' in norm:\n"
    "            header_idx = {name: i for i, name in enumerate(norm)}\n"
    "            break\n"
    "    if not header_idx:\n"
    "        print(\"ERROR: No competitor table header (SailNo/HelmName) found\")\n"
    "        return None, None\n"
    "\n"
    "    def cell(row, column, alt):\n"
    "        idx = header_idx.get(column)\n"
    "        if idx is None:\n"
    "            return ''\n"
    "        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)\n"
    "        if idx >= len(cells):\n"
    "            return ''\n"
    "        text = html_mod.unescape(re.sub(r'<[^>]+>', '', cells[idx])).strip()\n"
    "        return text if text.lower() not in ('x', column, alt) else ''\n"
    "\n"
    "    boats = []\n"
    "    for row in rows:\n"
    "        sail_no = cell(row, 'sailno', 'sailno')\n"
    "        if not sail_no:\n"
    "            continue  # header row or non-competitor row\n"
    "        boats.append({\n"
    "            'compfleet': cell(row, 'fleet', 'fleet'),\n"
    "            'compclass': cell(row, 'class', 'class'),\n"
    "            'compboat': cell(row, 'boat', 'boat'),\n"
    "            'compsailno': sail_no,\n"
    "            'comphelmname': cell(row, 'helmname', 'helmname'),\n"
    "            'comprating': cell(row, 'handicap', 'handicap'),\n"
    "        })\n"
    "\n"
    "    print(f\"  Found {len(boats)} competitors\")\n"
    "    return boats, []",
    'S1: parse_sailwave_htm')

# 2. dispatch by extension in import_sailwave_data
c = apply(c,
    "        # Parse the Sailwave XML export\n        boats, classes = parse_sailwave_xml(xml_path)\n        \n        if boats is None:\n            print(\"ERROR: Failed to parse XML file\")\n            return False",
    "        # Parse the Sailwave export - boat_master.htm or Boats_Master.xml\n"
    "        # depending on the file extension\n"
    "        if str(xml_path).lower().endswith(('.htm', '.html')):\n"
    "            boats, classes = parse_sailwave_htm(xml_path)\n"
    "        else:\n"
    "            boats, classes = parse_sailwave_xml(xml_path)\n"
    "        \n"
    "        if boats is None:\n"
    "            print(\"ERROR: Failed to parse the Sailwave export file\")\n"
    "            return False",
    'S2: dispatch by extension')

# 3. header print + help text
c = apply(c,
    '    print(f"# XML: {xml_path}")',
    '    print(f"# Source: {xml_path}")',
    'S3: source print')
c = apply(c,
    "        help=f'Path to Boats_Master.xml (default: {DEFAULT_XML_PATH})'",
    "        help='Path to the Sailwave export (boat_master.htm or Boats_Master.xml)'",
    'S4: help text')

# 4. import re needed at module level (parse_sailwave_htm uses re)
c = apply(c,
    "import argparse",
    "import argparse\nimport re",
    'S5: import re')
save(p, c)
print('import_sailwave.py saved')

# ---------- app.py ----------
p = 'app.py'
c = load(p)

c = apply(c,
    "def find_sailwave_source():\n"
    "    \"\"\"Locate the Sailwave Boats_Master.xml source file.\n"
    "    Prefer the Sailwave database folder; fall back to tempref/.\"\"\"\n"
    "    candidates = [\n"
    "        os.path.join(SAILWAVE_DB_FOLDER, 'Boats_Master.xml'),\n"
    "        os.path.join(SAILWAVE_DB_FOLDER, 'boat_master.xml'),\n"
    "        os.path.join(os.path.dirname(__file__), 'tempref', 'Boats_Master.xml'),\n"
    "        os.path.join(os.path.dirname(__file__), 'tempref', 'boat_master.xml'),\n"
    "    ]",
    "def find_sailwave_source():\n"
    "    \"\"\"Locate the Sailwave competitor source file.\n"
    "    Prefer the boat_master.htm listing (the club's actual Sailwave export,\n"
    "    agreed with the RO 2026-10-16 - the 'Import Sailwave sailors' button\n"
    "    reads it); fall back to Boats_Master.xml, then tempref/.\"\"\"\n"
    "    candidates = [\n"
    "        # Windows paths are case-insensitive: this also matches Boats_master.htm\n"
    "        os.path.join(SAILWAVE_DB_FOLDER, 'boat_master.htm'),\n"
    "        os.path.join(os.path.dirname(__file__), 'tempref', 'boat_master.htm'),\n"
    "        os.path.join(SAILWAVE_DB_FOLDER, 'Boats_Master.xml'),\n"
    "        os.path.join(SAILWAVE_DB_FOLDER, 'boat_master.xml'),\n"
    "        os.path.join(os.path.dirname(__file__), 'tempref', 'Boats_Master.xml'),\n"
    "        os.path.join(os.path.dirname(__file__), 'tempref', 'boat_master.xml'),\n"
    "    ]",
    'A1: find_sailwave_source prefers HTM')

c = apply(c,
    "    Import/refresh sailor and boat class data from Sailwave Boats_Master.xml.\n"
    "    \n"
    "    This endpoint triggers the import script to read from Boats_Master.xml\n"
    "    and update the score.db with the latest data from Sailwave.",
    "    Import/refresh sailor and boat class data from the Sailwave export.\n"
    "    \n"
    "    Reads boat_master.htm (the club's Sailwave HTML competitor list) when\n"
    "    present, falling back to Boats_Master.xml, and updates score.db.",
    'A2: endpoint docstring')

c = apply(c,
    "            \"message\": f\"No Boats_Master.xml found in {SAILWAVE_DB_FOLDER} \"\n"
    "                       f\"or the tempref/ folder.\"\n"
    "        }), 404",
    "            \"message\": f\"No boat_master.htm or Boats_Master.xml found in \"\n"
    "                       f\"{SAILWAVE_DB_FOLDER} or the tempref/ folder.\"\n"
    "        }), 404",
    'A3: endpoint error message')

c = apply(c,
    "    \"\"\"\n    Check if Boats_Master.xml is available for import.\n    \n    Returns:\n        {\"status\": \"available\" or \"not_found\", \"path\": \"...\"}\n    \"\"\"\n    xml_path = find_sailwave_source()",
    "    \"\"\"\n    Check if the Sailwave export (boat_master.htm preferred, else\n    Boats_Master.xml) is available for import.\n    \n    Returns:\n        {\"status\": \"available\" or \"not_found\", \"path\": \"...\"}\n    \"\"\"\n    xml_path = find_sailwave_source()",
    'A4: status docstring')

c = apply(c,
    "            \"message\": \"Boats_Master.xml not found in the Sailwave database folder or tempref/.\"",
    "            \"message\": \"boat_master.htm / Boats_Master.xml not found in the Sailwave database folder or tempref/.\"",
    'A5: status message')
save(p, c)
print('app.py saved')

# ---------- templates/index.html: RO button matches the finish sheets ----------
p = 'templates/index.html'
c = load(p)
import re as _re
c2, n = _re.subn(
    r'(<button id="btn-refresh-sailwave" class="btn btn-sailwave">)[^<]*(</button>)',
    r'\g<1>\U0001f4e5 Import Sailwave sailors\g<2>', c)
assert n == 1, 'RO sailwave button not found (%d)' % n
save(p, c)
print('index.html saved')

# ---------- static/js/app.js + finishsheet.js: same wording on both ----------
for p in ('static/js/app.js', 'static/js/finishsheet.js'):
    c = load(p)
    c = apply(c,
        "// Refresh Sailwave data from boat_master.json",
        "// Import sailors from the Sailwave boat_master.htm export",
        p + ': comment')
    c = apply(c,
        "btn.innerHTML = '\\ud83d\\udd04 Refreshing...';",
        "btn.innerHTML = '\\ud83d\\udce5 Importing...';",
        p + ': busy text')
    c = apply(c,
        "alert(`Sailwave refresh successful!\\n\\n` +",
        "alert(`Sailwave sailors imported successfully!\\n\\n` +",
        p + ': success alert')
    c = apply(c,
        "alert(`Refresh failed: ${data.message || 'Unknown error'}`);",
        "alert(`Import failed: ${data.message || 'Unknown error'}`);",
        p + ': failure alert')
    c = apply(c,
        "alert(`Refresh failed: ${error.message}`);",
        "alert(`Import failed: ${error.message}`);",
        p + ': catch alert')
    save(p, c)
    print(p + ' saved')

print('ALL IMPORT-HTM PATCHES APPLIED')
