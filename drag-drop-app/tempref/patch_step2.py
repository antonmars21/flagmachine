"""One-off patch: card layout + light scrollbars + Step Back (feature 4 Step 2).
Safe to delete after use."""
import io

def load(path):
    with io.open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()

def save(path, content):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)

def apply(content, old, new, label, expected=1):
    for o, n in ((old, new), (old.replace('\n', '\r\n'), new.replace('\n', '\r\n'))):
        if content.count(o) == expected:
            print('OK  :', label)
            return content.replace(o, n)
    raise SystemExit('FAIL: %s (LF=%d CRLF=%d expected=%d)' % (
        label, content.count(old), content.count(old.replace('\n', '\r\n')), expected))

def apply_in_slice(content, start_marker, end_marker, old, new, label):
    """Apply a replace within one function/region only."""
    s = content.find(start_marker)
    e = content.find(end_marker, s + len(start_marker))
    assert s != -1 and e != -1, 'slice markers not found for ' + label
    region = content[s:e]
    for o, n in ((old, new), (old.replace('\n', '\r\n'), new.replace('\n', '\r\n'))):
        if region.count(o) == 1:
            print('OK  :', label)
            return content[:s] + region.replace(o, n) + content[e:]
    raise SystemExit('FAIL in slice: ' + label)

# ==================== app.py ====================
p = 'app.py'
c = load(p)

# 1. capture_actions table (after class_station_assignments)
c = apply(c,
    "    c.execute('''CREATE TABLE IF NOT EXISTS class_station_assignments (\n"
    "        class_key TEXT PRIMARY KEY,\n"
    "        station INTEGER NOT NULL,\n"
    "        updated_at TEXT\n"
    "    )''')",
    "    c.execute('''CREATE TABLE IF NOT EXISTS class_station_assignments (\n"
    "        class_key TEXT PRIMARY KEY,\n"
    "        station INTEGER NOT NULL,\n"
    "        updated_at TEXT\n"
    "    )''')\n"
    "    \n"
    "    # Per-station capture log for the Step Back feature (feature 4): every\n"
    "    lap/finish is logged with the station that captured it, so each screen\n"
    "    reverses only its own most recent action. Nothing is hard-deleted -\n"
    "    undone actions stay in the log so Restore can re-apply them with the\n"
    "    ORIGINAL timestamp.\n"
    "    c.execute('''CREATE TABLE IF NOT EXISTS capture_actions (\n"
    "        id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    "        race_id INTEGER NOT NULL,\n"
    "        uid TEXT NOT NULL,\n"
    "        action TEXT NOT NULL,\n"
    "        station INTEGER,\n"
    "        timestamp TEXT NOT NULL,\n"
    "        lap_number INTEGER,\n"
    "        ref_id INTEGER,\n"
    "        undone INTEGER DEFAULT 0,\n"
    "        undone_at TEXT,\n"
    "        FOREIGN KEY(race_id) REFERENCES races(race_id),\n"
    "        FOREIGN KEY(uid) REFERENCES sailors(uid)\n"
    "    )''')",
    'B1: capture_actions table')

# 2. rename assignments_version -> sheet_version (it now also covers
#    step back / restore re-renders, not just column toggles)
c = apply(c, '    "assignments_version": 1\n}', '    "sheet_version": 1\n}', 'B2a: app_state rename')
c = apply(c,
    "        \"assignments_version\": app_state.get('assignments_version', 1)\n    })",
    "        \"sheet_version\": app_state.get('sheet_version', 1)\n    })",
    'B2b: race-status rename')
c = apply(c,
    "    app_state['assignments_version'] = app_state.get('assignments_version', 1) + 1\n"
    "    return jsonify({\"status\": \"success\", \"class_key\": class_key, \"station\": station})",
    "    # Bump the sheet version so every station's poller re-renders.\n"
    "    app_state['sheet_version'] = app_state.get('sheet_version', 1) + 1\n"
    "    return jsonify({\"status\": \"success\", \"class_key\": class_key, \"station\": station})",
    'B2c: assign endpoint rename')

