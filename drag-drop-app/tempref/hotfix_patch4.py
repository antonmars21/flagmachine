"""Hotfix patch 4 (RO request 2026-10-16): in the sailor registry sidebar,
a sailor selected to race (racing today) drops to the bottom of the list so
the sailors still to sign on stay at the top. The user's chosen sort order
still applies, but only within the signed-on / not-signed groups."""
import sys

BASE = r'C:\Users\anton\flagmachine\drag-drop-app'
p = BASE + r'\static\js\finishsheet.js'
with open(p, 'rb') as f:
    d = f.read()

old = """    // Apply sorting
    if (sortBy && visibleRows.length > 0) {
        visibleRows.sort((a, b) => {
            if (sortBy === "name") {
                const nameA = (a.dataset.shortName || a.dataset.sailorName || a.querySelector('.sailor-primary')?.textContent || "").toLowerCase();
                const nameB = (b.dataset.shortName || b.dataset.sailorName || b.querySelector('.sailor-primary')?.textContent || "").toLowerCase();
                return nameA.localeCompare(nameB);
            } else if (sortBy === "sailno") {
                const sailA = (a.dataset.sailNo || a.querySelector('.sailor-sail')?.textContent || "").replace(/[^\\d]/g, '').toLowerCase();
                const sailB = (b.dataset.sailNo || b.querySelector('.sailor-sail')?.textContent || "").replace(/[^\\d]/g, '').toLowerCase();
                return sailA.localeCompare(sailB);
            } else if (sortBy === "class") {
                const classA = (a.dataset.boatClass || "").toLowerCase();
                const classB = (b.dataset.boatClass || "").toLowerCase();
                const cmp = classA.localeCompare(classB);
                if (cmp !== 0) return cmp;
                const nameA = (a.dataset.shortName || "").toLowerCase();
                const nameB = (b.dataset.shortName || "").toLowerCase();
                return nameA.localeCompare(nameB);
            }
            return 0;
        });
        
        // Re-append sorted rows to maintain visibility
        const container = document.getElementById('registry-list');
        if (container) {
            visibleRows.forEach(row => container.appendChild(row));
        }
    }
"""
new = """    // Sort: sailors checked as racing today DROP TO THE BOTTOM of the list so
    // sailors still to sign on stay at the top (RO hotfix 2026-10-16). The chosen
    // sort order applies within each group; the default order keeps the
    // registry's original order within each group.
    if (visibleRows.length > 0) {
        const signedRank = r => r.classList.contains('signed-on') ? 1 : 0;
        const byCriterion = (a, b) => {
            if (sortBy === "name") {
                const nameA = (a.dataset.shortName || a.dataset.sailorName || a.querySelector('.sailor-primary')?.textContent || "").toLowerCase();
                const nameB = (b.dataset.shortName || b.dataset.sailorName || b.querySelector('.sailor-primary')?.textContent || "").toLowerCase();
                return nameA.localeCompare(nameB);
            } else if (sortBy === "sailno") {
                const sailA = (a.dataset.sailNo || a.querySelector('.sailor-sail')?.textContent || "").replace(/[^\\d]/g, '').toLowerCase();
                const sailB = (b.dataset.sailNo || b.querySelector('.sailor-sail')?.textContent || "").replace(/[^\\d]/g, '').toLowerCase();
                return sailA.localeCompare(sailB);
            } else if (sortBy === "class") {
                const classA = (a.dataset.boatClass || "").toLowerCase();
                const classB = (b.dataset.boatClass || "").toLowerCase();
                const cmp = classA.localeCompare(classB);
                if (cmp !== 0) return cmp;
                const nameA = (a.dataset.shortName || "").toLowerCase();
                const nameB = (b.dataset.shortName || "").toLowerCase();
                return nameA.localeCompare(nameB);
            }
            return 0;
        };
        visibleRows.sort((a, b) => signedRank(a) - signedRank(b) || byCriterion(a, b));
        
        // Re-append sorted rows to maintain visibility
        const container = document.getElementById('registry-list');
        if (container) {
            visibleRows.forEach(row => container.appendChild(row));
        }
    }
"""

old_b, new_b = old.encode(), new.encode()
old_crlf = old_b.replace(b'\n', b'\r\n')
if d.count(old_crlf) == 1:
    d = d.replace(old_crlf, new_b.replace(b'\n', b'\r\n'))
elif d.count(old_b) == 1:
    d = d.replace(old_b, new_b)
else:
    sys.exit('MATCH FAIL: LF count=%d CRLF count=%d' % (d.count(old_b), d.count(old_crlf)))

with open(p, 'wb') as f:
    f.write(d)
print('PATCH 4 APPLIED OK')
