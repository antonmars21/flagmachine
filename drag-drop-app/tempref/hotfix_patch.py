"""Hotfix patch 2026-10-16: RO panel compact layout + 3rd flag, finish sheet
compact one-line sailor rows + lap-count-asc ordering, 1-minute row defaults.

Exact-match replacement with count==1 assertions (same safety as an editor's
find/replace). Handles the repo's CRLF line endings by trying LF then CRLF
matches and writing the replacement in the matched style.
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


# ---------------- app.py: default row time 1 minute ----------------
p = BASE + r'\app.py'
d = load(p)
d = rep(d, """                default_minutes = 2
                if "prep" in clean_label.lower() or "p flag" in clean_label.lower():
                    default_minutes = 1
""", """                # RO hotfix 2026-10-16: every row in a start event defaults to 1 minute
                default_minutes = 1
""", 'app.py default minutes')
save(p, d)

# ---------------- app.js: 3rd flag + 1-minute fallback ----------------
p = BASE + r'\static\js\app.js'
d = load(p)
d = rep(d, "minutes: parseInt(card.dataset.minutes) || 5",
        "minutes: parseInt(card.dataset.minutes) || 1", 'app.js dragstart default')
d = rep(d, """            id: rowId, label: data.label, flag_image: data.flag, secondary_flag_image: null,
""", """            id: rowId, label: data.label, flag_image: data.flag, secondary_flag_image: null, tertiary_flag_image: null,
""", 'app.js state push tertiary')
d = rep(d, """        <div class="event-row-col col-secondary-flag">
            <div class="secondary-flag-box" data-row-id="${rowId}" draggable="false" style="width: 50px; height: 40px; background: #ddd; border: 2px dashed #999; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #666; cursor: copy;">
                <span>+Flag</span>
            </div>
        </div>
""", """        <div class="event-row-col col-secondary-flag">
            <div class="secondary-flag-box" data-row-id="${rowId}" draggable="false" style="width: 50px; height: 40px; background: #ddd; border: 2px dashed #999; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #666; cursor: copy;">
                <span>+Flag</span>
            </div>
        </div>
        <div class="event-row-col col-tertiary-flag">
            <div class="tertiary-flag-box" data-row-id="${rowId}" draggable="false" style="width: 50px; height: 40px; background: #ddd; border: 2px dashed #999; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #666; cursor: copy;">
                <span>+Flag</span>
            </div>
        </div>
""", 'app.js tertiary column')

# Secondary flag drop handlers -> shared secondary/tertiary handler (splice by markers)
start_m = b"    // Secondary flag box drop handler"
end_m = b"    row.addEventListener('dragstart'"
i, j = d.find(start_m), d.find(end_m)
if i == -1 or j == -1 or i >= j:
    sys.exit('MATCH FAIL [app.js handler block]: i=%d j=%d' % (i, j))
new_block = """    // Secondary/tertiary flag box drop handlers (up to 3 flags per row)
    row.querySelectorAll('.secondary-flag-box, .tertiary-flag-box').forEach(box => {
        const flagField = box.classList.contains('tertiary-flag-box') ? 'tertiary_flag_image' : 'secondary_flag_image';
        box.addEventListener('dragover', e => {
            e.preventDefault();
            e.stopPropagation();
            e.dataTransfer.dropEffect = 'copy';
            box.style.backgroundColor = '#90caf9';
            box.style.borderColor = '#1976d2';
        });
        box.addEventListener('dragleave', e => {
            e.stopPropagation();
            box.style.backgroundColor = '#ddd';
            box.style.borderColor = '#999';
        });
        box.addEventListener('drop', e => {
            e.preventDefault();
            e.stopPropagation();
            box.style.backgroundColor = '#ddd';
            box.style.borderColor = '#999';
            try {
                const cardData = e.dataTransfer.getData('card-data');
                if (!cardData) {
                    console.warn('No card data in drop');
                    return;
                }
                const d = JSON.parse(cardData);
                const item = state.sequence.find(s => s.id === rowId);
                if (item) {
                    item[flagField] = d.flag;
                    box.innerHTML = `<img src="/static/flags/${d.flag}" alt="Flag" style="width: 40px; height: 35px; object-fit: contain;">`;
                    syncToServer();
                }
            } catch (err) {
                console.error('Flag drop failed:', err);
            }
        });
    });