# 3. record-lap: station param + 2s double-capture guard + capture log
c = apply_in_slice(c, "@app.route('/api/record-lap', methods=['POST'])", "@app.route('/api/mark-finish', methods=['POST'])",
    "    payload = request.get_json()\n    race_id = app_state.get('race_id')\n    uid = payload.get('uid')",
    "    payload = request.get_json()\n    race_id = app_state.get('race_id')\n    uid = payload.get('uid')\n"
    "    # Station that captured this (feature 4) - logged for per-screen Step Back\n"
    "    try:\n"
    "        station = int(payload.get('station'))\n"
    "    except (TypeError, ValueError):\n"
    "        station = None",
    'B3a: record-lap station param')
c = apply_in_slice(c, "@app.route('/api/record-lap', methods=['POST'])", "@app.route('/api/mark-finish', methods=['POST'])",
    "    try:\n        # Ensure the sailor belongs to this race",
    "    # Double-capture guard (feature 4): the same sailor lapped twice within\n"
    "    # 2 seconds is a double tap or both operators - reject it. Boats need\n"
    "    # minutes per lap, so this never blocks a real lap.\n"
    "    guard = c.execute('''SELECT timestamp FROM lap_records\n"
    "                         WHERE race_id = ? AND uid = ?\n"
    "                         ORDER BY lap_number DESC LIMIT 1''', (race_id, uid)).fetchone()\n"
    "    if guard and guard['timestamp']:\n"
    "        try:\n"
    "            if (datetime.now() - datetime.fromisoformat(guard['timestamp'])).total_seconds() < 2:\n"
    "                conn.close()\n"
    "                return jsonify({\"status\": \"error\",\n"
    "                                \"message\": \"Lap already recorded for this sailor less than 2 seconds ago\"}), 400\n"
    "        except ValueError:\n"
    "            pass\n"
    "    \n"
    "    try:\n        # Ensure the sailor belongs to this race",
    'B3b: 2s double-capture guard')
c = apply_in_slice(c, "@app.route('/api/record-lap', methods=['POST'])", "@app.route('/api/mark-finish', methods=['POST'])",
    "        # Record lap\n        lap_time = datetime.now().isoformat()\n        c.execute('''\n            INSERT INTO lap_records (race_id, uid, lap_number, timestamp)\n            VALUES (?, ?, ?, ?)\n        ''', (race_id, uid, lap_number, lap_time))",
    "        # Record lap\n        lap_time = datetime.now().isoformat()\n        cur = c.execute('''\n            INSERT INTO lap_records (race_id, uid, lap_number, timestamp)\n            VALUES (?, ?, ?, ?)\n        ''', (race_id, uid, lap_number, lap_time))\n"
    "        # Log the capture for per-station Step Back (feature 4)\n"
    "        c.execute('''INSERT INTO capture_actions\n"
    "                      (race_id, uid, action, station, timestamp, lap_number, ref_id)\n"
    "                      VALUES (?, ?, 'lap', ?, ?, ?, ?)''',\n"
    "                  (race_id, uid, station, lap_time, lap_number, cur.lastrowid))",
    'B3c: record-lap capture log')

# 4. mark-finish: station param + capture log
c = apply_in_slice(c, "@app.route('/api/mark-finish', methods=['POST'])", "@app.route('/api/get-elapsed-time')",
    "    payload = request.get_json()\n    race_id = app_state.get('race_id')\n    uid = payload.get('uid')",
    "    payload = request.get_json()\n    race_id = app_state.get('race_id')\n    uid = payload.get('uid')\n"
    "    # Station that captured this (feature 4) - logged for per-screen Step Back\n"
    "    try:\n"
    "        station = int(payload.get('station'))\n"
    "    except (TypeError, ValueError):\n"
    "        station = None",
    'B4a: mark-finish station param')
