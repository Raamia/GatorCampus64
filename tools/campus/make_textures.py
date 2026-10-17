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
from stage_palette import INTERIOR_MATERIALS  # noqa: E402  (interior kit, written after the outdoor set)


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


# ================================================================== interior kit textures
# Recipes for stage_palette.INTERIOR_MATERIALS (the int_* materials of tools/campus/interior_kit.py:
# Marston, later Library West and the Century Tower interior). Kept apart from build_all() so the
# outdoor textures (and every outdoor stage build) are untouched; main() writes both sets.
# Scale: "tile" textures repeat every stage_palette tile_m metres; "once" textures (signs, screens,
# doors, the window view) are mapped whole onto one panel by the kit's builders. Row 0 = top (v = 1).

# 5 x 7 pixel font for the interior signs (the hub's GLYPHS above are 6 x 10 and only know THE HUB)
FONT5 = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    "^": ["..#..", ".###.", "#.#.#", "..#..", "..#..", "..#..", "..#.."],   # up arrow
    "v": ["..#..", "..#..", "..#..", "..#..", "#.#.#", ".###.", "..#.."],   # down arrow
}
UF_BLUE = hexc("#0021A5")
UF_ORANGE = hexc("#FA4616")
SIGN_WHITE = hexc("#F4F2EC")


def font_width(text, scale=1, spacing=1):
    n = len(text)
    return n * 5 * scale + max(0, n - 1) * spacing * scale if n else 0


def font_text(t, text, x, y, color, scale=1, spacing=1):
    """Draw text with FONT5 (5 x 7 px glyphs, `scale` x bigger); (x, y) = top-left. Space = a blank glyph."""
    for ch in text:
        g = FONT5.get(ch)
        if g is not None:
            for gy, row in enumerate(g):
                for gx, c in enumerate(row):
                    if c == "#":
                        t.rect(x + gx * scale, y + gy * scale, x + gx * scale + scale - 1, y + gy * scale + scale - 1,
                               color)
        x += (5 + spacing) * scale


