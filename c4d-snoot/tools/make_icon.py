"""Render res/icons/snoot.png (64x64 RGBA) without third-party libraries.

Side view: an area light panel, the snoot tapering away from it and the
orange beam leaving the opening. Run from the repository root:

    python3 tools/make_icon.py
"""

import os
import struct
import zlib

SIZE = 64
SAMPLES = 4  # supersampling per axis

OUT = os.path.join(os.path.dirname(__file__), "..", "snoot", "res", "icons", "snoot.png")

# (polygon in 64x64 space, RGBA colour), painted in order.
SHAPES = [
    # Beam
    ([(46, 24), (62, 14), (62, 50), (46, 40)], (255, 140, 0, 110)),
    # Snoot body (tapered tube, side view)
    ([(14, 8), (48, 20), (48, 44), (14, 56)], (58, 58, 62, 255)),
    # Inner wall visible at the opening
    ([(44, 21), (48, 20), (48, 44), (44, 43)], (235, 235, 235, 255)),
    # Light panel
    ([(8, 6), (14, 6), (14, 58), (8, 58)], (250, 250, 250, 255)),
    # Handles
    ([(46, 29), (50, 29), (50, 35), (46, 35)], (255, 140, 0, 255)),
    ([(45, 16), (51, 16), (51, 22), (45, 22)], (255, 140, 0, 255)),
]


def inside(polygon, x, y):
    result = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            result = not result
        j = i
    return result


def render():
    pixels = [[(0.0, 0.0, 0.0, 0.0)] * SIZE for _ in range(SIZE)]
    step = 1.0 / SAMPLES
    for polygon, (r, g, b, a) in SHAPES:
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        for py in range(max(int(min(ys)) - 1, 0), min(int(max(ys)) + 2, SIZE)):
            for px in range(max(int(min(xs)) - 1, 0), min(int(max(xs)) + 2, SIZE)):
                hits = sum(
                    inside(polygon, px + (sx + 0.5) * step, py + (sy + 0.5) * step)
                    for sx in range(SAMPLES) for sy in range(SAMPLES))
                if not hits:
                    continue
                alpha = (a / 255.0) * hits / float(SAMPLES * SAMPLES)
                dr, dg, db, da = pixels[py][px]
                out_a = alpha + da * (1.0 - alpha)
                if out_a <= 0.0:
                    continue
                blend = lambda src, dst: (src / 255.0 * alpha + dst * da * (1.0 - alpha)) / out_a
                pixels[py][px] = (blend(r, dr), blend(g, dg), blend(b, db), out_a)
    return pixels


def write_png(path, pixels):
    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *(int(round(c * 255)) for c in pixel)) for pixel in row)
        for row in pixels)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)


if __name__ == "__main__":
    write_png(OUT, render())
    print("wrote %s" % os.path.normpath(OUT))