c = apply_in_slice(c, "@app.route('/api/mark-finish', methods=['POST'])", "@app.route('/api/get-elapsed-time')",
    "        finish_time = datetime.now().isoformat()\n        c.execute('''\n            UPDATE race_sailors\n            SET finish_time = ?\n            WHERE race_id = ? AND uid = ?\n        ''', (finish_time, race_id, uid))",
    "        finish_time = datetime.now().isoformat()\n        c.execute('''\n            UPDATE race_sailors\n            SET finish_time = ?\n            WHERE race_id = ? AND uid = ?\n        ''', (finish_time, race_id, uid))\n"
    "        # Log the capture for per-station Step Back (feature 4)\n"
    "        c.execute('''INSERT INTO capture_actions\n"
    "                      (race_id, uid, action, station, timestamp)\n"
    "                      VALUES (?, ?, 'finish', ?, ?)''',\n"
    "                  (race_id, uid, station, finish_time))",
    'B4b: mark-finish capture log')

# 5. undo-last + restore-last endpoints
c = apply(c,
    "@app.route('/api/get-elapsed-time')",
    "def _normalize_station(payload):\n"
    "    \"\"\"Station param for undo/restore: must be 1 or 2.\"\"\"\n"
    "    try:\n"
    "        station = int(payload.get('station'))\n"
    "    except (TypeError, ValueError):\n"
    "        station = 0\n"
    "    return station if station in (1, 2) else None\n"
    "\n"
    "@app.route('/api/undo-last', methods=['POST'])\n"
    "def undo_last():\n"
    "    \"\"\"Step Back (feature 4): reverse THIS station's most recent capture.\n"
    "    Lap: the logged lap record is removed and the lap count decremented.\n"
    "    Finish: the finish time is cleared and the sailor returns to racing.\n"
    "    The action stays in the log (undone=1) so /api/restore-last can\n"
    "    re-apply it with the ORIGINAL timestamp. The undone action's time\n"
    "    drops off the live sheet; all other times keep exact timestamps\n"
    "    (agreed with the RO 2026-10-16).\"\"\"\n"
    "    station = _normalize_station(request.get_json() or {})\n"
    "    if station is None:\n"
    "        return jsonify({\"status\": \"error\", \"message\": \"station (1 or 2) required\"}), 400\n"
    "    race_id = app_state.get('race_id')\n"
    "    if not race_id:\n"
    "        return jsonify({\"status\": \"error\", \"message\": \"No active race\"}), 400\n"
    "    conn = get_db_connection()\n"
    "    c = conn.cursor()\n"
    "    c.execute('''SELECT ca.*, s.short_name FROM capture_actions ca\n"
    "                 JOIN sailors s ON s.uid = ca.uid\n"
    "                 WHERE ca.race_id = ? AND ca.station = ? AND ca.undone = 0\n"
    "                 ORDER BY ca.id DESC LIMIT 1''', (race_id, station))\n"
    "    action = c.fetchone()\n"
    "    if not action:\n"
    "        conn.close()\n"
    "        return jsonify({\"status\": \"error\",\n"
    "                        \"message\": \"Nothing to step back for this station\"}), 404\n"
    "    if action['action'] == 'lap':\n"
    "        if not c.execute('SELECT id FROM lap_records WHERE id = ?',\n"
    "                         (action['ref_id'],)).fetchone():\n"
    "            conn.close()\n"
    "            return jsonify({\"status\": \"error\",\n"
    "                            \"message\": \"That lap was already reversed\"}), 409\n"
    "        c.execute('DELETE FROM lap_records WHERE id = ?', (action['ref_id'],))\n"
    "        c.execute('''UPDATE race_sailors SET lap_count = MAX(lap_count - 1, 0)\n"
    "                     WHERE race_id = ? AND uid = ?''', (race_id, action['uid']))\n"
    "    else:  # finish\n"
    "        row = c.execute('''SELECT finish_time FROM race_sailors\n"
    "                           WHERE race_id = ? AND uid = ?''',\n"
    "                         (race_id, action['uid'])).fetchone()\n"
    "        if (row['finish_time'] if row else None) != action['timestamp']:\n"
    "            conn.close()\n"
    "            return jsonify({\"status\": \"error\",\n"
    "                            \"message\": \"That finish was superseded by a later finish\"}), 409\n"
    "        c.execute('''UPDATE race_sailors SET finish_time = NULL\n"
    "                     WHERE race_id = ? AND uid = ?''', (race_id, action['uid']))\n"
    "    c.execute('UPDATE capture_actions SET undone = 1, undone_at = ? WHERE id = ?',\n"
    "              (datetime.now().isoformat(), action['id']))\n"
    "    conn.commit()\n"
    "    conn.close()\n"
    "    app_state['sheet_version'] = app_state.get('sheet_version', 1) + 1\n"
    "    return jsonify({\n"
    "        \"status\": \"success\",\n"
    "        \"action\": action['action'],\n"
    "        \"uid\": action['uid'],\n"
    "        \"sailor\": action['short_name'],\n"
    "        \"lap_number\": action['lap_number'],\n"
    "        \"timestamp\": action['timestamp'],\n"
    "    })\n"
    "\n"
    "@app.route('/api/restore-last', methods=['POST'])\n"
    "def restore_last():\n"
    "    \"\"\"Restore this station's most recently undone capture with its\n"
    "    ORIGINAL timestamp - the safety net behind instant Step Back.\"\"\"\n"
    "    station = _normalize_station(request.get_json() or {})\n"
    "    if station is None:\n"
    "        return jsonify({\"status\": \"error\", \"message\": \"station (1 or 2) required\"}), 400\n"
    "    race_id = app_state.get('race_id')\n"
    "    if not race_id:\n"
    "        return jsonify({\"status\": \"error\", \"message\": \"No active race\"}), 400\n"
    "    conn = get_db_connection()\n"
    "    c = conn.cursor()\n"
    "    c.execute('''SELECT ca.*, s.short_name FROM capture_actions ca\n"
    "                 JOIN sailors s ON s.uid = ca.uid\n"
    "                 WHERE ca.race_id = ? AND ca.station = ? AND ca.undone = 1\n"
    "                 ORDER BY ca.undone_at DESC LIMIT 1''', (race_id, station))\n"
    "    action = c.fetchone()\n"
    "    if not action:\n"
    "        conn.close()\n"
    "        return jsonify({\"status\": \"error\",\n"
    "                        \"message\": \"Nothing undone to restore for this station\"}), 404\n"
    "    if action['action'] == 'lap':\n"
    "        cur = c.execute('''INSERT INTO lap_records (race_id, uid, lap_number, timestamp)\n"
    "                           VALUES (?, ?, ?, ?)''',\n"
    "                         (race_id, action['uid'], action['lap_number'], action['timestamp']))\n"
    "        c.execute('UPDATE capture_actions SET ref_id = ? WHERE id = ?',\n"
    "                  (cur.lastrowid, action['id']))\n"
    "        c.execute('''UPDATE race_sailors SET lap_count = lap_count + 1\n"
    "                     WHERE race_id = ? AND uid = ?''', (race_id, action['uid']))\n"
    "    else:  # finish\n"
    "        row = c.execute('''SELECT finish_time FROM race_sailors\n"
    "                           WHERE race_id = ? AND uid = ?''',\n"
    "                         (race_id, action['uid'])).fetchone()\n"
    "        if row and row['finish_time'] is not None:\n"
    "            conn.close()\n"
    "            return jsonify({\"status\": \"error\",\n"
    "                            \"message\": \"That sailor has finished again since - nothing restored\"}), 409\n"
    "        c.execute('''UPDATE race_sailors SET finish_time = ?\n"
    "                     WHERE race_id = ? AND uid = ?''',\n"
    "                  (action['timestamp'], race_id, action['uid']))\n"
    "    c.execute('UPDATE capture_actions SET undone = 0, undone_at = NULL WHERE id = ?',\n"
    "              (action['id'],))\n"
    "    conn.commit()\n"
    "    conn.close()\n"
    "    app_state['sheet_version'] = app_state.get('sheet_version', 1) + 1\n"
    "    return jsonify({\n"
    "        \"status\": \"success\",\n"
    "        \"action\": action['action'],\n"
    "        \"uid\": action['uid'],\n"
    "        \"sailor\": action['short_name'],\n"
    "        \"lap_number\": action['lap_number'],\n"
    "        \"timestamp\": action['timestamp'],\n"
    "    })\n"
    "\n"
    "@app.route('/api/get-elapsed-time')",
    'B5: undo-last + restore-last endpoints')
