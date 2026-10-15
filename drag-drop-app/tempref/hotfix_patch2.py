"""Hotfix patch 2: include the tertiary flag slot in backend sequence logic
(active class IDs, class-sequence mapping, open-flag detection, finish-sheet
column creation). Display-board JSON (primary+secondary only) untouched."""
import sys

BASE = r'C:\Users\anton\flagmachine\drag-drop-app'
p = BASE + r'\app.py'
with open(p, 'rb') as f:
    d = f.read()

old1 = b"for fi in (item.get('flag_image'), item.get('secondary_flag_image')):"
new1 = b"for fi in (item.get('flag_image'), item.get('secondary_flag_image'), item.get('tertiary_flag_image')):"
old2 = b"for flag_image in (item.get('flag_image'), item.get('secondary_flag_image')):"
new2 = b"for flag_image in (item.get('flag_image'), item.get('secondary_flag_image'), item.get('tertiary_flag_image')):"

for old, new, expected in [(old1, new1, 2), (old2, new2, 2)]:
    old_crlf = old.replace(b'\n', b'\r\n')
    n = d.count(old) or d.count(old_crlf)
    if n != expected:
        sys.exit('MATCH FAIL: expected %d got %d for %r' % (expected, n, old[:60]))
    d = d.replace(old, new)

# Update the two stale comments
old_c1 = b"# Match ALL flags in the start event: primary + secondary"
new_c1 = b"# Match ALL flags in the start event: primary + secondary + tertiary"
if d.count(old_c1) >= 1:
    d = d.replace(old_c1, new_c1)
old_c2 = b"Both primary and secondary flags create a column (shared start = two columns)."
new_c2 = b"Primary, secondary and tertiary flags all create a column (shared start)."
if d.count(old_c2) == 1:
    d = d.replace(old_c2, new_c2)

with open(p, 'wb') as f:
    f.write(d)
print('PATCH 2 APPLIED OK')
