"""Procedural N64-style textures for the campus stages (RGBA16-friendly: 5 bits per channel,
1-bit alpha; 32x32 or 64x32 so each fits the 4 KB TMEM).

Usage: tools/.venv/bin/python -I tools/campus/make_textures.py [--out DIR] [--sheet PNG]
Writes art/levels/textures/<name>.png for every material in stage_palette.MATERIALS
(deterministic: same files every run) and optionally a contact sheet.

Scale conventions (match stage_palette tile_m):
  brick textures: 2 m per 32 px  -> bricks 0.5 m x 0.25 m (8 x 4 px; chunky, readable)
  facade bays:    4 m x 4 m per 32 px (one window bay x one floor; bricks 4 x 2 px = same size)
  ground:         4 m per 32 px (grass, asphalt), sidewalks 3 m
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from stage_palette import MATERIALS, TEXTURE_DIR  # noqa: E402


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def q5(c):
    """8-bit -> RGBA16 5-bit -> 8-bit (what the game will show)."""
    v = max(0, min(255, int(round(c))))
    v5 = (v * 31 + 127) // 255
    return (v5 << 3) | (v5 >> 2)


def shade(c, k):
    return tuple(max(0, min(255, int(round(x * k)))) for x in c)


def mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class Tex:
    def __init__(self, w, h, color, seed):
        self.w, self.h = w, h
        self.r = random.Random(seed)
        self.px = [[tuple(color) + (255,) for _ in range(w)] for _ in range(h)]

    def set(self, x, y, c, a=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = tuple(int(v) for v in c[:3]) + (a,)

    def get(self, x, y):
        return self.px[y % self.h][x % self.w]

    def rect(self, x0, y0, x1, y1, c, a=255):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, c, a)

    def noise(self, amp, mono=True, x0=0, y0=0, x1=None, y1=None):
        x1 = self.w - 1 if x1 is None else x1
        y1 = self.h - 1 if y1 is None else y1
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                r, g, b, a = self.px[y][x]
                if mono:
                    d = self.r.uniform(-amp, amp)
                    self.px[y][x] = (r + d, g + d, b + d, a)
                else:
                    self.px[y][x] = (r + self.r.uniform(-amp, amp), g + self.r.uniform(-amp, amp),
                                     b + self.r.uniform(-amp, amp), a)

    def speckle(self, n, colors):
        for _ in range(n):
            self.set(self.r.randrange(self.w), self.r.randrange(self.h), self.r.choice(colors))

    def image(self):
        im = Image.new("RGBA", (self.w, self.h))
        im.putdata([tuple(q5(c) for c in p[:3]) + (255 if p[3] >= 128 else 0,) for row in self.px for p in row])
        return im


# ------------------------------------------------------------------ building blocks
def brick_field(t, base, mortar, bw, bh, x0=0, y0=0, x1=None, y1=None, var=0.10, offset=None):
    """Running-bond brick: bricks bw x bh px including one mortar pixel each way."""
    x1 = t.w - 1 if x1 is None else x1
    y1 = t.h - 1 if y1 is None else y1
    offset = bw // 2 if offset is None else offset
    tones = {}
    for y in range(y0, y1 + 1):
        course = y // bh
        for x in range(x0, x1 + 1):
            xs = x + (offset if course % 2 else 0)
            if y % bh == bh - 1 or xs % bw == bw - 1:
                c = mortar
            else:
                key = (course, xs // bw)
                if key not in tones:
                    tones[key] = 1.0 + t.r.uniform(-var, var)
                c = shade(base, tones[key])
            t.set(x, y, c)


def window_pane(t, x0, y0, x1, y1, glass, frame, reflect=True, mullion_x=None, transom_y=None):
    t.rect(x0, y0, x1, y1, frame)
    for y in range(y0 + 1, y1):
        for x in range(x0 + 1, x1):
            k = 1.0
            if reflect:
                # diagonal sky reflection streak
                d = (x - x0) - (y - y0) * 0.6
                if 2 <= d % 9 <= 3:
                    k = 1.35
                k *= 1.0 + 0.25 * (1 - (y - y0) / max(1, y1 - y0))
            t.set(x, y, shade(glass, k))
    if mullion_x is not None:
        for y in range(y0, y1 + 1):
            t.set(mullion_x, y, frame)
    if transom_y is not None:
        for x in range(x0, x1 + 1):
            t.set(x, transom_y, frame)


# ------------------------------------------------------------------ textures
BRICK = hexc("#A9533A")
BRICK_DARK = hexc("#7A3828")
MORTAR = hexc("#C9B79C")
LIME = hexc("#D6C8A4")
GLASS = hexc("#2E4254")


def tx_brick(base, mortar, seed):
    t = Tex(32, 32, base, seed)
    brick_field(t, base, mortar, 8, 4)
    t.noise(7)
    return t


def tx_limestone(seed):
    t = Tex(32, 32, LIME, seed)
    joint = shade(LIME, 0.82)
    for y in range(32):
        for x in range(32):
            xs = x + (8 if (y // 8) % 2 else 0)
            if y % 8 == 7 or xs % 16 == 15:
                t.set(x, y, joint)
    t.noise(6)
    t.speckle(18, [shade(LIME, 0.9), shade(LIME, 1.06)])
    return t


def tx_roof_tile(base, seed):
    t = Tex(32, 32, base, seed)
    for y in range(32):
        for x in range(32):
            col = x % 4
            k = (0.78, 1.0, 1.12, 0.92)[col]
            row = y % 8
            if row == 0:
                k *= 0.62          # course shadow under the tile above
            elif row == 1:
                k *= 0.85
            t.set(x, y, shade(base, k * (1 + 0.05 * math.sin((x // 4) * 1.7 + (y // 8) * 2.3))))
    t.noise(6)
    return t


def tx_roof_dark(seed):
    base = hexc("#4C4C52")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        for x in range(32):
            xs = x + (4 if (y // 4) % 2 else 0)
            if y % 4 == 3 or xs % 8 == 7:
                t.set(x, y, shade(base, 0.7))
    t.noise(8)
    return t


def tx_noise(color, seed, amp=9, speck=None, n=40):
    t = Tex(32, 32, hexc(color), seed)
    t.noise(amp)
    if speck:
        t.speckle(n, [hexc(c) for c in speck])
    return t


def tx_copper(seed):
    base = hexc("#5E9C88")
    t = Tex(32, 32, base, seed)
    for x in range(32):
        k = 1 + 0.12 * math.sin(x * 0.9) + t.r.uniform(-0.05, 0.05)
        for y in range(32):
            t.set(x, y, shade(base, k))
    t.noise(8)
    t.speckle(30, [hexc("#7FB8A0"), hexc("#3E7262"), hexc("#8A6A3A")])
    return t


def tx_window_dark(seed):
    t = Tex(32, 32, hexc("#3C3E42"), seed)
    for py in (0, 16):
        for px in (0, 8, 16, 24):
            window_pane(t, px, py, px + 7, py + 15, GLASS, hexc("#56585C"), reflect=True)
    return t


def tx_window_glass(seed):
    t = Tex(32, 32, hexc("#6E94B4"), seed)
    for y in range(32):
        for x in range(32):
            k = 0.85 + 0.35 * (1 - y / 31)
            if 3 <= (x - y * 0.5) % 12 <= 5:
                k *= 1.18
            t.set(x, y, shade(hexc("#5A84A8"), k))
    for x in (0, 16):
        for y in range(32):
            t.set(x, y, hexc("#3E464E"))
    for y in (0,):
        for x in range(32):
            t.set(x, y, hexc("#3E464E"))
    return t


def tx_door_wood(seed):
    base = hexc("#6B4226")
    t = Tex(32, 32, base, seed)
    for x in range(32):
        k = 1 + (0.18 if x % 8 == 0 else 0) * -1 + t.r.uniform(-0.04, 0.04)
        for y in range(32):
            t.set(x, y, shade(base, k + 0.05 * math.sin(y * 0.7 + x)))
    t.noise(6)
    return t


def tx_metal(seed):
    base = hexc("#8A8E92")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        k = 1 + t.r.uniform(-0.06, 0.06)
        for x in range(32):
            t.set(x, y, shade(base, k))
    t.noise(4)
    return t


def tx_plaza_brick(seed):
    a, b = hexc("#A65A42"), hexc("#8E4A36")
    sand = hexc("#C4A882")
    t = Tex(32, 32, a, seed)
    # basket weave: 8x8 blocks of two 8x4 pavers, orientation alternating
    for by in range(4):
        for bx in range(4):
            horiz = (bx + by) % 2 == 0
            for y in range(8):
                for x in range(8):
                    X, Y = bx * 8 + x, by * 8 + y
                    if horiz:
                        edge = y in (3, 7) or x == 7
                        tone = a if y < 4 else b
                    else:
                        edge = x in (3, 7) or y == 7
                        tone = b if x < 4 else a
                    t.set(X, Y, sand if edge else shade(tone, 1 + t.r.uniform(-0.05, 0.05)))
    t.noise(5)
    return t


def tx_grass(color, seed, blades=("#7CB858", "#4A7A30")):
    base = hexc(color)
    t = Tex(32, 32, base, seed)
    t.noise(10, mono=False)
    for _ in range(70):
        x, y = t.r.randrange(32), t.r.randrange(32)
        c = hexc(t.r.choice(blades))
        t.set(x, y, c)
        t.set(x, y - 1, mix(c, base, 0.5))
    return t


def tx_sidewalk(seed):
    base = hexc("#C8C2B4")
    t = Tex(32, 32, base, seed)
    t.noise(6)
    joint = shade(base, 0.8)
    for i in range(32):
        t.set(i, 0, joint)
        t.set(0, i, joint)
        t.set(i, 16, shade(base, 0.88))
        t.set(16, i, shade(base, 0.88))
    t.speckle(25, [shade(base, 0.9), shade(base, 1.06)])
    return t


def tx_steps(seed):
    base = hexc("#B4AEA2")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        k = 1.0 if y % 16 > 3 else 0.7
        for x in range(32):
            t.set(x, y, shade(base, k))
    t.noise(5)
    return t


def tx_asphalt(color, seed):
    t = Tex(32, 32, hexc(color), seed)
    t.noise(7)
    t.speckle(60, [shade(hexc(color), 1.25), shade(hexc(color), 0.8)])
    return t


def tx_crosswalk(seed):
    t = Tex(32, 32, hexc("#4C4C50"), seed)
    for y in range(32):
        white = (y % 16) < 9
        for x in range(32):
            t.set(x, y, hexc("#E6E4DC") if white else hexc("#4C4C50"))
    t.noise(7)
    return t


def tx_water(seed):
    base = hexc("#3A72A8")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        for x in range(32):
            k = 1 + 0.12 * math.sin((x + 2 * math.sin(y * 0.4)) * 0.8) * math.sin(y * 0.35 + 1)
            t.set(x, y, shade(base, k))
    for _ in range(14):
        x, y = t.r.randrange(32), t.r.randrange(32)
        for d in range(t.r.randrange(2, 5)):
            t.set(x + d, y, shade(base, 1.45))
    return t


def tx_facade(kind, seed):
    """One window bay x one floor (4 m x 4 m). Row 0 = top of the floor (ceiling line)."""
    base = BRICK if kind != "glass" else hexc("#5E8098")
    t = Tex(32, 32, base, seed)
    if kind in ("gothic", "brick", "service", "band"):
        # small bricks (4 x 2 px = 0.5 x 0.25 m) need a dark, warm mortar or the wall turns pink
        fb = hexc("#A8492E") if kind != "band" else hexc("#9A4C38")
        brick_field(t, fb, hexc("#86523E"), 4, 2, var=0.14)
        t.noise(5)
    if kind == "gothic":
        # two lancet windows with limestone surrounds, sill and label mould
        for wx in (8, 18):
            x0, x1, y0, y1 = wx, wx + 5, 5, 25
            t.rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1, LIME)
            window_pane(t, x0, y0 + 2, x1, y1, GLASS, hexc("#4A4E50"), mullion_x=x0 + 3, transom_y=14)
            # pointed arch
            t.rect(x0, y0, x1, y0 + 1, LIME)
            t.set(x0 + 2, y0 + 1, shade(GLASS, 1.2))
            t.set(x0 + 3, y0 + 1, shade(GLASS, 1.2))
            t.set(x0 + 2, y0, LIME)
            t.set(x0 + 3, y0, LIME)
            t.rect(x0 - 2, y1 + 2, x1 + 2, y1 + 2, shade(LIME, 0.9))  # sill
        t.rect(0, 30, 31, 30, shade(LIME, 0.95))  # floor string course
    elif kind == "brick":
        t.rect(9, 6, 22, 25, LIME)                 # surround / lintel
        window_pane(t, 10, 7, 21, 24, GLASS, hexc("#D8D4CC"), mullion_x=15, transom_y=12)
        t.rect(8, 26, 23, 26, shade(LIME, 0.9))    # sill
    elif kind == "band":
        window_pane(t, 0, 8, 31, 22, GLASS, hexc("#3E3C3A"), mullion_x=None)
        for x in (0, 8, 16, 24):
            for y in range(8, 23):
                t.set(x, y, hexc("#3E3C3A"))
        t.rect(0, 23, 31, 24, hexc("#B8B2A6"))   # concrete sill band
        t.rect(0, 30, 31, 31, hexc("#B8B2A6"))   # exposed floor slab
        t.noise(3)
    elif kind == "glass":
        for y in range(32):
            for x in range(32):
                k = 0.8 + 0.45 * (1 - y / 31)
                if 4 <= (x - y * 0.55) % 14 <= 6:
                    k *= 1.2
                t.set(x, y, shade(hexc("#5A8AA8"), k))
        for y in range(27, 32):
            for x in range(32):
                t.set(x, y, hexc("#4A5056"))
        for y in range(32):
            t.set(0, y, hexc("#2E3236"))
            t.set(16, y, hexc("#2E3236"))
        for x in range(32):
            t.set(x, 13, hexc("#2E3236"))
    elif kind == "service":
        t.rect(11, 4, 20, 10, hexc("#6E6A64"))
        for y in range(5, 10, 2):
            t.rect(12, y, 19, y, hexc("#4A4642"))
    return t


def tx_roof_gravel(seed):
    base = hexc("#7C7A76")
    t = Tex(32, 32, base, seed)
    t.noise(12)
    t.speckle(80, [hexc("#9A9690"), hexc("#5E5C58"), hexc("#8A8274")])
    return t


def tx_door_marker(seed):
    t = Tex(32, 32, hexc("#FA4616"), seed)
    for y in range(32):
        for x in range(32):
            if x < 3 or x > 28 or y < 3:
                t.set(x, y, hexc("#0021A5"))
    t.noise(4)
    return t


def tx_leaves(base_hex, light_hex, dark_hex, seed, blobs=26):
    base, light, dark = hexc(base_hex), hexc(light_hex), hexc(dark_hex)
    t = Tex(32, 32, base, seed)
    t.noise(8, mono=False)
    for _ in range(blobs):
        cx, cy, r = t.r.randrange(32), t.r.randrange(32), t.r.uniform(1.5, 3.5)
        c = light if t.r.random() < 0.55 else dark
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    t.set(x % 32, y % 32, shade(c, 1 + t.r.uniform(-0.06, 0.06)))
    return t


def tx_bark(base_hex, seed, rings=False):
    base = hexc(base_hex)
    t = Tex(32, 32, base, seed)
    for x in range(32):
        k = 1 + 0.15 * math.sin(x * 1.3) + t.r.uniform(-0.08, 0.08)
        for y in range(32):
            kk = k * (0.8 if rings and y % 6 == 0 else 1.0)
            t.set(x, y, shade(base, kk))
    t.noise(6)
    return t


def tx_palm_frond(seed):
    base = hexc("#5A9440")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        for x in range(32):
            k = 1.0 + (0.25 if (x + y // 2) % 4 == 0 else 0) - (0.2 if x == 16 else 0)
            t.set(x, y, shade(base, k))
    t.noise(6)
    return t


def tx_treeline(seed):
    """64 x 32 cut-out band of tree crowns (row 0 = top). Alpha 0 above the crowns."""
    t = Tex(64, 32, hexc("#3A5E32"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, (0, 0, 0), 0)
    crowns = [(4, 14, 6), (13, 10, 7), (23, 15, 6), (32, 8, 8), (42, 13, 6), (51, 9, 7), (60, 15, 6)]
    for cx, cy, r in crowns:
        for y in range(32):
            for x in range(64):
                dx = min(abs(x - cx), 64 - abs(x - cx))
                if dx * dx + (y - cy) ** 2 * 1.3 <= r * r or (y >= cy and dx <= r):
                    k = 1.0 + 0.25 * (1 - y / 31) + t.r.uniform(-0.08, 0.08)
                    t.set(x, y, shade(hexc("#3A5E32"), k))
    for _ in range(60):
        x, y = t.r.randrange(64), t.r.randrange(32)
        if t.px[y][x][3]:
            t.set(x, y, hexc("#5A8442") if t.r.random() < 0.5 else hexc("#28401F"))
    return t


def tx_rock(seed):
    """Pale weathered stone (the Turlington rock 'The Potato' is a cream / light grey boulder)."""
    base = hexc("#C2B79F")
    t = Tex(32, 32, base, seed)
    t.noise(12)
    t.speckle(90, [hexc("#D6CDB8"), hexc("#A39880"), hexc("#CFC6B2")])
    for _ in range(4):
        x, y = t.r.randrange(32), t.r.randrange(32)
        for _ in range(10):
            t.set(x, y, hexc("#8E846E"))
            x += t.r.choice((-1, 0, 1))
            y += 1
    return t


def tx_bronze(seed):
    """Dark statue bronze with worn highlights."""
    base = hexc("#5E4630")
    t = Tex(32, 32, base, seed)
    t.noise(8)
    t.speckle(70, [hexc("#8A6A44"), hexc("#3A2A1C"), hexc("#74583A")])
    return t


# 6 x 10 bold glyphs for the name signs
GLYPHS = {
    "T": ["######", "######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
    "H": ["##..##", "##..##", "##..##", "##..##", "######", "######", "##..##", "##..##", "##..##", "##..##"],
    "E": ["######", "######", "##....", "##....", "#####.", "#####.", "##....", "##....", "######", "######"],
    "U": ["##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "######", ".####."],
    "B": ["#####.", "######", "##..##", "##..##", "#####.", "#####.", "##..##", "##..##", "######", "#####."],
}


def tx_name_sign(text, seed):
    """64 x 32 building name sign: white bold letters on UF blue, orange rule underneath."""
    blue, orange, white = hexc("#0021A5"), hexc("#FA4616"), hexc("#F4F2EC")
    t = Tex(64, 32, blue, seed)
    t.noise(3)
    width = sum(6 if ch != " " else 4 for ch in text) + (len(text) - 1)
    x = (64 - width) // 2
    y0 = 9
    for ch in text:
        if ch == " ":
            x += 5
            continue
        for gy, row in enumerate(GLYPHS[ch]):
            for gx, c in enumerate(row):
                if c == "#":
                    t.set(x + gx, y0 + gy, white)
        x += 7
    t.rect(6, 23, 57, 24, orange)
    for i in range(64):               # thin white frame
        t.set(i, 1, white)
        t.set(i, 30, white)
    for j in range(1, 31):
        t.set(1, j, white)
        t.set(62, j, white)
    return t


def tx_banner(main_hex, stripe_hex, seed):
    """Lamp-post banner (one repeat = the banner): solid colour, stripe near the bottom, darker hem."""
    main, stripe = hexc(main_hex), hexc(stripe_hex)
    t = Tex(32, 32, main, seed)
    t.noise(4)
    t.rect(0, 22, 31, 25, stripe)
    t.rect(0, 0, 31, 1, shade(main, 0.75))
    t.rect(0, 30, 31, 31, shade(main, 0.75))
    return t


def build_all():
    T = {
        "brick_red": tx_brick(BRICK, MORTAR, 11),
        "brick_dark": tx_brick(BRICK_DARK, hexc("#A89880"), 12),
        "limestone": tx_limestone(13),
        "roof_tile_red": tx_roof_tile(hexc("#B0532F"), 14),
        "roof_dark": tx_roof_dark(15),
        "copper_green": tx_copper(16),
        "window_dark": tx_window_dark(17),
        "window_glass": tx_window_glass(18),
        "door_wood": tx_door_wood(19),
        "concrete": tx_noise("#B8B4AA", 20, 7, ["#A8A49A", "#C8C4BA"]),
        "metal_gray": tx_metal(21),
        "plaza_brick": tx_plaza_brick(22),
        "grass": tx_grass("#5F9A3F", 23),
        "path": tx_sidewalk(24),
        "water": tx_water(25),
        "dark_trim": tx_noise("#3A3430", 26, 5),
        "white_trim": tx_noise("#E6E2D8", 27, 4),
        "rock": tx_rock(28),
        "bronze": tx_bronze(29),
        "sign_the_hub": tx_name_sign("THE HUB", 30),
        "banner_orange": tx_banner("#FA4616", "#0021A5", 58),
        "banner_blue": tx_banner("#0021A5", "#FA4616", 59),
        "ground_grass": tx_grass("#5A8C3C", 31, blades=("#6E9E48", "#4A7430")),
        "lawn": tx_grass("#6AA346", 32, blades=("#86C060", "#56883A")),
        "forest_floor": tx_noise("#4E6E34", 33, 12, ["#6A5434", "#3E5A2A", "#5E7E3E"], 120),
        "mulch": tx_noise("#6E4A30", 34, 14, ["#8A6040", "#4E3220", "#7A5038"], 150),
        "asphalt": tx_asphalt("#4C4C50", 35),
        "parking": tx_asphalt("#5A5A5E", 36),
        "road_paint": tx_noise("#E2BE3C", 37, 6),
        "crosswalk": tx_crosswalk(38),
        "sidewalk": tx_sidewalk(39),
        "steps": tx_steps(40),
        "pond_bed": tx_noise("#3E4A30", 41, 10, ["#2E3822", "#56603E"], 80),
        "pond_water": tx_water(42),
        "facade_gothic": tx_facade("gothic", 43),
        "facade_brick": tx_facade("brick", 44),
        "facade_band": tx_facade("band", 45),
        "facade_glass": tx_facade("glass", 46),
        "facade_service": tx_facade("service", 47),
        "roof_gravel": tx_roof_gravel(48),
        "door_marker": tx_door_marker(49),
        "leaves_oak": tx_leaves("#3E6E2E", "#5E9440", "#2A4C20", 50),
        "leaves_oak2": tx_leaves("#46682C", "#6A8C3E", "#2E4A1E", 57),
        "leaves_pine": tx_leaves("#365C3A", "#4E7A4C", "#22402A", 51, blobs=34),
        "palm_frond": tx_palm_frond(52),
        "bark": tx_bark("#5A4632", 53),
        "palm_trunk": tx_bark("#8A7A62", 54, rings=True),
        "treeline": tx_treeline(55),
        "forest_wall": tx_leaves("#33502C", "#3E6234", "#24381E", 56, blobs=30),
    }
    missing = set(MATERIALS) - set(T)
    if missing:
        raise SystemExit(f"no texture recipe for {sorted(missing)}")
    return T


def main():
    out = TEXTURE_DIR
    sheet = None
    argv = sys.argv[1:]
    if "--out" in argv:
        out = os.path.abspath(argv[argv.index("--out") + 1])
    if "--sheet" in argv:
        sheet = os.path.abspath(argv[argv.index("--sheet") + 1])
    os.makedirs(out, exist_ok=True)
    T = build_all()
    imgs = {}
    for name, m in MATERIALS.items():
        im = T[name].image()
        w, h = im.size
        if (w, h) not in ((32, 32), (64, 32)):
            raise SystemExit(f"{name}: {w}x{h} is not 32x32 / 64x32")
        im.save(os.path.join(out, m["tex"]))
        imgs[name] = im
    print(f"make_textures: wrote {len(imgs)} textures to {out}")
    if sheet:
        cols, cell = 8, 136
        rows = (len(imgs) + cols - 1) // cols
        sh = Image.new("RGB", (cols * cell, rows * (cell + 14)), (40, 40, 40))
        d = ImageDraw.Draw(sh)
        for i, (name, im) in enumerate(imgs.items()):
            r, c = divmod(i, cols)
            tile = Image.new("RGBA", (im.width * 2, im.height * 2))
            for yy in range(2):
                for xx in range(2):
                    tile.paste(im, (xx * im.width, yy * im.height))
            big = tile.resize((128, int(128 * tile.height / tile.width)), Image.NEAREST)
            bg = Image.new("RGB", big.size, (255, 0, 255))
            bg.paste(big, (0, 0), big)
            sh.paste(bg, (c * cell + 4, r * (cell + 14) + 4))
            d.text((c * cell + 4, r * (cell + 14) + 134), name, fill=(230, 230, 230))
        sh.save(sheet)
        print("make_textures: sheet", sheet)


if __name__ == "__main__":
    main()