save(p, c)

# ==================== static/js/finishsheet.js ====================
p = 'static/js/finishsheet.js'
c = load(p)

# J1. card layout: name + complete sail number on top row, class under it
c = apply(c,
    "    card.innerHTML = `\n"
    "        <div class=\"lap-counter\">\n"
    "            <button class=\"btn-lap\" data-action=\"lap\" data-uid=\"${sailor.uid}\" ${can_record ? '' : 'disabled'}>+ Lap</button>\n"
    "            <div class=\"lap-value\">${sailor.lap_count || 0}</div>\n"
    "        </div>\n"
    "        <span class=\"sailor-class\">${sailor.boat_class}</span>\n"
    "        <span class=\"sailor-name\">${sailor.short_name}${finished_class}</span>\n"
    "        <div class=\"sailor-spacer\"></div>\n"
    "        <span class=\"sail-number\">${sailor.sail_no}</span>\n"
    "        <input type=\"checkbox\" class=\"finish-checkbox\" data-uid=\"${sailor.uid}\" \n"
    "            ${sailor.finish_time ? 'checked disabled' : (can_record ? '' : 'disabled')}>\n"
    "    `;",
    "    card.innerHTML = `\n"
    "        <div class=\"lap-counter\">\n"
    "            <button class=\"btn-lap\" data-action=\"lap\" data-uid=\"${sailor.uid}\" ${can_record ? '' : 'disabled'}>+ Lap</button>\n"
    "            <div class=\"lap-value\">${sailor.lap_count || 0}</div>\n"
    "        </div>\n"
    "        <div class=\"sailor-details\">\n"
    "            <div class=\"sailor-name-row\">\n"
    "                <span class=\"sailor-name\">${sailor.short_name}${finished_class}</span>\n"
    "                <span class=\"sail-number\">${sailor.sail_no}</span>\n"
    "            </div>\n"
    "            <div class=\"sailor-class-row\">\n"
    "                <span class=\"sailor-class\">${sailor.boat_class}</span>\n"
    "            </div>\n"
    "        </div>\n"
    "        <input type=\"checkbox\" class=\"finish-checkbox\" data-uid=\"${sailor.uid}\" \n"
    "            ${sailor.finish_time ? 'checked disabled' : (can_record ? '' : 'disabled')}>\n"
    "    `;",
    'J1: two-line sailor card')

