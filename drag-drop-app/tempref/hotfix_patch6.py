"""Hotfix patch 6 (2026-10-16, found on the Dell): 'Add New Sailor' blocked with
"SL-2045 not available". Root cause: uid is the sailors PRIMARY KEY (Sailwave
convention SL-<sail_no>) and sail_no is UNIQUE; the first add had succeeded but
the registry's saved search filter hid the new row, so the RO retried and hit the
duplicate - the generic error did not say which constraint or that the sailor
was already registered.

Fix: UID optional in the add form (auto SL-<sail_no>, suffixed if taken);
duplicate sail_no / uid get actionable messages naming the existing sailor;
successful add clears the saved search/class filters so the new sailor shows.
"""
import sys

BASE = r'C:\Users\anton\flagmachine\drag-drop-app'


def load(path):
    with open(path, 'rb') as f:
        return f.read()


def save(path, data):
    with open(path, 'wb') as f:
        f.write(data)


def rep(data, old, new, label):
    old_b, new_b = old.encode(), new.encode()
    if data.count(old_b) == 1:
        return data.replace(old_b, new_b)
    old_crlf = old_b.replace(b'\n', b'\r\n')
    if data.count(old_crlf) == 1:
        return data.replace(old_crlf, new_b.replace(b'\n', b'\r\n'))
    sys.exit('MATCH FAIL [%s]: LF count=%d CRLF count=%d' % (
        label, data.count(old_b), data.count(old_crlf)))


# ---------------- app.py: add-sailor uid auto-generation + clear messages ----------------
p = BASE + r'\app.py'
d = load(p)
d = rep(d, """def add_sailor():
    \"\"\"Add a new sailor to the registry.\"\"\"
    payload = request.get_json() or {}
    uid = (payload.get('uid') or '').strip()
    sailor_name = (payload.get('sailor_name') or '').strip()
    short_name = (payload.get('short_name') or '').strip()
    sail_no = (payload.get('sail_no') or '').strip()
    boat_class = (payload.get('boat_class') or '').strip()
    handicap = payload.get('handicap', 1.0)
    seed = payload.get('seed', 0)
    
    if not uid or not sailor_name:
        return jsonify({"status": "error", "message": "UID and Sailor Name are required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
""", """def add_sailor():
    \"\"\"Add a new sailor to the registry. UID is optional - auto-generated as
    SL-<sail_no> (Sailwave convention), suffixed -2/-3... if already taken.\"\"\"
    payload = request.get_json() or {}
    uid = (payload.get('uid') or '').strip()
    sailor_name = (payload.get('sailor_name') or '').strip()
    short_name = (payload.get('short_name') or '').strip()
    sail_no = (payload.get('sail_no') or '').strip()
    boat_class = (payload.get('boat_class') or '').strip()
    handicap = payload.get('handicap', 1.0)
    seed = payload.get('seed', 0)
    
    if not sailor_name or not sail_no:
        return jsonify({"status": "error", "message": "Sailor Name and Sail No are required"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # A duplicate sail number means the sailor is almost certainly already
    # registered (sail_no is UNIQUE). Point the RO at the existing row instead
    # of creating a confusing duplicate.
    c.execute('SELECT uid, short_name FROM sailors WHERE sail_no = ?', (sail_no,))
    dup_sail = c.fetchone()
    if dup_sail:
        conn.close()
        return jsonify({"status": "error",
                        "message": f"Sail number {sail_no} is already in the registry "
                                   f"({dup_sail['short_name']}, UID {dup_sail['uid']}). Sign them on "
                                   f"from the list instead of adding again - clear the search box "
                                   f"if you cannot see them."}), 400
    
    if uid:
        c.execute('SELECT short_name FROM sailors WHERE uid = ?', (uid,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error",
                            "message": f"UID '{uid}' already exists. Leave the UID box blank "
                                       f"and one will be chosen automatically."}), 400
    else:
        base = f'SL-{sail_no}'
        uid = base
        n = 2
        while c.execute('SELECT 1 FROM sailors WHERE uid = ?', (uid,)).fetchone():
            uid = f'{base}-{n}'
            n += 1
    
    try:
""", 'add_sailor header')
save(p, d)

# ---------------- finishsheet.html: UID optional in the add form ----------------
p = BASE + r'\templates\finishsheet.html'
d = load(p)
d = rep(d, """<div class="form-group"><label>UID</label><input type="text" name="uid" required></div>
""", """<div class="form-group"><label>UID (optional)</label><input type="text" name="uid" placeholder="auto: SL-sail number"></div>
""", 'add form uid optional')
save(p, d)

# ---------------- finishsheet.js: clear saved filters after a successful add ----------------
p = BASE + r'\static\js\finishsheet.js'
d = load(p)
d = rep(d, """        if (data.status === 'success') {
            form.reset();
            document.getElementById('add-sailor-form').classList.add('hidden');
            await loadRegistryList();
        } else {
""", """        if (data.status === 'success') {
            form.reset();
            document.getElementById('add-sailor-form').classList.add('hidden');
            // Clear saved filters so the new sailor is immediately visible:
            // a stale search filter previously hid the new row, the RO retried,
            // and the retry failed on the duplicate sail number.
            const searchInput = document.getElementById('registry-search');
            if (searchInput) { searchInput.value = ''; localStorage.setItem('registry_search_query', ''); }
            const classFilterEl = document.getElementById('classFilter');
            if (classFilterEl) { classFilterEl.value = ''; localStorage.setItem('registry_class_filter', ''); }
            await loadRegistryList();
        } else {
""", 'clear filters after add')
save(p, d)

print('PATCH 6 APPLIED OK')