def font_center(t, text, y, color, scale=1, spacing=1, x0=0, x1=None):
    x1 = t.w - 1 if x1 is None else x1
    w = font_width(text, scale, spacing)
    font_text(t, text, x0 + (x1 - x0 + 1 - w) // 2, y, color, scale, spacing)


def tx_int_carpet(base_hex, fleck, seed):
    """Carpet tiles, 0.5 m (8 px at 2 m / 32 px), laid quarter-turned (the pile stripes alternate)."""
    base = hexc(base_hex)
    t = Tex(32, 32, base, seed)
    for ty in range(4):
        for tx in range(4):
            vertical = (tx + ty) % 2 == 0
            kt = 1.0 + t.r.uniform(-0.035, 0.035)
            for y in range(8):
                for x in range(8):
                    stripe = (x if vertical else y) % 2
                    t.set(tx * 8 + x, ty * 8 + y, shade(base, kt * (1.05 if stripe else 0.95)))
    t.noise(5)
    t.speckle(24, [hexc(c) for c in fleck])
    return t


def tx_int_carpet_accent(seed):
    """Reading-room carpet: rust orange with a darker diamond lattice (16 px = 1 m cells)."""
    base, line = hexc("#B4532E"), hexc("#7E3620")
    t = Tex(32, 32, base, seed)
    t.noise(6)
    for y in range(32):
        for x in range(32):
            if abs((x % 16) - 8) + abs((y % 16) - 8) == 7:
                t.set(x, y, line)
    t.speckle(30, [hexc("#D8803E"), hexc("#3A4E7A")])
    return t


def tx_int_floor_tile(seed):
    """Vinyl composition tile: 0.3 m (12") tiles = 8 px at 1.2 m / 32 px, cream / grey with a few accents."""
    cream, grey, accent = hexc("#D8D0BC"), hexc("#B8B4AA"), hexc("#9AA6B2")
    t = Tex(32, 32, cream, seed)
    for ty in range(4):
        for tx in range(4):
            tone = cream if (tx + ty) % 2 == 0 else grey
            if t.r.random() < 0.12:
                tone = accent
            kt = 1.0 + t.r.uniform(-0.03, 0.03)
            for y in range(8):
                for x in range(8):
                    c = shade(tone, kt)
                    if x == 0 or y == 0:
                        c = shade(tone, 0.82)       # joint
                    t.set(tx * 8 + x, ty * 8 + y, c)
            for _ in range(5):                      # VCT chips
                t.set(tx * 8 + t.r.randrange(1, 8), ty * 8 + t.r.randrange(1, 8),
                      shade(tone, t.r.choice((0.86, 1.1))))
    t.noise(3)
    return t


def tx_int_paint(base_hex, seed, amp=3, speck=6):
    base = hexc(base_hex)
    t = Tex(32, 32, base, seed)
    t.noise(amp)
    t.speckle(speck, [shade(base, 0.94), shade(base, 1.04)])
    return t


def tx_int_ceiling(seed):
    """Acoustic lay-in ceiling: 0.6 m (2') tiles = 16 px at 1.2 m, white T-bar grid, pinholes and fissures."""
    base, tbar, shadow = hexc("#E2E0D8"), hexc("#F6F6F2"), hexc("#BEBCB4")
    t = Tex(32, 32, base, seed)
    t.noise(3)
    for _ in range(90):
        t.set(t.r.randrange(32), t.r.randrange(32), hexc("#B4B2AA"))
    for _ in range(10):
        x, y = t.r.randrange(32), t.r.randrange(32)
        for d in range(t.r.randrange(2, 4)):
            t.set(x + d, y + (d // 2), hexc("#C4C2BA"))
    for i in range(32):
        for k in (0, 16):
            t.set(i, k, tbar)
            t.set(k, i, tbar)
            t.set(i, k + 1, shadow)
            t.set(k + 1, i, shadow)
    return t


def tx_int_light(seed):
    """2' x 4' fluorescent troffer, mapped once: white frame, prismatic diffuser, two brighter lamp bands."""
    t = Tex(32, 32, hexc("#F2F2EC"), seed)
    for y in range(32):
        for x in range(32):
            c = hexc("#F2F2EC")
            if (x + y) % 2 == 0:
                c = hexc("#E6E6E0")
            if 8 <= x <= 11 or 20 <= x <= 23:
                c = hexc("#FFFFFF")
            if x < 2 or x > 29 or y < 2 or y > 29:
                c = hexc("#CFCFCA")
            t.set(x, y, c)
    return t


BOOK_WARM = ("#7A2A2A", "#2A3A6A", "#2E5A3A", "#B89A6A", "#2A2A2E", "#C8642E", "#2E6E72", "#8A8A8A",
             "#D8CCAA", "#A83A32", "#6A4A2E", "#3E62A8", "#5A3A6A", "#C8B048")
BOOK_JOURNAL = ("#2A3A6A", "#5A1E22", "#1E4A3A", "#3A3A3E", "#6A5A2E", "#2E5A7A", "#7A2E2E", "#3E5A2E")


def tx_int_books(palette, seed, runs=False):
    """Two shelf rows of book spines, 64 x 32 = one 2 m x 0.8 m repeat (the kit maps v to whole rows).
    Each 16 px row: a dark shelf back, books 9-13 px tall and 2-4 px wide (3-6 cm: chunky, readable),
    a steel shelf board at the bottom (rows 14-15). runs=True: bound journal runs (same colour + height)."""
    back, board, edge = hexc("#2A221C"), hexc("#C8C0AA"), hexc("#E2DCC8")
    t = Tex(64, 32, back, seed)
    pal = [hexc(c) for c in palette]
    for row in range(2):
        y0 = row * 16
        x = 0
        while x < 64:
            if runs:
                c = t.r.choice(pal)
                hb = t.r.randint(10, 13)
                n = t.r.randint(4, 9)
                label = t.r.randint(1, 3)
                spec = [(t.r.choice((2, 3)), hb, c, label) for _ in range(n)]
            else:
                spec = [(t.r.choice((2, 2, 3, 3, 3, 4)), t.r.randint(9, 13), t.r.choice(pal), t.r.randint(1, 4))]
            for w, hb, c, label in spec:
                if x >= 64:
                    break
                if 64 - x - w < 2:            # last book fills the row so the texture tiles
                    w = 64 - x
                if not runs and t.r.random() < 0.06:
                    x += min(w, 64 - x)        # a gap on the shelf
                    continue
                tone = 1.0 + t.r.uniform(-0.08, 0.08)
                top = y0 + 14 - hb
                for xx in range(x, min(64, x + w)):
                    for yy in range(top, y0 + 14):
                        k = tone * (0.72 if xx == x else 1.0)
                        t.set(xx, yy, shade(c, k))
                    if label and w >= 2:
                        t.set(xx, top + label, shade(c, 1.45))   # title band
                    if runs:
                        t.set(xx, y0 + 12, hexc("#C8A848"))     # gilt volume number
                x += w
        for xx in range(64):
            t.set(xx, y0 + 14, edge)
            t.set(xx, y0 + 15, board)
            t.set(xx, y0, shade(back, 0.7))
    t.noise(3)
    return t


def tx_int_steel(base_hex, seed):
    base = hexc(base_hex)
    t = Tex(32, 32, base, seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, shade(base, 1.0 + 0.04 * (1 - y / 31)))
    t.noise(4)
    return t


def tx_int_wood(base_hex, seed):
    """Wood grain running along u (table tops, counter fronts)."""
    base = hexc(base_hex)
    t = Tex(32, 32, base, seed)
    rowk = [1.0 + t.r.uniform(-0.05, 0.05) for _ in range(32)]
    for y in range(32):
        for x in range(32):
            k = rowk[y] * (1 + 0.07 * math.sin(y * 0.9 + math.sin(x * 0.2 + y * 0.1) * 1.6))
            t.set(x, y, shade(base, k))
    for _ in range(9):                          # darker grain streaks
        y, x = t.r.randrange(32), t.r.randrange(32)
        for d in range(t.r.randrange(5, 14)):
            t.set((x + d) % 32, y, shade(base, 0.8))
    t.noise(3)
    return t


def tx_int_glass(seed):
    """Glass partition (translucent material): pale cyan with diagonal reflection streaks."""
    base = hexc("#9CC4D8")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        for x in range(32):
            k = 0.92 + 0.12 * (1 - y / 31)
            d = (x + y * 0.7) % 16
            if 3 <= d <= 4 or d == 9:
                k *= 1.18
            t.set(x, y, shade(base, k))
    return t


def tx_int_rail_bars(seed):
    """Cut-out railing infill, 1 m x 1 m: balusters every 12.5 cm (4 px), a bottom rail and a cap."""
    metal = hexc("#4E5256")
    t = Tex(32, 32, metal, seed)
    for y in range(32):
        for x in range(32):
            if y <= 1 or y >= 29 or x % 4 == 1:
                t.set(x, y, shade(metal, 1.0 + (0.15 if y in (0, 29) else 0.0)))
            else:
                t.set(x, y, (0, 0, 0), 0)
    return t


def tx_int_brushed(base_hex, seed, vertical=False):
    base = hexc(base_hex)
    t = Tex(32, 32, base, seed)
    ks = [1.0 + t.r.uniform(-0.06, 0.06) for _ in range(32)]
    for y in range(32):
        for x in range(32):
            t.set(x, y, shade(base, ks[x] if vertical else ks[y]))
    t.noise(3)
    return t


def tx_int_fabric(base_hex, seed):
    base = hexc(base_hex)
    t = Tex(32, 32, base, seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, shade(base, 1.06 if (x + y) % 2 else 0.94))
    t.noise(5)
    return t


def tx_int_stone(seed):
    """Speckled quartz / terrazzo (counter tops, lobby floor)."""
    t = tx_noise("#B0AAA2", seed, 6)
    t.speckle(110, [hexc("#3A3836"), hexc("#E8E4DC"), hexc("#9A6A4A"), hexc("#7A7672")])
    return t


def tx_int_whiteboard(seed):
    """64 x 32 whiteboard, mapped once onto a 2:1 board: aluminium frame, tray, marker scribbles."""
    t = Tex(64, 32, hexc("#ECEEEC"), seed)
    t.noise(2)
    blue, red, black, green = hexc("#2A4AB8"), hexc("#C83A32"), hexc("#2A2A2E"), hexc("#2E8A4A")
    font_text(t, "E=MC", 4, 4, blue)
    font_text(t, "2", 28, 1, blue)                      # squared
    for k in range(3):                                   # handwriting lines
        y = 15 + k * 4
        n = t.r.randint(22, 34)
        for x in range(4, 4 + n):
            if t.r.random() < 0.85:
                t.set(x, y + int(round(math.sin(x * 1.3 + k) * 0.8)), black)
    cx, cy, r = 45, 9, 6                                 # red circle + arrow
    for a in range(48):
        ang = a / 48 * 2 * math.pi
        t.set(int(round(cx + r * math.cos(ang))), int(round(cy + r * math.sin(ang))), red)
    for x in range(52, 60):
        t.set(x, 9, red)
    t.set(58, 8, red)
    t.set(58, 10, red)
    for y in range(16, 27):                              # green graph
        t.set(44, y, green)
    for x in range(44, 60):
        t.set(x, 26, green)
    for x in range(45, 59):
        t.set(x, 26 - int((x - 45) ** 2 / 20.0), green)
    for x in range(64):
        t.set(x, 0, hexc("#9A9EA2"))
        t.set(x, 31, hexc("#9A9EA2"))
        t.set(x, 29, hexc("#B4B8BC"))
        t.set(x, 30, hexc("#8A8E92"))
    for y in range(32):
        t.set(0, y, hexc("#9A9EA2"))
        t.set(63, y, hexc("#9A9EA2"))
    return t


def tx_int_monitor(seed):
    """Monitor front, mapped once onto the screen box: bezel, UF-blue desktop, a window, taskbar."""
    t = Tex(32, 32, hexc("#1E1E22"), seed)
    for y in range(2, 27):
        for x in range(2, 30):
            t.set(x, y, mix(hexc("#2E62B8"), hexc("#1E4A9A"), (y - 2) / 25))
    t.rect(6, 6, 24, 20, hexc("#E8ECF0"))
    t.rect(6, 6, 24, 7, UF_ORANGE)
    for k, y in enumerate((10, 12, 14, 16, 18)):
        t.rect(8, y, 8 + t.r.randint(8, 15), y, hexc("#8A9098"))
    t.rect(2, 25, 29, 26, hexc("#14223E"))
    for x in (4, 7, 10):
        t.rect(x, 25, x + 1, 26, hexc("#E8C848") if x == 4 else hexc("#6A8AC8"))
    t.set(27, 29, hexc("#3AD05A"))                       # power LED
    return t


def tx_int_kiosk(seed):
    """Room-booking kiosk touch screen, mapped once: 'BOOK' header, a slot grid, a big orange button."""
    t = Tex(32, 32, hexc("#1E1E22"), seed)
    t.rect(2, 2, 29, 29, hexc("#E8F0F8"))
    t.rect(2, 2, 29, 10, UF_BLUE)
    font_center(t, "BOOK", 3, SIGN_WHITE, x0=2, x1=29)
    cols = [hexc("#3AA05A"), hexc("#C83A32"), hexc("#9AA0A8")]
    for r in range(3):
        for c in range(3):
            x0, y0 = 4 + c * 9, 12 + r * 4
            t.rect(x0, y0, x0 + 6, y0 + 2, cols[(r * 2 + c + seed) % 3])
    t.rect(8, 25, 23, 28, UF_ORANGE)
    return t


def tx_int_elevator(seed):
    """Brushed-steel elevator door pair, mapped once onto the opening (2 panels, centre seam)."""
    base = hexc("#A4AAAE")
    t = Tex(32, 32, base, seed)
    ks = [1.0 + t.r.uniform(-0.06, 0.06) for _ in range(32)]
    for y in range(32):
        for x in range(32):
            k = ks[x] * (1.12 if 6 <= (x * 0.5 + y) % 22 <= 9 else 1.0)
            t.set(x, y, shade(base, k))
    for y in range(32):
        t.set(15, y, hexc("#4A4E52"))
        t.set(16, y, hexc("#C4CACE"))
    t.rect(0, 0, 31, 0, hexc("#6A6E72"))
    t.rect(0, 31, 31, 31, hexc("#5A5E62"))
    return t


def tx_int_stair(seed):
    """Stair tread, mapped with v = 1 at the nosing: metal nosing edge, anti-slip grooves, rubber tread."""
    base = hexc("#8E8A84")
    t = Tex(32, 32, base, seed)
    t.noise(5)
    t.speckle(40, [hexc("#A8A49C"), hexc("#74706A")])
    for x in range(32):
        t.set(x, 0, hexc("#C8CCD0"))
        t.set(x, 1, hexc("#B0B4B8"))
        for y in (2, 4):
            t.set(x, y, hexc("#3A3C40"))
        t.set(x, 3, hexc("#5A5C60"))
    return t


def tx_int_window(seed):
    """Window view of the campus outside (64 x 32, mapped once per two-pane bay): sky and clouds,
    Century Tower, a red-brick hall, oak canopies, lawn and a walk; dark bronze head and mullion."""
    t = Tex(64, 32, hexc("#88AACC"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#6E9ED6"), hexc("#C2D8EC"), min(1.0, y / 14)))
    for cx, cy, rx, ry in ((14, 4, 6, 2), (44, 6, 8, 2), (56, 3, 4, 1)):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / max(ry, 1)) ** 2 <= 1.0:
                    t.set(x % 64, y, hexc("#F4F6F8"))
    brick = hexc("#A9533A")
    for y in range(11, 24):                               # red-brick hall
        for x in range(22, 54):
            c = shade(brick, 1.0 + t.r.uniform(-0.05, 0.05))
            if y >= 13 and (x - 22) % 4 in (1, 2) and (y - 13) % 4 in (1, 2):
                c = hexc("#2E4254")
            t.set(x, y, c)
    t.rect(21, 10, 54, 10, hexc("#D6C8A4"))
    for y in range(5, 24):                                # Century Tower
        for x in range(8, 12):
            t.set(x, y, shade(brick, 0.95 if x == 8 else 1.05))
    t.set(9, 9, hexc("#F4F2EC"))
    t.set(10, 9, hexc("#F4F2EC"))
    for y in range(1, 5):
        for x in range(8 + (4 - y) // 2, 12 - (4 - y) // 2):
            t.set(x, y, hexc("#5E9C88"))
    for cx, cy, r in ((4, 21, 5), (18, 20, 6), (30, 22, 5), (42, 21, 6), (54, 20, 5), (62, 22, 4)):
        for y in range(cy - r, 27):
            for x in range(cx - r - 1, cx + r + 2):
                if (x - cx) ** 2 + (y - cy) ** 2 * 1.4 <= r * r or y >= cy + 2:
                    k = 1.0 + 0.2 * (cy - y) / r + t.r.uniform(-0.1, 0.1)
                    t.set(x % 64, y, shade(hexc("#3E6E2E"), k))
    for y in range(27, 32):
        for x in range(64):
            t.set(x, y, shade(hexc("#6AA346"), 1.0 + t.r.uniform(-0.06, 0.06)))
    for x in range(64):
        t.set(x, 29, hexc("#C8C2B4"))
    frame = hexc("#3A3430")
    for y in range(32):
        t.set(0, y, frame)
        t.set(32, y, frame)
    for x in range(64):
        t.set(x, 0, frame)
    return t


def tx_int_posters(seed):
    """Two posters side by side (64 x 32; the kit maps the left or right half): a DNA science poster
    and an orange READ poster."""
    t = Tex(64, 32, hexc("#1C2A4A"), seed)
    for y in range(32):                                   # DNA (left)
        for x in range(32):
            t.set(x, y, hexc("#1C2A4A"))
    for y in range(3, 23):
        a = math.sin(y * 0.55) * 7
        x1, x2 = int(round(16 + a)), int(round(16 - a))
        if y % 3 == 0:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                t.set(x, y, hexc("#9AA6B8"))
        t.set(x1, y, UF_ORANGE)
        t.set(x2, y, hexc("#4AC8E0"))
    font_center(t, "DNA", 24, SIGN_WHITE, x0=0, x1=31)
    t.rect(32, 0, 63, 31, UF_ORANGE)                       # READ (right)
    t.rect(38, 4, 57, 14, SIGN_WHITE)
    for y in range(4, 15):
        t.set(47, y, UF_BLUE)
        t.set(48, y, UF_BLUE)
    for y in (7, 9, 11):
        t.rect(40, y, 45, y, hexc("#9A9EA2"))
        t.rect(50, y, 55, y, hexc("#9A9EA2"))
    font_center(t, "READ", 16, SIGN_WHITE, x0=32, x1=63)
    font_center(t, "MORE", 24, UF_BLUE, x0=32, x1=63)
    for x in range(64):
        t.set(x, 0, SIGN_WHITE)
        t.set(x, 31, SIGN_WHITE)
    for y in range(32):
        for x in (0, 31, 32, 63):
            t.set(x, y, SIGN_WHITE)
    return t


def tx_int_sign(lines, bg_hex, seed, frame_hex=None, stripes=False):
    """64 x 32 sign, mapped once onto a 2:1 panel. lines: [(text, y, scale, colour hex)], centred."""
    t = Tex(64, 32, hexc(bg_hex), seed)
    t.noise(2)
    if stripes:                                           # hazard stripes along the bottom
        for y in range(27, 32):
            for x in range(64):
                t.set(x, y, hexc("#1E1E1E") if (x + y) % 8 < 4 else hexc(bg_hex))
    for text, y, scale, col in lines:
        font_center(t, text, y, hexc(col), scale=scale)
    if frame_hex:
        for x in range(64):
            t.set(x, 0, hexc(frame_hex))
            t.set(x, 31, hexc(frame_hex))
        for y in range(32):
            t.set(0, y, hexc(frame_hex))
            t.set(63, y, hexc(frame_hex))
    return t


def tx_int_sign_cafe(seed):
    """Chalkboard menu board: CAFE + two menu lines with prices, wood frame."""
    t = Tex(64, 32, hexc("#2E3A32"), seed)
    t.noise(4)
    chalk = hexc("#ECEAE0")
    font_center(t, "CAFE", 1, chalk, scale=2)
    font_text(t, "COFFEE", 4, 16, hexc("#E8C878"))
    font_text(t, "2", 56, 16, chalk)
    font_text(t, "BAGEL", 4, 24, hexc("#9AD0E8"))
    font_text(t, "3", 56, 24, chalk)
    for x in range(42, 54, 2):
        t.set(x, 22, chalk)
        t.set(x, 30, chalk)
    for x in range(64):
        t.set(x, 0, hexc("#8A6A44"))
        t.set(x, 31, hexc("#8A6A44"))
    for y in range(32):
        t.set(0, y, hexc("#8A6A44"))
        t.set(63, y, hexc("#8A6A44"))
    return t


def tx_int_sign_floors(seed):
    """Wayfinding atlas, 4 x 2 cells of 16 x 16 px: 1 2 3 4 / 5 6 up down (white on UF blue). The kit maps
    one cell: cell i = column i % 4, row i // 4 (row 0 = top)."""
    t = Tex(64, 32, UF_BLUE, seed)
    for i, ch in enumerate("123456^v"):
        cx, cy = (i % 4) * 16, (i // 4) * 16
        for k in range(16):
            for (x, y) in ((cx + k, cy), (cx + k, cy + 15), (cx, cy + k), (cx + 15, cy + k)):
                t.set(x, y, hexc("#14207A"))
        font_text(t, ch, cx + 3, cy + 1, SIGN_WHITE if ch.isdigit() else UF_ORANGE, scale=2)
    return t


def build_interior():
    """-> {int_* name: Tex} for every stage_palette.INTERIOR_MATERIALS entry (seeds 101+, deterministic)."""
    T = {
        "int_carpet": tx_int_carpet("#46597A", ("#E07A3A", "#8AA2C8", "#2E3C56"), 101),
        "int_carpet_accent": tx_int_carpet_accent(102),
        "int_floor_tile": tx_int_floor_tile(103),
        "int_stone": tx_int_stone(104),
        "int_drywall": tx_int_paint("#E4DED0", 105),
        "int_wall_blue": tx_int_paint("#2C4A8E", 106, amp=4),
        "int_ceiling": tx_int_ceiling(107),
        "int_light": tx_int_light(108),
        "int_books": tx_int_books(BOOK_WARM, 109),
        "int_books_b": tx_int_books(BOOK_JOURNAL, 110, runs=True),
        "int_shelf_steel": tx_int_steel("#C8C0AA", 111),
        "int_wood": tx_int_wood("#B88A58", 112),
        "int_wood_dark": tx_int_wood("#6A4A32", 113),
        "int_glass": tx_int_glass(114),
        "int_rail_bars": tx_int_rail_bars(115),
        "int_metal": tx_int_brushed("#A8ACB0", 116),
        "int_plastic": tx_int_paint("#2E3034", 117, amp=4, speck=10),
        "int_fabric_orange": tx_int_fabric("#E2642C", 118),
        "int_fabric_blue": tx_int_fabric("#2E4C9A", 119),
        "int_fabric_green": tx_int_fabric("#4E8A5A", 120),
        "int_whiteboard": tx_int_whiteboard(121),
        "int_monitor": tx_int_monitor(122),
        "int_kiosk": tx_int_kiosk(123),
        "int_elevator": tx_int_elevator(124),
        "int_stair": tx_int_stair(125),
        "int_window": tx_int_window(126),
        "int_posters": tx_int_posters(127),
        "int_sign_quiet": tx_int_sign([("QUIET", 1, 2, "#F4F2EC"), ("FLOOR", 17, 2, "#F4F2EC")], "#0021A5", 128),
        "int_sign_out_of_order": tx_int_sign([("OUT OF", 2, 1, "#1E1E1E"), ("ORDER", 11, 2, "#1E1E1E")], "#F2C230",
                                             129, stripes=True),
        "int_sign_study": tx_int_sign([("GROUP", 1, 2, "#FA4616"), ("STUDY", 17, 2, "#F4F2EC")], "#0021A5", 130),
        "int_sign_help": tx_int_sign([("HELP", 1, 2, "#F4F2EC"), ("DESK", 17, 2, "#F4F2EC")], "#FA4616", 131),
        "int_sign_cafe": tx_int_sign_cafe(132),
        "int_sign_marston": tx_int_sign([("MARSTON", 3, 1, "#F4F2EC"), ("SCIENCE", 12, 1, "#F4F2EC"),
                                         ("LIBRARY", 21, 1, "#FA4616")], "#0021A5", 133, frame_hex="#F4F2EC"),
        "int_sign_floors": tx_int_sign_floors(134),
    }
    missing = set(INTERIOR_MATERIALS) - set(T)
    if missing:
        raise SystemExit(f"no interior texture recipe for {sorted(missing)}")
    return T


def contact_sheet(imgs, path, cols=8, cell=136):
    sh = Image.new("RGB", (cols * cell, ((len(imgs) + cols - 1) // cols) * (cell + 14)), (40, 40, 40))
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
    sh.save(path)


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
    # interior kit textures (int_*; written next to the outdoor ones, not on the outdoor --sheet).
    # --interior-sheet PNG: contact sheet of just these (shown 2 x 2 tiled; magenta = cut-out alpha)
    TI = build_interior()
    iimgs = {}
    for name, m in INTERIOR_MATERIALS.items():
        im = TI[name].image()
        if im.size not in ((32, 32), (64, 32)):
            raise SystemExit(f"{name}: {im.size[0]}x{im.size[1]} is not 32x32 / 64x32")
        im.save(os.path.join(out, m["tex"]))
        iimgs[name] = im
    print(f"make_textures: wrote {len(iimgs)} interior kit textures to {out}")
    if "--interior-sheet" in argv:
        isheet = os.path.abspath(argv[argv.index("--interior-sheet") + 1])
        os.makedirs(os.path.dirname(isheet), exist_ok=True)
        contact_sheet(iimgs, isheet)
        print("make_textures: interior sheet", isheet)


if __name__ == "__main__":
    main()
