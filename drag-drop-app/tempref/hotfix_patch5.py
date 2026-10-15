"""Hotfix patch 5 (RO feedback 2026-10-16, cosmetic):
- Finish tick box scaled up as large as the row allows (36px inside the 56px card).
- Class flag image REMOVED from finish-sheet sailor cards (screen real estate).
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


# ---------------- finishsheet.js: drop the flag from the card ----------------
p = BASE + r'\static\js\finishsheet.js'
d = load(p)
d = rep(d, """    const flag_img = sailor.flag_image
        ? `<img class="sailor-flag" src="/static/flags/${sailor.flag_image}" alt="${sailor.boat_class}">`
        : '';
    card.innerHTML = `
        <div class="lap-counter">
            <button class="btn-lap" data-action="lap" data-uid="${sailor.uid}" ${can_record ? '' : 'disabled'}>+ Lap</button>
            <div class="lap-value">${sailor.lap_count || 0}</div>
        </div>
        ${flag_img}
        <span class="sailor-class">${sailor.boat_class}</span>
""", """    card.innerHTML = `
        <div class="lap-counter">
            <button class="btn-lap" data-action="lap" data-uid="${sailor.uid}" ${can_record ? '' : 'disabled'}>+ Lap</button>
            <div class="lap-value">${sailor.lap_count || 0}</div>
        </div>
        <span class="sailor-class">${sailor.boat_class}</span>
""", 'card markup without flag')
save(p, d)

# ---------------- finishsheet.html: bigger finish box, remove flag CSS ----------------
p = BASE + r'\templates\finishsheet.html'
d = load(p)
d = rep(d, """        .finish-checkbox {
            width: 30px;
            height: 30px;
""", """        .finish-checkbox {
            width: 36px;
            height: 36px;
""", 'finish checkbox size')
d = rep(d, """        .sailor-flag {
            width: 48px;
            height: 38px;
            object-fit: contain;
            background: #0f172a;
            border-radius: 3px;
            padding: 2px;
            flex-shrink: 0;
        }

""", "", 'remove sailor-flag css')
d = rep(d, """            .sail-number {
                font-size: 20px;
            }

            .sailor-flag {
                width: 40px;
                height: 32px;
            }
""", """            .sail-number {
                font-size: 20px;
            }
""", 'remove media sailor-flag')
save(p, d)

print('PATCH 5 APPLIED OK')
