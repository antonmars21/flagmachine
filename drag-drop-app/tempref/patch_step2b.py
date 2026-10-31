"""Follow-up patch: remaining Step 2 items (JS J3b onward + HTML + test rename)."""
import io

def load(path):
    with io.open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()

def save(path, content):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)

def find(content, marker):
    i = content.find(marker)
    if i == -1:
        i = content.find(marker.replace('\n', '\r\n'))
    return i

def apply(content, old, new, label):
    for o, n in ((old, new), (old.replace('\n', '\r\n'), new.replace('\n', '\r\n'))):
        if content.count(o) == 1:
            print('OK  :', label)
            return content.replace(o, n)
    raise SystemExit('FAIL: %s (LF=%d CRLF=%d)' % (
        label, content.count(old), content.count(old.replace('\n', '\r\n'))))

def apply_in_slice(content, start_marker, end_marker, old, new, label):
    s = find(content, start_marker)
    e = find(content, end_marker) if end_marker else -1
    assert s != -1 and e != -1 and e > s, 'slice markers not found for ' + label
    region = content[s:e]
    for o, n in ((old, new), (old.replace('\n', '\r\n'), new.replace('\n', '\r\n'))):
        if region.count(o) == 1:
            print('OK  :', label)
            return content[:s] + region.replace(o, n) + content[e:]
    raise SystemExit('FAIL in slice: ' + label)

# ---------- static/js/finishsheet.js ----------
p = 'static/js/finishsheet.js'
c = load(p)

c = apply_in_slice(c, "async function markFinish(uid, is_finished, card) {",
    "/**\n * Poll for class-start status",
    "body: JSON.stringify({ uid })",
    "body: JSON.stringify({ uid, station: state.station })",
    'J3b: markFinish carries station')

c = apply(c,
    "    document.getElementById('btn-export-csv').addEventListener('click', exportRaceCsv);",
    "    document.getElementById('btn-export-csv').addEventListener('click', exportRaceCsv);\n"
    "    document.getElementById('btn-step-back').addEventListener('click', stepBack);",
    'J4: step back listener')

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

# ---------- templates/finishsheet.html ----------
p = 'templates/finishsheet.html'
c = load(p)
c = apply(c,
    "            <button class=\"btn btn-start\" id=\"btn-start-race\">\u25b6 Start Race</button>",
    "            <button class=\"btn btn-stepback\" id=\"btn-step-back\" title=\"Reverse this station's most recent lap or finish\">\u291a Step Back</button>\n"
    "            <button class=\"btn btn-start\" id=\"btn-start-race\">\u25b6 Start Race</button>",
    'H1: Step Back button')
c = apply(c,
    "        .btn-export { background-color: #0369a1; color: #fff; }",
    "        .btn-export { background-color: #0369a1; color: #fff; }\n"
    "        .btn-stepback { background-color: #b45309; color: #fff; }",
    'H2: Step Back style')
c = apply(c,
    "        .sailor-card {\n            background-color: #1a2332;\n            border: 2px solid #334155;\n            border-radius: 6px;\n            padding: 8px 12px;\n            cursor: grab;\n            transition: all 0.2s;\n            user-select: none;\n            display: flex;\n            align-items: center;\n            gap: 10px;\n            min-height: 56px;\n        }",
    "        .sailor-card {\n            background-color: #1a2332;\n            border: 2px solid #334155;\n            border-radius: 6px;\n            padding: 6px 12px;\n            cursor: grab;\n            transition: all 0.2s;\n            user-select: none;\n            display: flex;\n            align-items: center;\n            gap: 10px;\n            min-height: 64px;\n        }",
    'H3: card sizing for two lines')
c = apply(c,
    "        .sailor-spacer {\n            flex: 1;\n        }",
    "        .sailor-details {\n            flex: 1;\n            min-width: 0;\n            display: flex;\n            flex-direction: column;\n            gap: 1px;\n        }\n\n"
    "        .sailor-name-row {\n            display: flex;\n            align-items: center;\n            justify-content: space-between;\n            gap: 10px;\n            min-width: 0;\n        }\n\n"
    "        .sailor-class-row {\n            display: flex;\n        }\n\n"
    "        /* Light scrollbars so the column scroll slider is clearly visible */\n"
    "        .columns-wrapper::-webkit-scrollbar,\n"
    "        .sailors-list::-webkit-scrollbar {\n"
    "            width: 12px;\n"
    "            height: 12px;\n        }\n\n"
    "        .columns-wrapper::-webkit-scrollbar-track,\n"
    "        .sailors-list::-webkit-scrollbar-track {\n"
    "            background: #e2e8f0;\n"
    "            border-radius: 6px;\n        }\n\n"
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
c = apply(c,
    "        .sail-number {\n            font-size: 22px;\n            font-weight: 900;\n            color: #f59e0b;\n            flex-shrink: 0;\n        }",
    "        .sail-number {\n            font-size: 24px;\n            font-weight: 900;\n            color: #f59e0b;\n            flex-shrink: 0;\n            white-space: nowrap;\n        }",
    'H5: sail number complete + prominent')
c = apply(c,
    "        .sailor-class {\n            font-size: 13px;\n            font-weight: 600;\n            color: #94a3b8;\n            text-transform: uppercase;\n            white-space: nowrap;\n            flex-shrink: 0;\n        }",
    "        .sailor-class {\n            font-size: 12px;\n            font-weight: 600;\n            color: #94a3b8;\n            text-transform: uppercase;\n            white-space: nowrap;\n            flex-shrink: 0;\n        }",
    'H6: class line styling')
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

# ---------- scripts/test_stations.py ----------
p = 'scripts/test_stations.py'
c = load(p)
c = apply(c,
    "assert rs['assignments_version'] == 2, rs",
    "assert rs['sheet_version'] == 2, rs",
    'T1: stations test rename')
save(p, c)

print('ALL REMAINING PATCHES APPLIED')