# J2. sailor/sailors plural
c = apply(c,
    "<div class=\"column-count\">${sailors.length} sailors</div>",
    "<div class=\"column-count\">${sailors.length} sailor${sailors.length === 1 ? '' : 's'}</div>",
    'J2: sailor plural')

# J3. captures carry the station (recordLap + markFinish - identical bodies)
c = apply_in_slice(c, "async function recordLap(uid, card) {", "async function markFinish(uid, is_finished, card) {",
    "body: JSON.stringify({ uid })",
    "body: JSON.stringify({ uid, station: state.station })",
    'J3a: recordLap carries station')
c = apply_in_slice(c, "async function markFinish(uid, is_finished, card) {", "/**\n * Poll for class-start status",
    "body: JSON.stringify({ uid })",
    "body: JSON.stringify({ uid, station: state.station })",
    'J3b: markFinish carries station')

# J4. Step Back wiring
c = apply(c,
    "    document.getElementById('btn-export-csv').addEventListener('click', exportRaceCsv);",
    "    document.getElementById('btn-export-csv').addEventListener('click', exportRaceCsv);\n"
    "    document.getElementById('btn-step-back').addEventListener('click', stepBack);",
    'J4: step back listener')

# J5. stepBack / restore / toast functions after moveClassToStation
c = apply(c,
    "    } catch (error) {\n        console.error(\"Error moving class to station:\", error);\n    }\n}",
    "    } catch (error) {\n        console.error(\"Error moving class to station:\", error);\n    }\n}\n\n"
    "/**\n"
    " * Step Back (feature 4): instantly reverse THIS station's most recent\n"
    " * capture (lap or finish, any sailor). No confirm dialog - the toast\n"
    " * that follows offers Restore with the original time as the safety net.\n"
    " */\n"
    "async function stepBack() {\n"
    "    try {\n"
    "        const response = await fetch('/api/undo-last', {\n"
    "            method: 'POST',\n"
    "            headers: { 'Content-Type': 'application/json' },\n"
    "            body: JSON.stringify({ station: state.station })\n"
    "        });\n"
    "        const data = await response.json();\n"
    "        if (data.status === 'success') {\n"
    "            const what = data.action === 'lap'\n"
    "                ? `Lap ${data.lap_number} for ${data.sailor}`\n"
    "                : `Finish for ${data.sailor}`;\n"
    "            showStepBackToast(`Stepped back: ${what} (${fmtClock(data.timestamp)})`, true);\n"
    "            loadAndRenderSailors();\n"
    "        } else {\n"
    "            showStepBackToast(data.message || 'Nothing to step back.', false);\n"
    "        }\n"
    "    } catch (error) {\n"
    "        console.error(\"Error stepping back:\", error);\n"
    "    }\n"
    "}\n\n"
    "/**\n"
    " * Restore this station's most recently undone capture (original time).\n"
    " */\n"
    "async function restoreLastStep() {\n"
    "    try {\n"
    "        const response = await fetch('/api/restore-last', {\n"
    "            method: 'POST',\n"
    "            headers: { 'Content-Type': 'application/json' },\n"
    "            body: JSON.stringify({ station: state.station })\n"
    "        });\n"
    "        const data = await response.json();\n"
    "        if (data.status === 'success') {\n"
    "            const what = data.action === 'lap'\n"
    "                ? `Lap ${data.lap_number} for ${data.sailor}`\n"
    "                : `Finish for ${data.sailor}`;\n"
    "            showStepBackToast(`Restored: ${what} (${fmtClock(data.timestamp)})`, false);\n"
    "            loadAndRenderSailors();\n"
    "        } else {\n"
    "            showStepBackToast(data.message || 'Nothing to restore.', false);\n"
    "        }\n"
    "    } catch (error) {\n"
    "        console.error(\"Error restoring:\", error);\n"
    "    }\n"
    "}\n\n"
    "function fmtClock(iso) {\n"
    "    if (!iso) return '';\n"
    "    const d = new Date(iso);\n"
    "    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });\n"
    "}\n\n"
    "function showStepBackToast(message, withRestore) {\n"
    "    let toast = document.getElementById('stepback-toast');\n"
    "    if (!toast) {\n"
    "        toast = document.createElement('div');\n"
    "        toast.id = 'stepback-toast';\n"
    "        document.body.appendChild(toast);\n"
    "    }\n"
    "    toast.innerHTML = `\n"
    "        <span>${message}</span>\n"
    "        ${withRestore ? '<button id=\"stepback-restore\">Restore</button>' : ''}\n"
    "    `;\n"
    "    toast.style.display = 'flex';\n"
    "    const restoreBtn = document.getElementById('stepback-restore');\n"
    "    if (restoreBtn) restoreBtn.addEventListener('click', restoreLastStep);\n"
    "    clearTimeout(state._toastTimer);\n"
    "    state._toastTimer = setTimeout(() => { toast.style.display = 'none'; }, 10000);\n"
    "}",
    'J5: stepBack/restore/toast functions')