""".encode().replace(b'\n', b'\r\n')
d = d[:i] + new_block + d[j:]

d = rep(d, """                    if (r.secondary_flag_image) flags.push(r.secondary_flag_image);
""", """                    if (r.secondary_flag_image) flags.push(r.secondary_flag_image);
                    if (r.tertiary_flag_image) flags.push(r.tertiary_flag_image);
""", 'app.js class-start flags')
save(p, d)

# ---------------- index.html: add-start button bottom-right ----------------
p = BASE + r'\templates\index.html'
d = load(p)
d = rep(d, """            <div class="pane-header">
                <h2>⏱️ Start Sequence</h2>
                <button id="btn-add-grid" class="btn btn-add-grid" title="Add Start Sequence">+</button>
            </div>
""", """            <div class="pane-header">
                <h2>⏱️ Start Sequence</h2>
            </div>
""", 'index.html remove header add button')
d = rep(d, """    </main>
""", """        <button id="btn-add-grid" class="btn btn-add-grid" title="Add Start Sequence">+ Add Start</button>
    </main>
""", 'index.html bottom-right add button')
save(p, d)

# ---------------- finishsheet.html: compact one-line cards ----------------
p = BASE + r'\templates\finishsheet.html'
d = load(p)
d = rep(d, """        /* ========== SAILOR CARD ========== */
        .sailor-card {
            background-color: #1a2332;
            border: 2px solid #334155;
            border-radius: 8px;
            padding: 12px;
            cursor: grab;
            transition: all 0.2s;
            user-select: none;
        }
""", """        /* ========== SAILOR CARD (compact one-line row) ========== */
        .sailor-card {
            background-color: #1a2332;
            border: 2px solid #334155;
            border-radius: 6px;
            padding: 6px 10px;
            cursor: grab;
            transition: all 0.2s;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 8px;
            min-height: 44px;
        }
""", 'finishsheet.html sailor card')
d = rep(d, """            border: 4px solid #f59e0b;
""", """            border: 2px solid #f59e0b;
""", 'finishsheet.html class-started border')
d = rep(d, """        .sailor-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 8px;
        }

        .sail-number {
            font-size: 20px;
            font-weight: bold;
            color: #f59e0b;
        }

        .sailor-class {
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
        }

        .sailor-nickname {
            font-size: 13px;
            color: #cbd5e1;
            margin-bottom: 8px;
        }

        .sailor-controls {
            display: flex;
            gap: 8px;
            align-items: center;
            justify-content: space-between;
        }

        .lap-counter {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .lap-value {
            font-size: 18px;
            font-weight: bold;
            color: #10b981;
            min-width: 30px;
            text-align: center;
        }
""", """        .sailor-flag {
            width: 38px;
            height: 30px;
            object-fit: contain;
            background: #0f172a;
            border-radius: 3px;
            padding: 2px;
            flex-shrink: 0;
        }

        .sailor-id {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }

        .sailor-name {
            font-size: 13px;
            font-weight: 600;
            color: #f8fafc;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .sailor-class {
            font-size: 10px;
            color: #94a3b8;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .sailor-spacer {
            flex: 1;
        }

        .sail-number {
            font-size: 18px;
            font-weight: 900;
            color: #f59e0b;
            flex-shrink: 0;
        }

        .lap-counter {
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
        }

        .lap-value {
            font-size: 16px;
            font-weight: bold;
            color: #10b981;
            min-width: 22px;
            text-align: center;
        }
""", 'finishsheet.html card fields')
d = rep(d, """        .sailors-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 12px;
        }
""", """        .sailors-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 8px;
        }
