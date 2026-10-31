"""Quick JS structural sanity check: strips comments and string/template
literals, then verifies brackets are balanced (catches broken patches)."""
import sys

def strip_js(src):
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            i = n if j == -1 else j
        elif c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i)
            i = n if j == -1 else j + 2
        elif c in ("'", '"', '`'):
            q = c
            i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)

ok_all = True
for f in sys.argv[1:]:
    s = strip_js(open(f, encoding='utf-8', errors='replace').read())
    stack = []
    pairs = {'}': '{', ')': '(', ']': '['}
    ok = True
    for ch in s:
        if ch in '{([':
            stack.append(ch)
        elif ch in '})]':
            if not stack or stack[-1] != pairs[ch]:
                print(f, 'MISMATCH at', repr(ch), 'depth', len(stack))
                ok = False
                ok_all = False
                break
            stack.pop()
    if ok and stack:
        print(f, 'UNCLOSED:', stack[:6])
        ok_all = False
    elif ok:
        print(f, 'BALANCED OK')
sys.exit(0 if ok_all else 1)