# J6. sheet_version rename in state + poller
c = apply(c,
    "    station: null,\n    assignments: {},\n    assignments_version: null\n};",
    "    station: null,\n    assignments: {},\n    sheet_version: null\n};",
    'J6a: state rename')
c = apply(c,
    "        // Column-to-station change made on another station: re-render.\n"
    "        const av = data.assignments_version;\n"
    "        if (av !== undefined && av !== state.assignments_version) {\n"
    "            const firstSeen = state.assignments_version === null;\n"
    "            state.assignments_version = av;\n"
    "            if (!firstSeen) loadAndRenderSailors();\n"
    "        }",
    "        // Sheet change made on another station (column toggle, step back,\n"
    "        // restore): re-render this station's columns.\n"
    "        const av = data.sheet_version;\n"
    "        if (av !== undefined && av !== state.sheet_version) {\n"
    "            const firstSeen = state.sheet_version === null;\n"
    "            state.sheet_version = av;\n"
    "            if (!firstSeen) loadAndRenderSailors();\n"
    "        }",
    'J6b: poller rename')
save(p, c)

# ==================== templates/finishsheet.html ====================
p = 'templates/finishsheet.html'
c = load(p)

# H1. Step Back button in the banner
c = apply(c,
    "            <button class=\"btn btn-start\" id=\"btn-start-race\">\u25b6 Start Race</button>",
    "            <button class=\"btn btn-stepback\" id=\"btn-step-back\" title=\"Reverse this station's most recent lap or finish\">\u291a Step Back</button>\n"
    "            <button class=\"btn btn-start\" id=\"btn-start-race\">\u25b6 Start Race</button>",
    'H1: Step Back button')

