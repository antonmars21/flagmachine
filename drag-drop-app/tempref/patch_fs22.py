import io

path = 'static/js/finishsheet.js'
src = io.open(path, encoding='utf-8', newline='').read()
NL = '\r\n'

# --- 1. pollClassStarts: re-enable Start button when sheet is READY again (bug 22) ---
old = (
"        if (state.race_active) {" + NL +
"            document.getElementById('btn-start-race').disabled = true;" + NL +
"            document.getElementById('btn-end-race').disabled = false;" + NL +
"        }"
)
new = (
"        if (state.race_active) {" + NL +
"            document.getElementById('btn-start-race').disabled = true;" + NL +
"            document.getElementById('btn-end-race').disabled = false;" + NL +
"        } else if (!state.race_ended) {" + NL +
"            // READY for the next race of the day (after end+reset or reset-race)" + NL +
"            document.getElementById('btn-start-race').disabled = false;" + NL +
"            document.getElementById('btn-end-race').disabled = true;" + NL +
"        }"
)
assert src.count(old) == 1, f"poll anchor: {src.count(old)}"
src = src.replace(old, new)

# --- 2. Registry Reset Finish Sheet button: always re-render, handle failure (bug 22) ---
old = (
"    if (btnResetFinishSheet) {" + NL +
"        btnResetFinishSheet.addEventListener('click', () => {" + NL +
"            if (!confirm('Reset the finish sheet?\\nAll finish times and orders will be cleared.')) return;" + NL +
"            fetch('/api/reset-finish-sheet', { method: 'POST' })" + NL +
"                .then(res => {" + NL +
"                    if (res.ok) {" + NL +
"                        loadRegistryList();" + NL +
"                        if (!state.race_active) loadAndRenderSailors();" + NL +
"                        // Reapply filters after resetting finish sheet" + NL +
"                        setTimeout(applyRegistryFilters, 100);" + NL +
"                    }" + NL +
"                });" + NL +
"        });" + NL +
"    }"
)
new = (
"    if (btnResetFinishSheet) {" + NL +
"        btnResetFinishSheet.addEventListener('click', () => {" + NL +
"            if (!confirm('Reset the finish sheet?\\nThe sheet will be cleared and made ready for the next race.\\nRecorded results are kept in the database.')) return;" + NL +
"            fetch('/api/reset-finish-sheet', { method: 'POST' })" + NL +
"                .then(res => {" + NL +
"                    if (res.ok) {" + NL +
"                        loadRegistryList();" + NL +
"                        loadAndRenderSailors();" + NL +
"                        // Reapply filters after resetting finish sheet" + NL +
"                        setTimeout(applyRegistryFilters, 100);" + NL +
"                    } else {" + NL +
"                        res.json().then(d => alert(d.message || 'Reset failed')).catch(() => {});" + NL +
"                    }" + NL +
"                });" + NL +
"        });" + NL +
"    }"
)
assert src.count(old) == 1, f"reset anchor: {src.count(old)}"
src = src.replace(old, new)

io.open(path, 'w', encoding='utf-8', newline='').write(src)
print('finishsheet.js patched OK')