""", 'finishsheet.html sailors list')
d = rep(d, """        .btn-lap {
            padding: 6px 12px;
""", """        .btn-lap {
            padding: 5px 10px;
""", 'finishsheet.html lap button')
d = rep(d, """        .finish-checkbox {
            width: 24px;
            height: 24px;
""", """        .finish-checkbox {
            width: 22px;
            height: 22px;
""", 'finishsheet.html finish checkbox')
d = rep(d, """            .sailor-card {
                padding: 10px;
            }
""", """            .sailor-card {
                padding: 5px 8px;
                gap: 6px;
                min-height: 40px;
            }
""", 'finishsheet.html media card')
d = rep(d, """            .sail-number {
                font-size: 18px;
            }
""", """            .sail-number {
                font-size: 16px;
            }

            .sailor-flag {
                width: 32px;
                height: 26px;
            }
""", 'finishsheet.html media sail number')
save(p, d)

# ---------------- finishsheet.js: one-line markup + lap asc sort ----------------
p = BASE + r'\static\js\finishsheet.js'
d = load(p)
d = rep(d, """    const finished_class = sailor.finish_time ? ' (Finished)' : '';
""", """    const finished_class = sailor.finish_time ? ' (Fin)' : '';
""", 'finishsheet.js finished label')
d = rep(d, """    card.innerHTML = `
        <div class="sailor-header">
            <span class="sail-number">${sailor.sail_no}</span>
            <span class="sailor-class">${sailor.boat_class}</span>
        </div>
        <div class="sailor-nickname">${sailor.short_name}${finished_class}</div>
        <div class="sailor-controls">
            <div class="lap-counter">
                <button class="btn-lap" data-action="lap" data-uid="${sailor.uid}" ${can_record ? '' : 'disabled'}>+ Lap</button>
                <div class="lap-value">${sailor.lap_count || 0}</div>
            </div>
            <input type="checkbox" class="finish-checkbox" data-uid="${sailor.uid}" 
                ${sailor.finish_time ? 'checked disabled' : (can_record ? '' : 'disabled')}>
        </div>
    `;
""", """    const flag_img = sailor.flag_image
        ? `<img class="sailor-flag" src="/static/flags/${sailor.flag_image}" alt="${sailor.boat_class}">`
        : '';
    card.innerHTML = `
        ${flag_img}
        <div class="sailor-id">
            <div class="sailor-name">${sailor.short_name}${finished_class}</div>
            <div class="sailor-class">${sailor.boat_class}</div>
        </div>
        <div class="sailor-spacer"></div>
        <span class="sail-number">${sailor.sail_no}</span>
        <div class="lap-counter">
            <button class="btn-lap" data-action="lap" data-uid="${sailor.uid}" ${can_record ? '' : 'disabled'}>+ Lap</button>
            <div class="lap-value">${sailor.lap_count || 0}</div>
        </div>
        <input type="checkbox" class="finish-checkbox" data-uid="${sailor.uid}" 
            ${sailor.finish_time ? 'checked disabled' : (can_record ? '' : 'disabled')}>
    `;
""", 'finishsheet.js card markup')
d = rep(d, """/**
 * Comparator for auto-sorting non-manual, unfinished cards:
 * lap_count desc, then last lap time asc, then handicap asc, then seed asc.
 */
function compareByLapThenTimeThenHandicap(a, b) {
    const lapDiff = (parseInt(b.dataset.lapCount) || 0) - (parseInt(a.dataset.lapCount) || 0);
""", """/**
 * Comparator for auto-sorting non-manual, unfinished cards:
 * lap_count asc (sailors approaching their next lap completion stay at the top;
 * completing a lap moves the sailor down the list), then last lap time asc,
 * then handicap asc, then seed asc.
 */
function compareByLapThenTimeThenHandicap(a, b) {
    const lapDiff = (parseInt(a.dataset.lapCount) || 0) - (parseInt(b.dataset.lapCount) || 0);
""", 'finishsheet.js comparator asc')
d = rep(d, """ * - Unfinished sailors are ordered by lap count (desc), then seed (asc) as tie-break.
""", """ * - Unfinished sailors are ordered by lap count (asc - lowest first), so sailors
 *   approaching lap completion stay at the top; completing a lap moves them down.
""", 'finishsheet.js resort doc')
save(p, d)

print('ALL PATCHES APPLIED OK')