# H2. Step Back button style
c = apply(c,
    "        .btn-export { background-color: #0369a1; color: #fff; }",
    "        .btn-export { background-color: #0369a1; color: #fff; }\n"
    "        .btn-stepback { background-color: #b45309; color: #fff; }",
    'H2: Step Back style')

# H3. two-line card: taller row, tighter padding
c = apply(c,
    "        .sailor-card {\n            background-color: #1a2332;\n            border: 2px solid #334155;\n            border-radius: 6px;\n            padding: 8px 12px;\n            cursor: grab;\n            transition: all 0.2s;\n            user-select: none;\n            display: flex;\n            align-items: center;\n            gap: 10px;\n            min-height: 56px;\n        }",
    "        .sailor-card {\n            background-color: #1a2332;\n            border: 2px solid #334155;\n            border-radius: 6px;\n            padding: 6px 12px;\n            cursor: grab;\n            transition: all 0.2s;\n            user-select: none;\n            display: flex;\n            align-items: center;\n            gap: 10px;\n            min-height: 64px;\n        }",
    'H3: card sizing for two lines')

# H4. name/class rows + light scrollbars replace the spacer rule
c = apply(c,
    "        .sailor-spacer {\n            flex: 1;\n        }",
    "        .sailor-details {\n            flex: 1;\n            min-width: 0;\n            display: flex;\n            flex-direction: column;\n            gap: 1px;\n        }\n\n"
    "        .sailor-name-row {\n            display: flex;\n            align-items: center;\n            justify-content: space-between;\n            gap: 10px;\n            min-width: 0;\n        }\n\n"
    "        .sailor-class-row {\n            display: flex;\n        }\n\n"
    "        /* Light scrollbars so the column scroll slider is clearly visible */\n"
    "        .columns-wrapper::-webkit-scrollbar,\n"
    "        .sailors-list::-webkit-scrollbar {\n"
    "            width: 12px;\n"
    "            height: 12px;\n"
    "        }\n\n"
    "        .columns-wrapper::-webkit-scrollbar-track,\n"
    "        .sailors-list::-webkit-scrollbar-track {\n"
    "            background: #e2e8f0;\n"
    "            border-radius: 6px;\n"
    "        }\n\n"
    "        .columns-wrapper::-webkit-scrollbar-thumb,\n"
    "        .sailors-list::-webkit-scrollbar-thumb {\n"
    "            background: #94a3b8;\n"
    "            border-radius: 6px;\n"
    "            border: 2px solid #e2e8f0;\n"
    "        }\n\n"
    "        .columns-wrapper::-webkit-scrollbar-thumb:hover,\n"
    "        .sailors-list::-webkit-scrollbar-thumb:hover {\n"
    "            background: #64748b;\n"
    "        }",
    'H4: detail rows + light scrollbars')

