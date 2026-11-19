#!/usr/bin/env python3
"""The World on Thursday - 19 November 2026 in one picture.

A deterministic, standard-library-only Python program that draws a
newspaper front page summing up the world news of Thursday,
19 November 2026, and writes it as a PNG to the output directory
(MAKEFUN_OUTPUT_DIR, or /output in the make.fun sandbox).

Every letter, headline and illustration is drawn by this program's own
code: a hand-rolled 5x7 typeface, simple drawing primitives and a zlib
PNG encoder. No network, no external files, no randomness - two runs
always write exactly the same bytes.
"""

import math
import os
import struct
import zlib

# ---------------------------------------------------------------- canvas

W = 1024
H = 1024

PAPER = (247, 241, 227)
INK = (26, 26, 26)
RED = (178, 32, 42)
DARKRED = (140, 22, 32)
BLUE = (29, 78, 137)
SKYBLUE = (120, 170, 220)
GREEN = (46, 125, 50)
SAND = (226, 205, 160)
GREY = (110, 110, 110)
LIGHTGREY = (205, 200, 186)
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
GOLD = (214, 164, 32)
BROWN = (120, 78, 40)
WATER = (64, 120, 180)
NIGHT = (24, 42, 92)

img = bytearray(W * H * 3)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        img[i] = c[0]
        img[i + 1] = c[1]
        img[i + 2] = c[2]


def rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        img[i:i + len(row)] = row


def rect_outline(x, y, w, h, c, th=2):
    rect(x, y, w, th, c)
    rect(x, y + h - th, w, th, c)
    rect(x, y, th, h, c)
    rect(x + w - th, y, th, h, c)


def circle(cx, cy, r, c, fill=True):
    r2 = r * r
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
            if fill:
                if d2 <= r2:
                    px(xx, yy, c)
            else:
                if r2 - 2 * r <= d2 <= r2 + 2 * r:
                    px(xx, yy, c)


