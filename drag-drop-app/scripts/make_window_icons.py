"""Generate the four window icons (taskbar navigator).

Each page opened by START.bat as a Chrome/Edge --app window uses the page's
FAVICON as its window/taskbar icon, so every work window gets a distinct,
instantly recognisable icon:

    RO control      red square, white 'RO'
    Finish Sheet 1  green square, white '1'
    Finish Sheet 2  blue square, white '2'
    Display Board   orange square, white 'D'

Icons are drawn VECTOR-style (stroke capsules + ellipse rings, never a
pixel font) and anti-aliased with 9 subsamples per pixel, on a rounded
square with a vertical gradient and transparent corners - crisp at every
taskbar size instead of the previous blocky scaled-up 5x7 font.

Pure-stdlib PNG writer (no Pillow dependency, matching the project rule of
no new pip requirements). Output: static/icons/icon_<key>.png (128x128 RGBA).

Run:  python scripts/make_window_icons.py
         python scripts/make_window_icons.py --preview   (ASCII check)
"""
import math
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'static', 'icons')

SIZE = 128          # output canvas
SUB = 3             # subsamples per axis -> 9x anti-aliasing
RR_INSET = 5        # background rounded-rect inset
RR_RADIUS = 26

# ---- vector primitives (128-unit space, y down) --------------------------

def capsule(x1, y1, x2, y2, r):
    """Thick round-capped line segment."""
    def test(x, y):
        dx, dy = x2 - x1, y2 - y1
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        px, py = x1 + t * dx, y1 + t * dy
        return (x - px) ** 2 + (y - py) ** 2 <= r * r
    return test


def ering(cx, cy, rx_out, rx_in, ry_out, ry_in):
    """Ellipse ring (annulus): inside the outer ellipse, outside the inner."""
    def test(x, y):
        ox, oy = (x - cx) / rx_out, (y - cy) / ry_out
        if ox * ox + oy * oy > 1:
            return False
        ix, iy = (x - cx) / rx_in, (y - cy) / ry_in
        return ix * ix + iy * iy >= 1
    return test


def hring(cx, cy, rx_out, rx_in, ry_out, ry_in):
    """Right half of an ellipse ring (bowls of R and D)."""
    ring = ering(cx, cy, rx_out, rx_in, ry_out, ry_in)
    return lambda x, y: x >= cx and ring(x, y)


def sector(cx, cy, rx_out, rx_in, ry_out, ry_in, a_start, a_end):
    """Ellipse ring clipped to an angle sweep. Angles in degrees, y-UP
    convention, sweeping DOWN from a_start to a_end (no 180-degree wrap)."""
    ring = ering(cx, cy, rx_out, rx_in, ry_out, ry_in)
    a0, a1 = a_start, a_end

    def test(x, y):
        if not ring(x, y):
            return False
        a = math.degrees(math.atan2(-(y - cy), x - cx))
        return a1 <= a <= a0
    return test


# ---- glyphs (stroke width comes from the primitive radii) ----------------

GLYPHS = {
    # 'RO' - stem, right-half-ring bowl, diagonal leg + tall ellipse-ring O
    'RO': [capsule(18, 30, 18, 98, 8),
           hring(18, 52, 26, 12, 22, 10),
           capsule(40, 66, 68, 98, 8),
           ering(96, 64, 21, 10, 34, 22)],
    # '1' - angled flag, tall stem, wide base serif
    '1': [capsule(42, 22, 70, 42, 9),
          capsule(78, 22, 78, 90, 10),
          capsule(46, 100, 110, 100, 10)],
    # '2' - top arc sweeping over the right, diagonal, base bar
    '2': [sector(64, 56, 34, 18, 28, 12, 160, -15),
          capsule(88, 60, 42, 96, 10),
          capsule(36, 108, 94, 108, 11)],
    # 'D' - stem + right-half-ring bowl
    'D': [capsule(34, 22, 34, 106, 10),
          hring(34, 64, 54, 38, 42, 26)],
}

ICONS = {
    # name:         (gradient top rgb, gradient bottom rgb, glyph key)
    'icon_ro':      ((239, 68, 68), (153, 27, 27), 'RO'),
    'icon_fs1':     ((74, 222, 128), (21, 128, 61), '1'),
    'icon_fs2':     ((96, 165, 250), (29, 78, 216), '2'),
    'icon_display': ((251, 146, 60), (194, 65, 12), 'D'),
}


# ---- rasterizer -----------------------------------------------------------

def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def inside_rounded_rect(x, y):
    """Coverage test point for the background rounded square."""
    x0, y0, x1, y1 = RR_INSET, RR_INSET, SIZE - RR_INSET, SIZE - RR_INSET
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    r = RR_RADIUS
    qx = min(x - x0, x1 - x)
    qy = min(y - y0, y1 - y)
    if qx >= r or qy >= r:
        return True
    return qx * qx + qy * qy <= r * r


def make_icon(top_rgb, bottom_rgb, glyph_key):
    shapes = GLYPHS[glyph_key]
    px = [[None] * SIZE for _ in range(SIZE)]
    step = 1.0 / SUB
    for py in range(SIZE):
        for pxx in range(SIZE):
            bg_cov = 0
            glyph_cov = 0
            for si in range(SUB):
                for sj in range(SUB):
                    sx = pxx + (si + 0.5) * step
                    sy = py + (sj + 0.5) * step
                    if inside_rounded_rect(sx, sy):
                        bg_cov += 1
                        if any(sh(sx, sy) for sh in shapes):
                            glyph_cov += 1
            n = SUB * SUB
            bg_cov /= n
            glyph_cov /= n
            if bg_cov == 0:
                px[py][pxx] = (0, 0, 0, 0)
                continue
            # vertical gradient; the anti-aliased border gets a darker edge
            t = py / (SIZE - 1)
            rgb = lerp(top_rgb, bottom_rgb, t)
            if bg_cov < 1:
                rgb = tuple(max(0, c - 40) for c in rgb)
            # white glyph blended over the background
            g = glyph_cov / bg_cov if bg_cov else 0
            g = min(1.0, g)
            rgb = tuple(round(rgb[i] + (255 - rgb[i]) * g) for i in range(3))
            px[py][pxx] = (*rgb, round(255 * bg_cov))
    return px


def write_png(path, size, pixels):
    """pixels: rows of (r, g, b, a) tuples."""
    raw = b''.join(
        b'\x00' + b''.join(struct.pack('BBBB', *p) for p in row)
        for row in pixels
    )

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body))

    png = (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw, 9))
        + chunk(b'IEND', b'')
    )
    with open(path, 'wb') as f:
        f.write(png)


def preview(pixels):
    """ASCII render (luminance) to eyeball the glyph shapes."""
    for y in range(0, SIZE, 3):
        line = ''
        for x in range(0, SIZE, 2):
            r, g, b, a = pixels[y][x]
            lum = (r + g + b) / 3 if a else 0
            line += ' ' if lum < 60 else ('.' if lum < 130 else ('+' if lum < 210 else '#'))
        print(line)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    preview_mode = '--preview' in sys.argv
    for name, (top, bottom, glyph) in ICONS.items():
        pixels = make_icon(top, bottom, glyph)
        if preview_mode:
            print(f'== {name} ({glyph}) ==')
            preview(pixels)
        path = os.path.join(OUT_DIR, name + '.png')
        write_png(path, SIZE, pixels)
        print(f'wrote {path} ({SIZE}x{SIZE} RGBA, glyph {glyph!r})')


if __name__ == '__main__':
    main()
