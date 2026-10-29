"""Generate the four window icons (taskbar navigator, bug 32/34 follow-up).

Each page opened by START.bat as a Chrome/Edge --app window uses the page's
FAVICON as its window/taskbar icon, so every work window gets a distinct,
instantly recognisable icon:

    RO control      red square, white 'RO'
    Finish Sheet 1  green square, white '1'
    Finish Sheet 2  blue square, white '2'
    Display Board   orange square, white 'D'

Pure-stdlib PNG writer (no Pillow dependency, matching the project rule of
no new pip requirements). Output: static/icons/icon_<key>.png (128x128).

Run:  python scripts/make_window_icons.py
"""
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'static', 'icons')

SIZE = 128

# 5x7 block font - '#' = glyph pixel
FONT = {
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'D': ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
    '1': ['..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.'],
    '2': ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'],
}

ICONS = {
    # name:        (background rgb, glyph text)
    'icon_ro':      ((185, 28, 28), 'RO'),
    'icon_fs1':     ((21, 128, 61), '1'),
    'icon_fs2':     ((29, 78, 216), '2'),
    'icon_display': ((194, 65, 12), 'D'),
}


def write_png(path, size, pixels):
    """pixels: list of rows, each row a list of (r, g, b) tuples."""
    raw = b''.join(
        b'\x00' + b''.join(struct.pack('BBB', *px) for px in row)
        for row in pixels
    )

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body))

    png = (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw, 9))
        + chunk(b'IEND', b'')
    )
    with open(path, 'wb') as f:
        f.write(png)


def make_icon(bg, text):
    scale = 16 if len(text) == 1 else 10
    gap = 4 if len(text) == 1 else 8
    glyphs = [FONT[ch] for ch in text]
    gw = len(glyphs) * 5 * scale + (len(glyphs) - 1) * gap
    x0 = (SIZE - gw) // 2
    y0 = (SIZE - 7 * scale) // 2
    pixels = [[bg for _ in range(SIZE)] for _ in range(SIZE)]
    for gi, glyph in enumerate(glyphs):
        gx = x0 + gi * (5 * scale + gap)
        for ry, row in enumerate(glyph):
            for rx, cell in enumerate(row):
                if cell == '#':
                    for dy in range(scale):
                        for dx in range(scale):
                            pixels[y0 + ry * scale + dy][gx + rx * scale + dx] = (255, 255, 255)
    return pixels


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, (bg, text) in ICONS.items():
        path = os.path.join(OUT_DIR, name + '.png')
        write_png(path, SIZE, make_icon(bg, text))
        print(f'wrote {path} ({SIZE}x{SIZE}, glyph {text!r})')


if __name__ == '__main__':
    main()