# H5. sail number: bigger, never truncated
c = apply(c,
    "        .sail-number {\n            font-size: 22px;\n            font-weight: 900;\n            color: #f59e0b;\n            flex-shrink: 0;\n        }",
    "        .sail-number {\n            font-size: 24px;\n            font-weight: 900;\n            color: #f59e0b;\n            flex-shrink: 0;\n            white-space: nowrap;\n        }",
    'H5: sail number complete + prominent')

# H6. class text slightly smaller as the secondary line
c = apply(c,
    "        .sailor-class {\n            font-size: 13px;\n            font-weight: 600;\n            color: #94a3b8;\n            text-transform: uppercase;\n            white-space: nowrap;\n            flex-shrink: 0;\n        }",
    "        .sailor-class {\n            font-size: 12px;\n            font-weight: 600;\n            color: #94a3b8;\n            text-transform: uppercase;\n            white-space: nowrap;\n            flex-shrink: 0;\n        }",
    'H6: class line styling')

# H7. step back toast styles
c = apply(c,
    "        .station-toggle:hover {\n            background-color: #475569;\n            color: #fff;\n        }",
    "        .station-toggle:hover {\n            background-color: #475569;\n            color: #fff;\n        }\n\n"
    "        #stepback-toast {\n"
    "            position: fixed;\n"
    "            bottom: 24px;\n"
    "            right: 24px;\n"
    "            display: none;\n"
    "            align-items: center;\n"
    "            gap: 12px;\n"
    "            background-color: #1e2640;\n"
    "            color: #f8fafc;\n"
    "            border: 2px solid #b45309;\n"
    "            border-radius: 8px;\n"
    "            padding: 12px 16px;\n"
    "            font-size: 15px;\n"
    "            font-weight: 600;\n"
    "            z-index: 1000;\n"
    "            box-shadow: 0 4px 12px rgba(0,0,0,0.5);\n"
    "        }\n\n"
    "        #stepback-toast button {\n"
    "            background-color: #b45309;\n"
    "            color: #fff;\n"
    "            border: none;\n"
    "            border-radius: 6px;\n"
    "            padding: 6px 14px;\n"
    "            font-weight: bold;\n"
    "            cursor: pointer;\n"
    "            font-size: 14px;\n"
    "        }",
    'H7: toast styles')
save(p, c)

# ==================== scripts/test_stations.py (rename) ====================
p = 'scripts/test_stations.py'
c = load(p)
c = apply(c,
    "assert rs['assignments_version'] == 2, rs",
    "assert rs['sheet_version'] == 2, rs",
    'T1: stations test rename')
save(p, c)

print('ALL PATCHES APPLIED')