def line(x0, y0, x1, y1, c, th=2):
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    r = max(0, th // 2)
    for s in range(steps + 1):
        x = x0 + (x1 - x0) * s // steps
        y = y0 + (y1 - y0) * s // steps
        if r == 0:
            px(x, y, c)
        else:
            circle(x, y, r, c)


def poly(points, c):
    ys = [p[1] for p in points]
    y_lo = max(0, min(ys))
    y_hi = min(H - 1, max(ys))
    n = len(points)
    for yy in range(y_lo, y_hi + 1):
        nodes = []
        for i in range(n):
            xa, ya = points[i]
            xb, yb = points[(i + 1) % n]
            if (ya <= yy < yb) or (yb <= yy < ya):
                nodes.append(xa + (yy - ya) * (xb - xa) // (yb - ya))
        nodes.sort()
        for i in range(0, len(nodes) - 1, 2):
            rect(nodes[i], yy, nodes[i + 1] - nodes[i] + 1, 1, c)


# ------------------------------------------------------------------ font
# A hand-drawn 5x7 typeface. Each glyph is 7 rows of 5 pixels.

FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    'a': (".....", ".....", ".####", "....#", ".####", "#...#", ".####"),
    'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    'c': (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    'f': ("..##.", ".#...", ".#...", "####.", ".#...", ".#...", ".#..."),
    'g': (".....", ".....", ".####", "#...#", ".####", "....#", ".###."),
    'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'i': ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    'j': ("...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##.."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    'p': (".....", ".....", "####.", "#...#", "####.", "#....", "#...."),
    'q': (".....", ".....", ".####", "#...#", ".####", "....#", "....#"),
    'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    't': (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".#.##"),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'w': (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'y': (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': (".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '%': ("##..#", "##.#.", "...#.", "..#..", ".#...", "#..##", "#..##"),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '/': ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    '*': (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '\u00b7': (".....", ".....", ".....", ".##..", ".##..", ".....", "....."),
    '\u2013': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '\u2014': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '\u2018': ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '\u2019': ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '\u201c': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '\u201d': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
}


def text_w(s, scale):
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def draw_text(x, y, s, scale, c):
    cx = x
    for ch in s:
        glyph = FONT.get(ch)
        if glyph is None:
            glyph = FONT[' ']
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '#':
                    rect(cx + col * scale, y + row * scale, scale, scale, c)
        cx += 6 * scale
    return cx


def draw_text_center(y, s, scale, c, cx=W // 2):
    draw_text(cx - text_w(s, scale) // 2, y, s, scale, c)


def wrap(s, scale, max_w):
    words = s.split()
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(x, y, s, scale, c, max_w, lh):
    for ln in wrap(s, scale, max_w):
        draw_text(x, y, ln, scale, c)
        y += lh
    return y


# ------------------------------------------------------------ PNG output

def png_bytes():
    raw = bytearray()
    stride = W * 3
    for yy in range(H):
        raw.append(0)
        raw += img[yy * stride:(yy + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# ------------------------------------------------------------ illustrations

def flag_us(x, y, w, h):
    for i in range(7):
        rect(x, y + i * h // 7, w, h // 7 + 1, RED if i % 2 == 0 else WHITE)
    rect(x, y, w * 2 // 5, h * 4 // 7, BLUE)
    for r in range(4):
        for s in range(5):
            px(x + 4 + s * w // 13, y + 3 + r * h // 9, WHITE)
            rect(x + 3 + s * w // 13, y + 2 + r * h // 9, 2, 2, WHITE)


def flag_cn(x, y, w, h):
    rect(x, y, w, h, RED)
    star(x + w // 6, y + h // 4, 5, GOLD)
    for dx, dy in ((3, 1), (3, 2), (3, 3)):
        star(x + w // 6 + dx * w // 12, y + dy * h // 8, 2, GOLD)


def flag_ru(x, y, w, h):
    rect(x, y, w, h // 3 + 1, WHITE)
    rect(x, y + h // 3, w, h // 3 + 1, BLUE)
    rect(x, y + 2 * h // 3, w, h // 3 + 1, RED)


def star(cx, cy, r, c):
    for a in range(5):
        ang = -math.pi / 2 + a * 2 * math.pi / 5
        x2 = int(cx + r * 2.2 * math.cos(ang))
        y2 = int(cy + r * 2.2 * math.sin(ang))
        line(cx, cy, x2, y2, c, 2)
    circle(cx, cy, r, c)


def illo_summit(x, y, w, h):
    """Three flags over a summit table."""
    rect(x, y, w, h, NIGHT)
    for i in range(14):
        sx = x + 12 + (i * 53) % (w - 24)
        sy = y + 8 + (i * 29) % (h // 3)
        px(sx, sy, WHITE)
        px(sx + 1, sy, WHITE)
    fw = w // 4
    fh = h // 2
    fy = y + 16
    flag_us(x + w // 16, fy, fw, fh)
    flag_cn(x + w // 2 - fw // 2, fy - 6, fw, fh)
    flag_ru(x + w - w // 16 - fw, fy, fw, fh)
    for fx in (x + w // 16, x + w // 2, x + w - w // 16):
        line(fx, fy + fh, fx, y + h - 26, GREY, 2)
    poly([(x + 18, y + h - 8), (x + w - 18, y + h - 8),
          (x + w - 52, y + h - 30), (x + 52, y + h - 30)], BROWN)
    for i in range(3):
        cx = x + w // 4 + i * w // 4
        circle(cx, y + h - 34, 7, GOLD)


def illo_court(x, y, w, h):
    """Courthouse with the scales of justice."""
    rect(x, y, w, h, (232, 222, 196))
    cx = x + w // 2
    roof_y = y + 14
    poly([(cx - 52, roof_y + 22), (cx + 52, roof_y + 22), (cx, roof_y)], INK)
    rect(cx - 58, roof_y + 26, 116, 6, INK)
    for i in range(5):
        colx = cx - 48 + i * 24
        rect(colx, roof_y + 36, 8, 44, INK)
    rect(cx - 58, roof_y + 82, 116, 6, INK)
    sx = cx
    sy = roof_y + 44
    line(sx, sy - 26, sx, sy + 26, DARKRED, 3)
    line(sx - 30, sy - 20, sx + 30, sy - 20, DARKRED, 3)
    for side in (-1, 1):
        px_ = sx + side * 30
        line(px_ - 10, sy - 20, px_, sy - 2, DARKRED, 2)
        line(px_ + 10, sy - 20, px_, sy - 2, DARKRED, 2)
        poly([(px_ - 13, sy - 2), (px_ + 13, sy - 2), (px_, sy + 7)], DARKRED)


def illo_bridge(x, y, w, h):
    """The Crimean Bridge: one span down in the water."""
    rect(x, y, w, h, SKYBLUE)
    circle(x + w - 42, y + 26, 13, GOLD)
    wy = y + h - 34
    rect(x, wy, w, h - (wy - y), WATER)
    for i in range(6):
        wx = x + 14 + i * (w // 6)
        line(wx, wy + 12 + (i % 2) * 7, wx + 22, wy + 12 + (i % 2) * 7, WHITE, 2)
    deck = wy - 44
    for px_x in (x + 34, x + w - 60):
        rect(px_x, deck - 26, 10, 70, GREY)
    rect(x + 6, deck, w // 2 - 30, 8, INK)
    rect(x + w // 2 + 38, deck, w // 2 - 44, 8, INK)
    poly([(x + w // 2 - 24, deck + 2), (x + w // 2 + 30, deck + 2),
          (x + w // 2 + 40, deck + 30), (x + w // 2 - 8, deck + 30)], INK)
    for i in range(4):
        gx = x + w // 2 - 6 + i * 9
        gy = deck - 16 - (i % 2) * 8
        circle(gx, gy, 6 + (i % 3), GREY)


def illo_tank(x, y, w, h):
    """A tank silhouette under a hard sun."""
    rect(x, y, w, h, SAND)
    circle(x + 34, y + 24, 12, RED)
    gy = y + h - 18
    rect(x, gy, w, 18, BROWN)
    tx = x + w // 2
    ty = gy - 26
    poly([(tx - 52, ty + 18), (tx + 56, ty + 18), (tx + 44, ty),
          (tx - 38, ty)], (58, 66, 44))
    rect(tx - 62, ty + 16, 130, 14, (44, 50, 34))
    for i in range(5):
        circle(tx - 48 + i * 26, ty + 23, 6, BLACK)
    poly([(tx - 16, ty - 16), (tx + 22, ty - 16), (tx + 14, ty),
          (tx - 8, ty)], (58, 66, 44))
    line(tx + 18, ty - 10, tx + 78, ty - 16, BLACK, 5)
    for i in range(3):
        rect(x + 16 + i * 30, gy - 6, 16, 4, BROWN)


def illo_tower(x, y, w, h):
    """Riyadh's PIF Tower, its crown damaged by falling debris."""
    rect(x, y, w, h, NIGHT)
    for i in range(10):
        px(x + 10 + (i * 37) % (w - 20), y + 8 + (i * 23) % 26, WHITE)
    tw = 54
    tx = x + w // 2 - tw // 2
    top = y + 22
    bot = y + h - 10
    poly([(tx + 8, top + 16), (tx + tw - 4, top), (tx + tw, bot),
          (tx, bot)], (96, 128, 168))
    for r in range(9):
        for s in range(3):
            if (r * 3 + s) % 4 != 3:
                rect(tx + 9 + s * 14, top + 26 + r * ((bot - top - 30) // 9),
                     8, 6, GOLD)
    poly([(tx + tw - 4, top), (tx + tw + 12, top + 14), (tx + tw - 10, top + 20)],
         GREY)
    line(tx + tw - 2, top + 4, tx + tw + 14, top + 22, GREY, 3)
    line(tx + tw + 16, top + 26, tx + tw + 26, top + 40, GREY, 2)
    for i in range(3):
        circle(tx + tw + 16 + i * 8, top + 30 + i * 10, 5 + i * 2, (150, 150, 150))


def illo_climate(x, y, w, h):
    """Earth and a leaf for the COP31 talks."""
    rect(x, y, w, h, (214, 236, 214))
    cx = x + w // 2 - 18
    cy = y + h // 2
    r = min(w, h) // 2 - 14
    circle(cx, cy, r, WATER)
    circle(cx - r // 3, cy - r // 4, r // 3, GREEN)
    circle(cx + r // 4, cy + r // 5, r // 4, GREEN)
    circle(cx + r // 6, cy - r // 2, r // 6, GREEN)
    lx = cx + r - 2
    ly = cy - r + 8
    poly([(lx, ly + 34), (lx + 12, ly + 6), (lx + 34, ly), (lx + 30, ly + 26),
          (lx + 16, ly + 36)], GREEN)
    line(lx + 4, ly + 32, lx + 30, ly + 4, (214, 236, 214), 2)


def illo_vangogh(x, y, w, h):
    """A swirly night sky in a gilt frame - the record Van Gogh."""
    rect(x, y, w, h, GOLD)
    ix, iy, iw, ih = x + 8, y + 8, w - 16, h - 16
    rect(ix, iy, iw, ih, NIGHT)
    for ring in range(3):
        rr = 10 + ring * 9
        for a_deg in range(0, 360, 6):
            a = math.radians(a_deg)
            sx = int(ix + iw // 3 + rr * math.cos(a))
            sy = int(iy + ih // 3 + rr * 0.62 * math.sin(a))
            px(sx, sy, SKYBLUE)
            px(sx + 1, sy, SKYBLUE)
    circle(ix + iw // 3, iy + ih // 3, 6, (250, 230, 120))
    circle(ix + iw - 30, iy + 22, 7, (250, 230, 120))
    circle(ix + iw - 58, iy + 40, 4, WHITE)
    for i in range(5):
        bx = ix + 12 + i * (iw // 5)
        by = iy + ih - 16 - (i % 2) * 8
        circle(bx, by, 6, (244, 194, 214))
        circle(bx + 5, by - 4, 4, WHITE)
    rect(ix, iy + ih - 8, iw, 8, (16, 60, 30))


def panel(x, y, w, h):
    rect_outline(x, y, w, h, INK, 2)


def story(x, y, w, kicker, headline, body, head_scale=3, body_scale=2):
    draw_text(x, y, kicker, 2, RED)
    yy = y + 24
    for ln in wrap(headline, head_scale, w):
        draw_text(x, yy, ln, head_scale, INK)
        yy += head_scale * 7 + 7
    yy += 2
    draw_block(x, yy, body, body_scale, (52, 48, 40), w, body_scale * 7 + 6)


# ------------------------------------------------------------------ page

def build_page():
    rect(0, 0, W, H, PAPER)

    # Masthead
    draw_text_center(22, "THE DAILY WORLD", 10, INK)
    rect(26, 102, W - 52, 3, INK)
    draw_text_center(110, "ALL THE WORLD'S NEWS OF ONE DAY, ON ONE PAGE", 2, GREY)
    rect(26, 130, W - 52, 1, INK)

    # Date band - the day, unmissable
    rect(26, 140, W - 52, 52, RED)
    draw_text_center(149, "THURSDAY, 19 NOVEMBER 2026", 5, WHITE)
    draw_text_center(200, "THE DAY IN FULL: EVERY STORY BELOW BROKE ON THIS DAY",
                     2, DARKRED)

    # Lead story: the Shenzhen trilateral summit
    ly = 224
    panel(26, ly, W - 52, 196)
    draw_text(46, ly + 16, "DIPLOMACY - SHENZHEN, CHINA", 2, RED)
    draw_text(46, ly + 42, "TRUMP, XI AND PUTIN", 5, INK)
    draw_text(46, ly + 88, "MEET IN SHENZHEN", 5, INK)
    draw_block(46, ly + 134,
               "The US, Chinese and Russian leaders held a first-ever "
               "trilateral summit at APEC and announced a \"peace "
               "declaration\".",
               2, (52, 48, 40), 556, 19)
    illo_summit(620, ly + 16, 356, 164)

    # Row two: the world court and the Crimean Bridge
    ry = 436
    panel(26, ry, 478, 216)
    illo_court(352, ry + 14, 138, 96)
    draw_text(44, ry + 16, "THE HAGUE - WORLD COURT", 2, RED)
    yy = ry + 42
    for ln in wrap("WORLD COURT RULES MYANMAR COMMITTED GENOCIDE", 3, 312):
        draw_text(44, yy, ln, 3, INK)
        yy += 28
    draw_block(44, ry + 128,
               "The UN's International Court of Justice ruled "
               "Myanmar's campaign against the Rohingya was "
               "state-sponsored genocide - a first for the UN's "
               "highest court.",
               2, (52, 48, 40), 442, 17)
    panel(520, ry, 478, 216)
    illo_bridge(846, ry + 14, 138, 96)
    draw_text(538, ry + 16, "UKRAINE WAR - KERCH STRAIT", 2, RED)
    yy = ry + 42
    for ln in wrap("UKRAINE HITS CRIMEAN BRIDGE A THIRD TIME", 3, 312):
        draw_text(538, yy, ln, 3, INK)
        yy += 28
    draw_block(538, ry + 128,
               "Russia said Ukraine struck the Crimean Bridge for "
               "the third time this week; a road span collapsed "
               "and traffic was suspended.",
               2, (52, 48, 40), 442, 17)

    # Row three: Gaza, Riyadh, COP31. Headlines are split by hand so
    # the first two lines stay clear of the illustration at top right.
    ty = 664
    pw = 312
    panel(26, ty, pw, 216)
    illo_tank(210, ty + 10, 102, 72)
    draw_text(42, ty + 12, "GAZA", 2, RED)
    yy = ty + 36
    for ln in ("ISRAELI", "TANKS PUSH", "INTO CENTRAL", "GAZA"):
        draw_text(42, yy, ln, 3, INK)
        yy += 26
    draw_block(42, ty + 144,
               "A rare ground operation near Nuseirat, past the "
               "ceasefire line; Hamas protests.",
               2, (52, 48, 40), 280, 17)
    panel(356, ty, pw, 216)
    illo_tower(542, ty + 10, 110, 72)
    draw_text(372, ty + 12, "SAUDI ARABIA", 2, RED)
    yy = ty + 36
    for ln in ("MISSILE", "DEBRIS", "DAMAGES RIYADH", "LANDMARK"):
        draw_text(372, yy, ln, 3, INK)
        yy += 26
    draw_block(372, ty + 144,
               "Debris from a Houthi missile damaged the PIF "
               "tower in the Saudi capital.",
               2, (52, 48, 40), 280, 17)
    panel(686, ty, pw, 216)
    illo_climate(870, ty + 10, 102, 72)
    draw_text(702, ty + 12, "COP31 TALKS", 2, RED)
    yy = ty + 36
    for ln in ("MINISTERS", "RACE TO", "UNBLOCK CLIMATE", "TALKS"):
        draw_text(702, yy, ln, 3, INK)
        yy += 26
    draw_block(702, ty + 144,
               "Ministers in Antalya worked through the night to "
               "save the summit's final text.",
               2, (52, 48, 40), 280, 17)

    # Row four: the Van Gogh record and the day in brief
    by = 892
    panel(26, by, 478, 88)
    illo_vangogh(44, by + 12, 118, 64)
    draw_text(178, by + 10, "ART MARKET - NEW YORK", 2, RED)
    draw_text(178, by + 30, "VAN GOGH SELLS FOR", 3, INK)
    draw_text(178, by + 54, "A RECORD $190.4M", 3, INK)
    panel(520, by, 478, 88)
    draw_text(538, by + 8, "ALSO TODAY - 19 NOVEMBER", 2, RED)
    briefs = [
        "SOMALIA EXPELS UAE AMBASSADOR",
        "DOZENS MISSING OFF SENEGAL COAST",
        "BANGLADESH: YUNUS HOME SET ABLAZE",
        "N. KOREA UNVEILS FIRST AI CHATBOT",
    ]
    yy = by + 28
    for b in briefs:
        rect(538, yy + 3, 8, 8, RED)
        draw_text(554, yy, b, 2, INK)
        yy += 15

    # Footer
    rect(26, 984, W - 52, 2, INK)
    draw_text_center(990, "DRAWN BY A PROGRAM - THURSDAY 19 NOVEMBER 2026, "
                          "THE WHOLE DAY ON ONE PAGE", 2, GREY)


def main():
    build_page()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png_bytes())
    print("wrote", path)


if __name__ == "__main__":
    main()
