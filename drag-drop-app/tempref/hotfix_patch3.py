"""Hotfix patch 3 (RO human-test feedback 2026-10-16, cosmetic only):
- Sailor card: lap counter on the LEFT, finish tick box on the FAR RIGHT
  (prevents accidental finish clicks); class, name, sail number inline.
- Card fonts/sizes +25%; lap button and finish checkbox +40%.
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


# ---------------- finishsheet.html: card CSS sizes + inline fields ----------------
p = BASE + r'\templates\finishsheet.html'
d = load(p)
d = rep(d, """        .sailor-card {
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
""", """        .sailor-card {
            background-color: #1a2332;
            border: 2px solid #334155;
            border-radius: 6px;
            padding: 8px 12px;
            cursor: grab;
            transition: all 0.2s;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 56px;
        }
""", 'sailor card size')
d = rep(d, """        .sailor-flag {
            width: 38px;
            height: 30px;
""", """        .sailor-flag {
            width: 48px;
            height: 38px;
""", 'sailor flag size')
d = rep(d, """        .sailor-id {
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
""", """        .sailor-class {
            font-size: 13px;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            white-space: nowrap;
            flex-shrink: 0;
        }

        .sailor-name {
            font-size: 16px;
            font-weight: 600;
            color: #f8fafc;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            min-width: 0;
        }
""", 'inline class/name')
d = rep(d, """        .sail-number {
            font-size: 18px;
""", """        .sail-number {
            font-size: 22px;
""", 'sail number size')
d = rep(d, """        .lap-value {
            font-size: 16px;
            font-weight: bold;
            color: #10b981;
            min-width: 22px;
            text-align: center;
        }
""", """        .lap-value {
            font-size: 20px;
            font-weight: bold;
            color: #10b981;
            min-width: 26px;
            text-align: center;
        }
""", 'lap value size')
d = rep(d, """        .btn-lap {
            padding: 5px 10px;
""", """        .btn-lap {
            padding: 7px 14px;
""", 'lap button padding')
d = rep(d, """            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
            transition: all 0.2s;
        }

        .btn-lap:hover {
""", """            cursor: pointer;
            font-weight: bold;
            font-size: 17px;
            transition: all 0.2s;
        }

        .btn-lap:hover {
""", 'lap button font')
d = rep(d, """        .finish-checkbox {
            width: 22px;
            height: 22px;
""", """        .finish-checkbox {
            width: 30px;
            height: 30px;
""", 'finish checkbox size')
d = rep(d, """        .sailors-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 8px;
        }
""", """        .sailors-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 10px;
        }
""", 'sailors list spacing')
d = rep(d, """            .sailor-card {
                padding: 5px 8px;
                gap: 6px;
                min-height: 40px;
            }
""", """            .sailor-card {
                padding: 6px 10px;
                gap: 8px;
                min-height: 50px;
            }
""", 'media card')
d = rep(d, """            .sail-number {
                font-size: 16px;
            }

            .sailor-flag {
                width: 32px;
                height: 26px;
            }
""", """            .sail-number {
                font-size: 20px;
            }

            .sailor-flag {
                width: 40px;
                height: 32px;
            }
""", 'media sizes')
save(p, d)

# ---------------- finishsheet.js: lap left, finish far right ----------------
p = BASE + r'\static\js\finishsheet.js'
d = load(p)
d = rep(d, """    card.innerHTML = `
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
""", """    card.innerHTML = `
        <div class="lap-counter">
            <button class="btn-lap" data-action="lap" data-uid="${sailor.uid}" ${can_record ? '' : 'disabled'}>+ Lap</button>
            <div class="lap-value">${sailor.lap_count || 0}</div>
        </div>
        ${flag_img}
        <span class="sailor-class">${sailor.boat_class}</span>
        <span class="sailor-name">${sailor.short_name}${finished_class}</span>
        <div class="sailor-spacer"></div>
        <span class="sail-number">${sailor.sail_no}</span>
        <input type="checkbox" class="finish-checkbox" data-uid="${sailor.uid}" 
            ${sailor.finish_time ? 'checked disabled' : (can_record ? '' : 'disabled')}>
    `;
""", 'card markup order')
save(p, d)

print('PATCH 3 APPLIED OK')
