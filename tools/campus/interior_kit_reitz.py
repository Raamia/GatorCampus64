"""Reitz Union interior kit: the J. Wayne Reitz Union's own materials, N64-style textures, plan geometry
helpers and photo-matched props, for tools/campus/interiors/reitz.py (Course 2 area 2, the Reitz Union
interior of levels/wf). It builds on tools/campus/interior_kit.py (imported, never changed here: the Marston
stage owns it).

    tools/.venv/bin/python -I tools/campus/interior_kit_reitz.py --textures   write art/levels/textures/int_ru_*.png
    tools/.venv/bin/python -I tools/campus/interior_kit_reitz.py --selftest   geometry + prop checks (no Blender)
    tools/.venv/bin/python -I tools/campus/interior_kit_reitz.py --sheet PNG  texture contact sheet

Materials (RU_MATERIALS, "int_ru_*"): additive. register() merges them into stage_palette.INTERIOR_MATERIALS at
import time of THIS module only, so no other stage (outdoor or interior) sees them and every other build exports
exactly as before. The textures come from the reference photos (reference/interiors/reitz/index.json; the photo
each one was sampled from is in its recipe's docstring) and are 32 x 32, 64 x 32 or 32 x 64 RGBA16 (each fits
the 4 KB TMEM, like every other SGL64 texture). Brand marks are not reproduced: the food court storefronts get
generic signs (BURGERS, PIZZA, ...) in the colours of the real counters.

Geometry helpers (pure Python, map metres): polygon cleaning, point-in-polygon, ear-clipping triangulation
(with holes), convex clipping, grid splitting for the vertex-colour bake, polygon offset. Props (pure Python,
interior_kit.Prop in local coordinates, front = local +y, as the kit's convention): bowling lane sets,
billiards, booths, arcade cabinets, esports stations, the atrium lounge set, UF letters, the Swamp Boss gator
head, food court storefronts, theatre chair rows (cut-out row textures), auditorium seating, senate desks,
hotel furniture, ...
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import stage_palette  # noqa: E402

# ================================================================== materials
# name: tex size (w, h), tile_m, colour (sRGB average: previews + Fast64 diffuse), kind, map
# kind: opaque | cutout (1-bit alpha, layer 4) | water (translucent, layer 5); map: tile | once
RU_MATERIALS = {
    # ---- floors
    "int_ru_terrazzo":     {"size": (32, 32), "tile_m": 1.5, "color": "#E6E2DA"},
    "int_ru_carpet_atrium": {"size": (64, 32), "tile_m": 3.0, "color": "#2C3F8E"},
    "int_ru_gator_track":  {"size": (32, 32), "tile_m": 0.6, "color": "#1E2A5A", "kind": "cutout", "map": "once"},
    "int_ru_lane":         {"size": (32, 32), "tile_m": 1.06, "color": "#D8B07A"},
    "int_ru_lane_arrows":  {"size": (32, 64), "tile_m": 1.06, "color": "#D2A874", "map": "once"},
    "int_ru_plank":        {"size": (64, 32), "tile_m": 2.4, "color": "#8E8C8A"},
    "int_ru_carpet_billiards": {"size": (64, 32), "tile_m": 2.4, "color": "#2A3C86"},
    "int_ru_fc_checker":   {"size": (32, 32), "tile_m": 1.2, "color": "#A88E66"},
    "int_ru_fc_tile":      {"size": (32, 32), "tile_m": 1.2, "color": "#B6B0A4"},
    "int_ru_carpet_meeting": {"size": (64, 32), "tile_m": 2.4, "color": "#56688E"},
    "int_ru_carpet_ballroom": {"size": (64, 32), "tile_m": 6.0, "color": "#2252B0"},
    "int_ru_maple":        {"size": (64, 32), "tile_m": 1.6, "color": "#CC9C66"},
    "int_ru_dance":        {"size": (32, 32), "tile_m": 2.0, "color": "#2C2C30"},
    "int_ru_carpet_olive": {"size": (32, 32), "tile_m": 1.2, "color": "#5C5838"},
    "int_ru_carpet_grey":  {"size": (32, 32), "tile_m": 1.2, "color": "#9C9A96"},
    "int_ru_carpet_hotel": {"size": (32, 32), "tile_m": 1.2, "color": "#5C6688"},
    "int_ru_carpet_aud":   {"size": (32, 32), "tile_m": 1.6, "color": "#46567E"},
    "int_ru_concrete_dark": {"size": (32, 32), "tile_m": 2.0, "color": "#5C5C5E"},
    "int_ru_paving":       {"size": (32, 32), "tile_m": 3.0, "color": "#C2BEB4"},
    # ---- walls
    "int_ru_wall":         {"size": (32, 32), "tile_m": 2.0, "color": "#EDEBE6"},
    "int_ru_wall_greyblue": {"size": (32, 32), "tile_m": 2.0, "color": "#A6B2C4"},
    "int_ru_wall_royal":   {"size": (32, 32), "tile_m": 2.0, "color": "#1E3CA0"},
    "int_ru_wall_navy":    {"size": (32, 32), "tile_m": 2.0, "color": "#22283A"},
    "int_ru_wall_grey":    {"size": (32, 32), "tile_m": 2.0, "color": "#B2B4B6"},
    "int_ru_wall_slate":   {"size": (32, 32), "tile_m": 2.0, "color": "#80848A"},
    "int_ru_wall_cream":   {"size": (32, 32), "tile_m": 2.0, "color": "#E8E0CC"},
    "int_ru_hex":          {"size": (32, 32), "tile_m": 1.2, "color": "#2E3036"},
    "int_ru_hex_neon":     {"size": (64, 32), "tile_m": 1.6, "color": "#AAC8FF", "kind": "cutout", "map": "once"},
    "int_ru_gator_skin":   {"size": (32, 32), "tile_m": 1.4, "color": "#B4B8BC"},
    "int_ru_acoustic":     {"size": (32, 32), "tile_m": 1.2, "color": "#E2E2E0"},
    "int_ru_cherry":       {"size": (32, 32), "tile_m": 1.2, "color": "#8C4026"},
    "int_ru_chevron":      {"size": (32, 32), "tile_m": 1.6, "color": "#9A4A2A"},
    "int_ru_cedar":        {"size": (32, 32), "tile_m": 0.8, "color": "#C27846"},
    "int_ru_brick":        {"size": (32, 32), "tile_m": 2.0, "color": "#A2533C"},
    "int_ru_wood_panel":   {"size": (32, 32), "tile_m": 1.2, "color": "#B07A44"},
    "int_ru_slat_dark":    {"size": (32, 32), "tile_m": 1.2, "color": "#4C3628"},
    "int_ru_mirror":       {"size": (32, 32), "tile_m": 2.0, "color": "#B6C6CE"},
    "int_ru_paint_lime":   {"size": (32, 32), "tile_m": 2.0, "color": "#B6D034"},
    "int_ru_paint_sky":    {"size": (32, 32), "tile_m": 2.0, "color": "#90CADC"},
    "int_ru_counter_front": {"size": (32, 32), "tile_m": 1.0, "color": "#A6D2DE"},
    "int_ru_soffit":       {"size": (32, 32), "tile_m": 2.0, "color": "#ECE6D6"},
    "int_ru_white":        {"size": (32, 32), "tile_m": 2.0, "color": "#F4F4F2"},
    "int_ru_black":        {"size": (32, 32), "tile_m": 1.0, "color": "#1E1F22"},
    "int_ru_steel":        {"size": (32, 32), "tile_m": 1.0, "color": "#B4B8BC"},
    "int_ru_orange":       {"size": (32, 32), "tile_m": 1.0, "color": "#F0561E"},
    "int_ru_uf_blue":      {"size": (32, 32), "tile_m": 1.0, "color": "#1E3C9E"},
    "int_ru_red":          {"size": (32, 32), "tile_m": 1.0, "color": "#C42A26"},
    # ---- ceilings + light
    "int_ru_coffer":       {"size": (32, 32), "tile_m": 1.2, "color": "#F2F2EE"},
    "int_ru_led":          {"size": (32, 32), "tile_m": 1.0, "color": "#FFFFFF"},
    "int_ru_tile_ceiling": {"size": (32, 32), "tile_m": 1.2, "color": "#E4E2DC"},
    # ---- upholstery, felt, plastics
    "int_ru_felt":         {"size": (32, 32), "tile_m": 1.0, "color": "#1E5ACC"},
    "int_ru_leather_navy": {"size": (32, 32), "tile_m": 0.8, "color": "#28366E"},
    "int_ru_leather_grey": {"size": (32, 32), "tile_m": 0.8, "color": "#8E8C8A"},
    "int_ru_fabric_taupe": {"size": (32, 32), "tile_m": 0.6, "color": "#9C8C6E"},
    "int_ru_fabric_navy":  {"size": (32, 32), "tile_m": 0.6, "color": "#26386E"},
    "int_ru_fabric_char":  {"size": (32, 32), "tile_m": 0.6, "color": "#3A3C40"},
    "int_ru_gator_green":  {"size": (32, 32), "tile_m": 0.5, "color": "#4E6E32"},
    "int_ru_bed":          {"size": (32, 32), "tile_m": 1.0, "color": "#F0F0EC"},
    "int_ru_drape":        {"size": (32, 32), "tile_m": 1.2, "color": "#1C1C22"},
    "int_ru_tablecloth":   {"size": (32, 32), "tile_m": 1.0, "color": "#1C2A5E"},
    # ---- glass (translucent)
    "int_ru_glass":        {"size": (32, 32), "tile_m": 3.0, "color": "#A8CCE0", "kind": "water", "alpha": 0.30},
    "int_ru_glass_blue":   {"size": (32, 32), "tile_m": 3.0, "color": "#5A8CB8", "kind": "water", "alpha": 0.50},
    # ---- railings (cut-out)
    "int_ru_picket":       {"size": (32, 32), "tile_m": 1.1, "color": "#9A9EA2", "kind": "cutout"},
    # ---- chair rows (cut-out, mapped once per 4-chair panel)
    "int_ru_row_navy":     {"size": (64, 32), "tile_m": 2.0, "color": "#26346A", "kind": "cutout", "map": "once"},
    "int_ru_row_black":    {"size": (64, 32), "tile_m": 2.0, "color": "#2A2A2E", "kind": "cutout", "map": "once"},
    "int_ru_row_aud":      {"size": (64, 32), "tile_m": 1.8, "color": "#2A3A6A", "kind": "cutout", "map": "once"},
    "int_ru_row_wood":     {"size": (64, 32), "tile_m": 1.8, "color": "#8A5A30", "kind": "cutout", "map": "once"},
    # ---- doors (32 x 64, one leaf, mapped once)
    "int_ru_door":         {"size": (32, 64), "tile_m": 2.2, "color": "#B07A40", "map": "once"},
    "int_ru_door_walnut":  {"size": (32, 64), "tile_m": 2.4, "color": "#5E3C24", "map": "once"},
    "int_ru_door_glass":   {"size": (32, 64), "tile_m": 2.4, "color": "#4A6478", "map": "once"},
    "int_ru_door_steel":   {"size": (32, 64), "tile_m": 2.2, "color": "#A8ACB0", "map": "once"},
    # ---- screens, signs, art (mapped once)
    "int_ru_video_wall":   {"size": (64, 32), "tile_m": 4.0, "color": "#2850B8", "map": "once"},
    "int_ru_masking":      {"size": (64, 32), "tile_m": 4.0, "color": "#1E2E66", "map": "once"},
    "int_ru_score_tv":     {"size": (32, 32), "tile_m": 1.0, "color": "#2A4AA0", "map": "once"},
    "int_ru_game_screen":  {"size": (32, 32), "tile_m": 1.0, "color": "#4A70A8", "map": "once"},
    "int_ru_arcade":       {"size": (32, 64), "tile_m": 1.8, "color": "#6A3A8A", "map": "once"},
    "int_ru_proj_screen":  {"size": (32, 32), "tile_m": 2.0, "color": "#F2F2F0", "map": "once"},
    "int_ru_sign_gameroom": {"size": (64, 32), "tile_m": 3.0, "color": "#1E2C6A", "map": "once"},
    "int_ru_sign_esports": {"size": (64, 32), "tile_m": 4.0, "color": "#E8F0FF", "kind": "cutout", "map": "once"},
    "int_ru_sign_union":   {"size": (64, 32), "tile_m": 4.0, "color": "#D8D8D8", "kind": "cutout", "map": "once"},
    "int_ru_sign_wayfind": {"size": (64, 32), "tile_m": 1.6, "color": "#1E3C9E", "map": "once"},
    "int_ru_sign_rooms":   {"size": (64, 32), "tile_m": 1.6, "color": "#E8E8E4", "map": "once"},
    "int_ru_sign_ballroom": {"size": (64, 32), "tile_m": 2.4, "color": "#2A2E3A", "map": "once"},
    "int_ru_sign_hotel":   {"size": (64, 32), "tile_m": 2.4, "color": "#1E3C9E", "map": "once"},
    "int_ru_sign_info":    {"size": (64, 32), "tile_m": 2.0, "color": "#1E3C9E", "map": "once"},
    "int_ru_sign_foodcourt": {"size": (64, 32), "tile_m": 3.0, "color": "#F05A1E", "map": "once"},
    "int_ru_floor_atlas":  {"size": (64, 32), "tile_m": 0.6, "color": "#1E3C9E", "map": "once"},
    "int_ru_vend_burger":  {"size": (64, 32), "tile_m": 3.0, "color": "#1C2A5E", "map": "once"},
    "int_ru_vend_pizza":   {"size": (64, 32), "tile_m": 3.0, "color": "#2C6A3A", "map": "once"},
    "int_ru_vend_wok":     {"size": (64, 32), "tile_m": 3.0, "color": "#B02420", "map": "once"},
    "int_ru_vend_halal":   {"size": (64, 32), "tile_m": 3.0, "color": "#1E1E22", "map": "once"},
    "int_ru_vend_coffee":  {"size": (64, 32), "tile_m": 3.0, "color": "#1E5A3E", "map": "once"},
    "int_ru_vend_smoothie": {"size": (64, 32), "tile_m": 3.0, "color": "#6A3A8E", "map": "once"},
    "int_ru_vend_mac":     {"size": (64, 32), "tile_m": 3.0, "color": "#E8B020", "map": "once"},
    "int_ru_vend_taco":    {"size": (64, 32), "tile_m": 3.0, "color": "#1E8A86", "map": "once"},
    "int_ru_menu":         {"size": (64, 32), "tile_m": 2.0, "color": "#22262E", "map": "once"},
    "int_ru_art":          {"size": (64, 32), "tile_m": 3.0, "color": "#8A7A6A", "map": "once"},
    "int_ru_photos":       {"size": (64, 32), "tile_m": 3.0, "color": "#7A6A58", "map": "once"},
    "int_ru_mural_acc":    {"size": (32, 32), "tile_m": 2.4, "color": "#D27A4A", "map": "once"},
    "int_ru_flags":        {"size": (64, 32), "tile_m": 2.0, "color": "#8A5A6A", "map": "once"},
    "int_ru_exit":         {"size": (32, 32), "tile_m": 0.4, "color": "#3A1A1A", "map": "once"},
    "int_ru_dais":         {"size": (64, 32), "tile_m": 2.0, "color": "#2A3A7A", "map": "once"},
    "int_ru_window_view":  {"size": (64, 32), "tile_m": 3.0, "color": "#86A6BC", "map": "once"},
    "int_ru_books":        {"size": (64, 32), "tile_m": 2.0, "color": "#7A5A4A", "map": "once"},
    "int_ru_tv_hotel":     {"size": (32, 32), "tile_m": 1.0, "color": "#26323E", "map": "once"},
    "int_ru_pins":         {"size": (32, 32), "tile_m": 1.0, "color": "#EEEEEA", "map": "once"},
}
for _m in RU_MATERIALS.values():
    _m["tex"] = None
for _n, _m in RU_MATERIALS.items():
    _m["tex"] = _n + ".png"
    _m.setdefault("kind", "opaque")
    _m.setdefault("map", "tile")
    _m.setdefault("lit", "vertex")


def register():
    """Merge the int_ru_* materials into stage_palette.INTERIOR_MATERIALS (in place: interior_kit and
    stage_materials read the same dict). Idempotent; only Reitz builds import this module."""
    for name, m in RU_MATERIALS.items():
        if name not in stage_palette.INTERIOR_MATERIALS:
            stage_palette.INTERIOR_MATERIALS[name] = {k: v for k, v in m.items() if k != "size"}
    return list(RU_MATERIALS)


register()

import interior_kit as K  # noqa: E402  (after register(): the kit's known_material() sees int_ru_*)


# ================================================================== textures (Pillow, tools venv)
def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def q5(c):
    v = max(0, min(255, int(round(c))))
    v5 = (v * 31 + 127) // 255
    return (v5 << 3) | (v5 >> 2)


def shade(c, k):
    return tuple(max(0, min(255, int(round(x * k)))) for x in c)


def mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class Tex:
    """Pixel buffer (rows top to bottom) -> RGBA16-quantised PIL image (make_textures.Tex, copied so this
    module does not depend on that shared script's state)."""

    def __init__(self, w, h, color, seed, alpha=255):
        self.w, self.h = w, h
        self.r = random.Random(seed)
        self.px = [[tuple(color[:3]) + (alpha,) for _ in range(w)] for _ in range(h)]

    def set(self, x, y, c, a=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = tuple(int(v) for v in c[:3]) + (a,)

    def get(self, x, y):
        return self.px[y % self.h][x % self.w]

    def rect(self, x0, y0, x1, y1, c, a=255):
        for y in range(max(0, y0), min(self.h - 1, y1) + 1):
            for x in range(max(0, x0), min(self.w - 1, x1) + 1):
                self.set(x, y, c, a)

    def noise(self, amp, mono=True):
        for y in range(self.h):
            for x in range(self.w):
                r, g, b, a = self.px[y][x]
                if a < 128:
                    continue
                if mono:
                    d = self.r.uniform(-amp, amp)
                    self.px[y][x] = (r + d, g + d, b + d, a)
                else:
                    self.px[y][x] = (r + self.r.uniform(-amp, amp), g + self.r.uniform(-amp, amp),
                                     b + self.r.uniform(-amp, amp), a)

    def speckle(self, n, colors):
        for _ in range(n):
            self.set(self.r.randrange(self.w), self.r.randrange(self.h), self.r.choice(colors))

    def frame(self, c, x0=0, y0=0, x1=None, y1=None):
        x1 = self.w - 1 if x1 is None else x1
        y1 = self.h - 1 if y1 is None else y1
        for x in range(x0, x1 + 1):
            self.set(x, y0, c)
            self.set(x, y1, c)
        for y in range(y0, y1 + 1):
            self.set(x0, y, c)
            self.set(x1, y, c)

    def line(self, x0, y0, x1, y1, c, a=255):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / max(1, n)
            self.set(int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)), c, a)

    def disc(self, cx, cy, r, c, a=255):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.set(x, y, c, a)

    def image(self):
        from PIL import Image
        im = Image.new("RGBA", (self.w, self.h))
        im.putdata([tuple(q5(c) for c in p[:3]) + (255 if p[3] >= 128 else 0,) for row in self.px for p in row])
        return im


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
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ">": ["#....", ".#...", "..#..", "...#.", "..#..", ".#...", "#...."],
    "<": ["....#", "...#.", "..#..", ".#...", "..#..", "...#.", "....#"],
    "^": ["..#..", ".###.", "#.#.#", "..#..", "..#..", "..#..", "..#.."],
    "v": ["..#..", "..#..", "..#..", "..#..", "#.#.#", ".###.", "..#.."],
    "'": ["..#..", "..#..", ".....", ".....", ".....", ".....", "....."],
}
# 3 x 5 font for small labels (room plates, menu lines)
FONT3 = {
    "A": ["###", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": ["###", "#..", "#..", "#..", "###"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": ["###", "#..", "#.#", "#.#", "###"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"], "P": ["###", "#.#", "###", "#..", "#.."],
    "R": ["###", "#.#", "##.", "#.#", "#.#"], "S": ["###", "#..", "###", "..#", "###"],
    "T": ["###", ".#.", ".#.", ".#.", ".#."], "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."], "W": ["#.#", "#.#", "###", "###", "#.#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"], "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", "..#", "..#", "..#"],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
    "-": ["...", "...", "###", "...", "..."], "$": [".#.", "###", "##.", ".##", "###"],
    ">": ["#..", ".#.", "..#", ".#.", "#.."], "<": ["..#", ".#.", "#..", ".#.", "..#"],
}


def font_text(t, text, x, y, color, scale=1, spacing=1, font=FONT5, a=255):
    gw = len(next(iter(font.values()))[0])
    for ch in text:
        g = font.get(ch)
        if g is not None:
            for gy, row in enumerate(g):
                for gx, c in enumerate(row):
                    if c == "#":
                        t.rect(x + gx * scale, y + gy * scale, x + gx * scale + scale - 1, y + gy * scale + scale - 1,
                               color, a)
        x += (gw + spacing) * scale


def font_width(text, scale=1, spacing=1, font=FONT5):
    gw = len(next(iter(font.values()))[0])
    n = len(text)
    return n * gw * scale + max(0, n - 1) * spacing * scale if n else 0


def font_center(t, text, y, color, scale=1, spacing=1, x0=0, x1=None, font=FONT5, a=255):
    x1 = t.w - 1 if x1 is None else x1
    w = font_width(text, scale, spacing, font)
    font_text(t, text, x0 + (x1 - x0 + 1 - w) // 2, y, color, scale, spacing, font, a)


# ---------------------------------------------------------------- recipes
def _flat(hx, seed, amp=4, w=32, h=32):
    t = Tex(w, h, hexc(hx), seed)
    t.noise(amp)
    return t


def tx_terrazzo(seed):
    """White terrazzo with grey / black / warm chips (ru_floor_gator_tracks, ru_atrium_uf_letters_wall); a faint
    1.5 m joint."""
    t = Tex(32, 32, hexc("#ECE9E2"), seed)
    t.noise(2)
    t.speckle(60, [hexc("#CFCAC0"), hexc("#D8D2C6"), hexc("#C4BEB4"), hexc("#DCD2C0")])
    t.speckle(10, [hexc("#9A968E"), hexc("#A8A296")])
    for i in range(32):
        t.set(i, 0, hexc("#CFCBC2"))
        t.set(0, i, hexc("#CFCBC2"))
    return t


def tx_carpet_atrium(seed):
    """Atrium lounge carpet (ru_atrium_enr_lounge): royal blue / navy blocks with light-blue squiggle lines."""
    t = Tex(64, 32, hexc("#2C4092"), seed)
    for by in range(2):
        for bx in range(4):
            c = [hexc("#2C4092"), hexc("#1E2C6A"), hexc("#3A56B4"), hexc("#24367E")][(bx * 3 + by * 2) % 4]
            t.rect(bx * 16, by * 16, bx * 16 + 15, by * 16 + 15, c)
    t.noise(5)
    for k in range(5):
        ph = t.r.uniform(0, 6.28)
        y0 = 3 + k * 6
        for x in range(64):
            y = int(round(y0 + 2.2 * math.sin(x / 5.0 + ph)))
            t.set(x, y % 32, hexc("#8CB8E8"))
    t.speckle(30, [hexc("#5A7AD0"), hexc("#16204E")])
    return t


def tx_gator_track(seed):
    """One navy gator footprint on clear (ru_floor_gator_tracks): palm + four toes."""
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    navy = hexc("#1E2A5C")
    t.disc(16, 20, 6.5, navy)
    for dx, dy in ((-9, -4), (-4, -11), (4, -11), (9, -4)):
        t.line(16, 18, 16 + dx, 18 + dy, navy)
        t.line(17, 18, 17 + dx, 18 + dy, navy)
        t.disc(16 + dx, 18 + dy, 2.2, navy)
    return t


def tx_lane(seed):
    """Maple lane boards (ru_gr_lane_screens): 39 boards across a 1.06 m lane -> thin light / honey strips."""
    t = Tex(32, 32, hexc("#DCB47C"), seed)
    for x in range(32):
        k = 1.0 + t.r.uniform(-0.07, 0.07)
        for y in range(32):
            t.set(x, y, shade(hexc("#DCB47C"), k * (0.93 if x % 4 == 3 else 1.0)))
    t.noise(3)
    for _ in range(6):
        y = t.r.randrange(32)
        x = t.r.randrange(32)
        t.set(x, y, hexc("#E8C894"))
    return t


def tx_lane_arrows(seed):
    """Lane segment with the targeting arrows (32 x 64: the lane width x ~2.1 m), mapped once."""
    t = Tex(32, 64, hexc("#D8B07A"), seed)
    for x in range(32):
        k = 1.0 + t.r.uniform(-0.07, 0.07)
        for y in range(64):
            t.set(x, y, shade(hexc("#D8B07A"), k * (0.93 if x % 4 == 3 else 1.0)))
    dark = hexc("#4A2E1E")
    for i, xc in enumerate((4, 9, 13, 16, 19, 23, 28)):
        yc = 30 + abs(i - 3) * 5
        for d in range(4):
            t.set(xc - d // 2, yc + d, dark)
            t.set(xc + d // 2, yc + d, dark)
    for xc in (6, 11, 16, 21, 26):
        t.rect(xc, 8, xc, 9, dark)
    return t


def tx_plank(seed):
    """Grey wood-look plank flooring (ru_gr_booth_detail, ru_es_oelrich_9188): 20 cm x 1.2 m planks."""
    base = hexc("#8E8C8A")
    t = Tex(64, 32, base, seed)
    for row in range(8):
        off = (row * 23) % 64
        k = 1.0 + t.r.uniform(-0.08, 0.08)
        for y in range(row * 4, row * 4 + 4):
            for x in range(64):
                xs = (x + off) % 64
                c = shade(base, k * (0.86 if (y % 4 == 3 or xs % 32 == 0) else 1.0))
                if t.r.random() < 0.06:
                    c = shade(c, 1.08)
                t.set(x, y, c)
    t.noise(3)
    return t


def tx_carpet_billiards(seed):
    """Game Room billiards carpet (ru_gr_billiards_room): a light blue-grey gator-scale pattern, scales outlined in
    mid blue with white highlights and orange flecks, lighter and darker bands."""
    t = Tex(64, 32, hexc("#7E9ACA"), seed)
    for y in range(32):
        band = 1.0 + 0.07 * math.sin(y / 32.0 * 2 * math.pi)
        for x in range(64):
            row = y // 4
            xs = (x + (4 if row % 2 else 0)) % 8
            ys = y % 4
            if ys == 3 or xs == 7:
                c = hexc("#4C64A0")
            elif ys == 0 and xs in (2, 3, 4):
                c = hexc("#D6E2F4")
            else:
                c = shade(hexc("#8AA6D4") if (x // 16 + row) % 3 else hexc("#7088BC"), band)
            t.set(x, y, c)
    for _ in range(60):
        x, y = t.r.randrange(64), t.r.randrange(32)
        if y % 4 == 3:
            t.set(x, y, hexc("#E08A3A"))
    t.noise(3)
    return t


def tx_fc_checker(seed):
    """Food court queue ring (ru_food_court_counter_2023): tan / brown / dark brick-bond basketweave tile."""
    t = Tex(32, 32, hexc("#B49A6E"), seed)
    cols = [hexc("#BCA27A"), hexc("#9A7C52"), hexc("#6A5238"), hexc("#C8B08A")]
    for by in range(8):
        for bx in range(4):
            c = cols[(bx + by * 3) % 4] if (bx + by) % 2 else cols[(bx * 2 + by) % 4]
            xo = (bx * 8 + (4 if by % 2 else 0))
            for y in range(by * 4, by * 4 + 4):
                for x in range(xo, xo + 8):
                    t.set(x % 32, y, shade(c, 0.85) if (y % 4 == 3 or x % 8 == 7) else c)
    t.noise(3)
    return t


def tx_fc_tile(seed):
    """Food court hall tile (ru_food_court_counter_2023): grey-beige 30 cm squares, darker grout."""
    t = Tex(32, 32, hexc("#B8B2A6"), seed)
    for ty in range(4):
        for tx in range(4):
            k = 1.0 + t.r.uniform(-0.05, 0.05)
            for y in range(8):
                for x in range(8):
                    c = shade(hexc("#B8B2A6"), k)
                    if x == 7 or y == 7:
                        c = hexc("#8C877E")
                    t.set(tx * 8 + x, ty * 8 + y, c)
    t.noise(3)
    return t


def tx_carpet_meeting(seed):
    """Meeting room carpet tile (ru_os_g310_g320, ru_os_2315_2330): blue / grey patchwork with linear weave."""
    t = Tex(64, 32, hexc("#56688E"), seed)
    cols = [hexc("#4E6290"), hexc("#62708E"), hexc("#465EA0"), hexc("#6A7290"), hexc("#566A98")]
    for by in range(2):
        for bx in range(4):
            c = cols[(bx * 2 + by * 3 + bx * by) % 5]
            for y in range(by * 16, by * 16 + 16):
                for x in range(bx * 16, bx * 16 + 16):
                    k = 1.08 if ((x if (bx + by) % 2 else y) % 3 == 0) else 0.97
                    t.set(x, y, shade(c, k))
    t.noise(4)
    return t


def tx_carpet_ballroom(seed):
    """Grand Ballroom carpet (ru_os_grand_ballroom_1..4): royal blue with sparse flowing white lines that meander
    lengthwise (v) and cross now and then; 6 m repeat, lines anti-aliased."""
    t = Tex(64, 32, hexc("#2152B2"), seed)
    t.noise(4)
    line = hexc("#EEF2FA")
    specs = [(4.0, 6.0, 1, 0.3), (15.0, 4.0, 1, 2.1), (25.0, 7.5, 1, 4.0), (36.0, 5.0, 2, 1.2), (47.0, 6.5, 1, 5.2),
             (56.0, 3.5, 1, 3.3), (30.0, 9.0, 1, 0.9)]
    for xc, amp, cyc, ph in specs:
        for k in range(32 * 6):
            y = k / 6.0
            x = xc + amp * math.sin(2 * math.pi * cyc * y / 32.0 + ph)
            xi = int(math.floor(x))
            fr = x - xi
            for dx, w in ((0, 1.0 - fr), (1, fr)):
                px, py = (xi + dx) % 64, int(y) % 32
                if w < 0.15:
                    continue
                c = t.get(px, py)
                a = min(1.0, w * 1.4)
                t.set(px, py, tuple(int(c[i] * (1 - a) + line[i] * a) for i in range(3)))
    t.speckle(24, [hexc("#173E92"), hexc("#3466C6")])
    return t


def tx_maple(seed):
    """Rion Ballroom maple floor (ru_os_rion_ballroom): 6 cm strips, staggered joints."""
    base = hexc("#D4A46C")
    t = Tex(64, 32, base, seed)
    for row in range(16):
        off = t.r.randrange(64)
        k = 1.0 + t.r.uniform(-0.09, 0.09)
        for y in range(row * 2, row * 2 + 2):
            for x in range(64):
                c = shade(base, k * (0.9 if y % 2 == 1 else 1.0))
                if (x + off) % 40 == 0:
                    c = shade(c, 0.85)
                t.set(x, y, c)
    t.noise(3)
    return t


def tx_carpet_pattern(base_hx, line_hx, seed, kind="loop"):
    t = Tex(32, 32, hexc(base_hx), seed)
    t.noise(5)
    if kind == "loop":
        for cy in (8, 24):
            for cx in (8, 24):
                for a in range(24):
                    ang = a * 2 * math.pi / 24
                    t.set(int(cx + 5 * math.cos(ang)), int(cy + 5 * math.sin(ang)), hexc(line_hx))
    elif kind == "tri":
        for y in range(32):
            for x in range(32):
                if (x + y) % 16 == 0 or (x - y) % 16 == 0:
                    t.set(x, y, hexc(line_hx))
    elif kind == "diamond":
        for y in range(32):
            for x in range(32):
                if abs((x % 16) - 8) + abs((y % 16) - 8) == 7:
                    t.set(x, y, hexc(line_hx))
    t.speckle(20, [shade(hexc(base_hx), 1.2), shade(hexc(base_hx), 0.8)])
    return t


def tx_paving(seed):
    t = Tex(32, 32, hexc("#C2BEB4"), seed)
    t.noise(5)
    for i in range(32):
        t.set(i, 0, hexc("#9C988E"))
        t.set(0, i, hexc("#9C988E"))
        t.set(i, 16, hexc("#AAA69C"))
    t.speckle(20, [hexc("#A8A49A"), hexc("#D2CEC4")])
    return t


def tx_hex(seed):
    """Esports wall (ru_es_overview): charcoal hexagon relief."""
    t = Tex(32, 32, hexc("#2E3036"), seed)
    t.noise(3)
    for y in range(32):
        for x in range(32):
            # hex grid: rows 8 px, offset every other row
            row = y // 8
            xs = (x + (4 if row % 2 else 0)) % 8
            ys = y % 8
            if ys == 0 or (xs == 0 and ys < 8):
                t.set(x, y, hexc("#24262A"))
            elif ys == 1 or xs == 1:
                t.set(x, y, hexc("#3A3C44"))
    return t


def tx_hex_neon(seed):
    """Lit hex neon panel cluster (ru_es_overview, ru_es_pods): white-blue outlines on clear."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    glow = hexc("#DCE8FF")
    edge = hexc("#6A9CFF")
    cells = [(10, 9), (22, 9), (34, 9), (16, 20), (28, 20), (40, 20), (52, 20), (46, 9)]
    for cx, cy in cells:
        pts = [(cx + 6 * math.cos(math.radians(30 + 60 * k)), cy + 6 * math.sin(math.radians(30 + 60 * k)))
               for k in range(6)]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            t.line(a[0], a[1], b[0], b[1], glow)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            t.line(a[0] + 0.6, a[1] + 0.6, b[0] + 0.6, b[1] + 0.6, edge)
    return t


def tx_gator_skin(seed):
    """Gator-skin patterned wall behind the UF letters (ru_atrium_uf_letters_flickr): grey / white scutes."""
    t = Tex(32, 32, hexc("#C4C8CC"), seed)
    for by in range(4):
        for bx in range(4):
            xo = bx * 8 + (4 if by % 2 else 0)
            k = 1.0 + t.r.uniform(-0.1, 0.06)
            for y in range(by * 8, by * 8 + 8):
                for x in range(xo, xo + 8):
                    dx, dy = (x - xo) - 3.5, (y - by * 8) - 3.5
                    edge = abs(dx) > 2.8 or abs(dy) > 2.8 or abs(dx) + abs(dy) > 5.2
                    c = hexc("#8A8E94") if edge else shade(hexc("#D0D4D8"), k)
                    t.set(x % 32, y, c)
    t.noise(3)
    return t


def tx_acoustic(seed):
    """White 3-D triangular acoustic panels (ru_os_grand_ballroom_1): lit / shaded facets."""
    t = Tex(32, 32, hexc("#E6E6E4"), seed)
    for y in range(32):
        for x in range(32):
            cx, cy = x % 16, y % 16
            up = cy < 8
            k = 1.0
            if up:
                k = 1.04 if cx < 8 else 0.88
            else:
                k = 0.95 if cx < 8 else 0.80
            if (cx == 0) or (cy == 0):
                k = 0.75
            t.set(x, y, shade(hexc("#E6E6E4"), k))
    return t


def tx_wood(base_hx, seed, stripe=4, gap_k=0.7, vertical=True):
    base = hexc(base_hx)
    t = Tex(32, 32, base, seed)
    for i in range(32):
        k = 1.0 + t.r.uniform(-0.07, 0.07)
        for j in range(32):
            x, y = (i, j) if vertical else (j, i)
            c = shade(base, k * (gap_k if i % stripe == stripe - 1 else 1.0))
            if t.r.random() < 0.04:
                c = shade(c, 0.9)
            t.set(x, y, c)
    t.noise(2)
    return t


def tx_chevron(seed):
    """Senate Chamber dais wall (ru_os_chamber): cherry panels with chevron reveals."""
    t = Tex(32, 32, hexc("#9A4A2A"), seed)
    for y in range(32):
        for x in range(32):
            k = 1.0 + 0.05 * math.sin(x * 0.7 + y * 0.2)
            v = (y + abs((x % 16) - 8)) % 16
            if v == 0:
                k = 0.65
            t.set(x, y, shade(hexc("#9A4A2A"), k))
    t.noise(2)
    return t


def tx_brick(seed):
    base, mortar = hexc("#A2533C"), hexc("#C2B29A")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        course = y // 4
        for x in range(32):
            xs = x + (4 if course % 2 else 0)
            if y % 4 == 3 or xs % 8 == 7:
                t.set(x, y, mortar)
            else:
                t.set(x, y, shade(base, 1.0 + ((course * 7 + xs // 8 * 3) % 5 - 2) * 0.04))
    t.noise(5)
    return t


def tx_mirror(seed):
    """Dance studio mirror wall (ru_os_dance_1): the room reflected: pale wall band over a dark floor band."""
    t = Tex(32, 32, hexc("#B6C6CE"), seed)
    for y in range(32):
        for x in range(32):
            d = (x - y * 0.5) % 16
            k = 1.18 if d < 2 else 1.0
            base = hexc("#C8D2D8") if y < 22 else hexc("#4A4E56")
            t.set(x, y, shade(base, k * (0.92 + 0.08 * y / 31)))
    for y in range(32):
        t.set(15, y, hexc("#8A969C"))
    return t


def tx_counter_front(seed):
    """Food court counter front (ru_food_court_counter_2023): light-blue horizontal siding in white frames."""
    t = Tex(32, 32, hexc("#A6D2DE"), seed)
    for y in range(32):
        for x in range(32):
            c = hexc("#A6D2DE")
            if y % 4 == 3:
                c = hexc("#86B2C0")
            if x in (0, 1) or y in (0, 31):
                c = hexc("#F0EEE6")
            t.set(x, y, c)
    t.noise(2)
    return t


def tx_ceiling(seed, base="#E4E2DC"):
    """2 x 2 ft acoustic tile with a light grid (every Reitz room photo)."""
    t = Tex(32, 32, hexc(base), seed)
    t.noise(3)
    t.speckle(60, [shade(hexc(base), 0.86), shade(hexc(base), 0.92)])
    for i in range(32):
        t.set(i, 0, hexc("#F4F4F2"))
        t.set(i, 16, hexc("#F4F4F2"))
        t.set(0, i, hexc("#F4F4F2"))
        t.set(16, i, hexc("#F4F4F2"))
    return t


def tx_coffer(seed):
    """Grand Ballroom coffer field (ru_os_grand_ballroom_2): white luminous field crossed by gently waving slats."""
    t = Tex(32, 32, hexc("#FAFAF6"), seed)
    for x in range(32):
        for k in range(4):
            y = k * 8 + 2.0 * math.sin(2 * math.pi * x / 32.0 + k * 0.9)
            yi = int(math.floor(y)) % 32
            t.set(x, yi, hexc("#C8CACE"))
            t.set(x, (yi + 1) % 32, hexc("#E2E4E6"))
    return t


def tx_led(seed):
    return _flat("#FFFFFF", seed, amp=1)


def tx_felt(seed):
    t = Tex(32, 32, hexc("#1E5ACC"), seed)
    t.noise(4)
    return t


def tx_leather(hx, seed):
    """Booth upholstery (ru_gr_booth_row): channel tufting."""
    t = Tex(32, 32, hexc(hx), seed)
    for y in range(32):
        for x in range(32):
            k = 1.0 - 0.18 * (1.0 - abs((x % 8) - 3.5) / 3.5) ** 0.5 * (0.5 if x % 8 else 1.0)
            k = 0.82 if x % 8 == 0 else 1.0 + 0.06 * math.cos((x % 8 - 4) / 4.0)
            t.set(x, y, shade(hexc(hx), k))
    t.noise(3)
    return t


def tx_fabric(hx, seed):
    t = Tex(32, 32, hexc(hx), seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, shade(hexc(hx), 1.06 if (x + y) % 2 else 0.95))
    t.noise(4)
    return t


def tx_gator_green(seed):
    t = Tex(32, 32, hexc("#4E6E32"), seed)
    for y in range(32):
        for x in range(32):
            xs = (x + (4 if (y // 4) % 2 else 0)) % 8
            k = 0.7 if (y % 4 == 0 or xs == 0) else 1.0 + 0.1 * math.sin(x + y)
            t.set(x, y, shade(hexc("#4E6E32"), k))
    t.noise(4)
    return t


def tx_picket(seed):
    """Atrium railing infill (ru_atrium_hdr_flickr): silver pickets every 11 cm, top + bottom rails, with the
    small gator cut-out the Alligator reported in the panel between two pickets."""
    metal = hexc("#A4A8AC")
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    for y in range(32):
        for x in range(32):
            if y <= 1 or y >= 30 or x % 3 == 1 or y in (14, 15):
                t.set(x, y, shade(metal, 1.12 if y in (0, 30, 14) else 1.0))
    # gator silhouette on the mid rail (head left, tail right)
    for x in range(4, 28):
        t.set(x, 13, metal)
        t.set(x, 16, metal)
    for x in range(3, 9):
        t.set(x, 12, metal)
    return t


def tx_row(kind, seed):
    """Cut-out row of 4 chairs seen from behind / the side (64 x 32 = 4 seats x 0.5 m wide, ~1.0 m tall)."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    if kind == "navy":       # banquet chairs (ballrooms): navy padded back, dark frame
        back, frame = hexc("#26346A"), hexc("#18181C")
        for i in range(4):
            x0 = i * 16 + 2
            t.rect(x0, 2, x0 + 11, 17, back)
            t.frame(frame, x0, 2, x0 + 11, 17)
            t.rect(x0, 18, x0 + 11, 20, shade(back, 0.8))
            t.rect(x0 + 1, 21, x0 + 1, 31, frame)
            t.rect(x0 + 10, 21, x0 + 10, 31, frame)
    elif kind == "black":    # stacking chairs (meeting rooms): black shell, chrome legs
        shell, leg = hexc("#2A2A2E"), hexc("#9EA2A6")
        for i in range(4):
            x0 = i * 16 + 2
            for y in range(3, 18):
                w = 11 - (1 if y < 5 else 0)
                t.rect(x0 + (11 - w) // 2, y, x0 + (11 + w) // 2, y, shade(shell, 1.0 + 0.1 * (y < 6)))
            t.rect(x0, 18, x0 + 11, 20, shell)
            t.line(x0 + 1, 21, x0, 31, leg)
            t.line(x0 + 10, 21, x0 + 11, 31, leg)
    elif kind == "aud":      # auditorium seats (ru_os_auditorium_1): navy fabric, honey wood arm caps
        fab, wood = hexc("#2A3A6A"), hexc("#B07A40")
        for i in range(4):
            x0 = i * 16 + 1
            t.rect(x0 + 1, 1, x0 + 13, 20, fab)
            t.rect(x0 + 1, 1, x0 + 13, 2, shade(fab, 1.2))
            t.rect(x0 - 1, 14, x0 + 0, 31, wood)
            t.rect(x0 + 1, 21, x0 + 13, 26, shade(fab, 0.8))
    elif kind == "wood":     # auditorium seats from the front: wood backs (ru_os_auditorium_3)
        wood, fab = hexc("#9A6434"), hexc("#2A3A6A")
        for i in range(4):
            x0 = i * 16 + 1
            t.rect(x0 + 1, 1, x0 + 13, 20, wood)
            t.rect(x0 + 1, 1, x0 + 13, 1, shade(wood, 1.25))
            t.rect(x0 + 1, 21, x0 + 13, 25, fab)
            t.rect(x0 - 1, 14, x0, 31, shade(wood, 0.8))
    t.noise(2)
    return t


def tx_door(kind, seed):
    """One door leaf, 32 x 64 (~1.0 x 2.2 m incl. a 4 px frame)."""
    if kind == "honey":       # meeting rooms (ru_os_2345_2350): honey wood, narrow vision panel, lever
        t = Tex(32, 64, hexc("#B07A40"), seed)
        for x in range(32):
            k = 1.0 + 0.06 * math.sin(x * 0.9) + t.r.uniform(-0.03, 0.03)
            for y in range(64):
                t.set(x, y, shade(hexc("#B07A40"), k))
        t.rect(20, 10, 24, 34, hexc("#2E3A44"))
        t.frame(hexc("#8C8E90"), 19, 9, 25, 35)
        t.rect(4, 33, 9, 34, hexc("#C8CACC"))
        t.frame(hexc("#6A6C6E"), 0, 0, 31, 63)
    elif kind == "walnut":    # Grand Ballroom (ru_os_grand_ballroom_1): walnut leaf, tall pull
        t = Tex(32, 64, hexc("#5E3C24"), seed)
        for x in range(32):
            k = 1.0 + 0.08 * math.sin(x * 1.3) + t.r.uniform(-0.04, 0.04)
            for y in range(64):
                t.set(x, y, shade(hexc("#5E3C24"), k))
        t.rect(25, 20, 26, 40, hexc("#D0D2D4"))
        t.frame(hexc("#3A2616"), 0, 0, 31, 63)
    elif kind == "glass":     # aluminium storefront door
        t = Tex(32, 64, hexc("#4A6478"), seed)
        for y in range(64):
            for x in range(32):
                d = (x - y * 0.4) % 20
                t.set(x, y, shade(hexc("#4A6478"), 1.25 if d < 3 else 1.0))
        t.rect(0, 0, 31, 3, hexc("#B4B8BC"))
        t.rect(0, 58, 31, 63, hexc("#B4B8BC"))
        t.rect(0, 0, 3, 63, hexc("#B4B8BC"))
        t.rect(28, 0, 31, 63, hexc("#B4B8BC"))
        t.rect(4, 30, 27, 31, hexc("#9A9EA2"))
    else:                     # steel service / stair door
        t = Tex(32, 64, hexc("#A8ACB0"), seed)
        t.noise(3)
        t.rect(4, 32, 9, 33, hexc("#4A4C50"))
        t.rect(20, 8, 26, 22, hexc("#3A4650"))
        t.frame(hexc("#6A6C70"), 0, 0, 31, 63)
    return t


def tx_video_wall(seed):
    """Bowling video wall above the pins (ru_gr_lanes_crowd_tvs, ru_gr_lane_screens): blue sky graphic, an orange
    gator and GAME ROOM."""
    t = Tex(64, 32, hexc("#2850B8"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#3A78E0"), hexc("#14286A"), y / 31))
    for x in range(64):
        y = 22 + int(2 * math.sin(x / 6.0))
        for yy in range(y, 32):
            t.set(x, yy, hexc("#1E3A2E") if yy < 26 else hexc("#14201C"))
    # gator body + head
    org = hexc("#F06A1E")
    t.rect(10, 18, 34, 21, org)
    t.rect(34, 19, 44, 21, org)
    t.rect(4, 19, 10, 20, org)
    for x in (14, 20, 26, 30):
        t.rect(x, 22, x + 1, 24, org)
    t.set(38, 18, hexc("#FFFFFF"))
    font_text(t, "GAME", 18, 3, hexc("#FFFFFF"))
    font_text(t, "ROOM", 18, 11, hexc("#F0A030"))
    return t


def tx_masking(seed):
    """Masking units over the pin decks with the gator mural (ru_gr_kosmic_lanes)."""
    t = Tex(64, 32, hexc("#1E2E66"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#2A48A8"), hexc("#141E48"), y / 31))
    for x in range(64):
        yb = 14 + int(4 * math.sin(x / 9.0 + 1.0))
        for y in range(yb, yb + 3):
            t.set(x, y, hexc("#6CC838"))
        for y in range(yb + 3, 32):
            t.set(x, y, mix(hexc("#2E5A2A"), hexc("#16301A"), (y - yb) / 18))
    t.speckle(18, [hexc("#E0E8FF")])
    return t


def tx_score_tv(seed):
    """Overhead scoring monitor (ru_gr_lanes_monitors): blue frame grid with names and scores."""
    t = Tex(32, 32, hexc("#1E3C9E"), seed)
    t.rect(1, 1, 30, 30, hexc("#2A4AB0"))
    for r in range(4):
        y = 4 + r * 7
        t.rect(2, y, 29, y + 5, hexc("#F0F0F0") if r % 2 == 0 else hexc("#DCE4F4"))
        for c in range(6):
            t.set(10 + c * 3, y + 1, hexc("#222222"))
            t.set(10 + c * 3, y + 3, hexc("#CC2222"))
        t.rect(3, y + 1, 7, y + 3, hexc("#F06A1E"))
    t.frame(hexc("#0A0A0C"))
    return t


def tx_game_screen(seed):
    """A game on a screen (esports stations, arcade, lounge TVs): sky, track, characters."""
    t = Tex(32, 32, hexc("#4A70A8"), seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, mix(hexc("#6AA0E8"), hexc("#B8D8F8"), y / 18) if y < 18 else
                  mix(hexc("#3A8A3A"), hexc("#285A28"), (y - 18) / 13))
    for x in range(32):
        t.set(x, 18 + abs(x - 16) // 6, hexc("#E8E0C8"))
    t.rect(8, 20, 11, 24, hexc("#D82020"))
    t.rect(20, 21, 23, 25, hexc("#2030D8"))
    t.disc(25, 6, 3, hexc("#FFF0A0"))
    t.frame(hexc("#0C0C10"))
    return t


def tx_arcade(seed):
    """Arcade cabinet side art (ru_gr_arcade): purple / magenta panel with a lit marquee + screen."""
    t = Tex(32, 64, hexc("#5A2A86"), seed)
    for y in range(64):
        for x in range(32):
            t.set(x, y, mix(hexc("#7A3AB0"), hexc("#2A1048"), y / 63))
    t.rect(2, 2, 29, 9, hexc("#F0C030"))
    font_center(t, "PLAY", 3, hexc("#C02020"), font=FONT3)
    t.rect(4, 13, 27, 30, hexc("#101014"))
    t.rect(6, 15, 25, 28, hexc("#3A80D0"))
    t.rect(8, 22, 12, 26, hexc("#E04040"))
    t.rect(18, 20, 22, 24, hexc("#40E060"))
    t.rect(3, 34, 28, 40, hexc("#222228"))
    for x in (8, 13, 18, 23):
        t.disc(x, 37, 1.6, [hexc("#E02020"), hexc("#20A0E0"), hexc("#F0D020"), hexc("#20E040")][(x // 5) % 4])
    for y in range(42, 64, 6):
        t.line(0, y, 31, y - 8, hexc("#E040C0"))
    return t


def tx_proj_screen(seed):
    t = Tex(32, 32, hexc("#F2F2F0"), seed)
    t.noise(1)
    t.frame(hexc("#1A1A1C"))
    t.rect(0, 0, 31, 1, hexc("#1A1A1C"))
    return t


def tx_sign(lines, bg_hx, seed, frame_hx=None, w=64, h=32):
    t = Tex(w, h, hexc(bg_hx), seed)
    t.noise(2)
    for text, y, scale, col, font in lines:
        font_center(t, text, y, hexc(col), scale=scale, font=font)
    if frame_hx:
        t.frame(hexc(frame_hx))
    return t


def tx_sign_gameroom(seed):
    """REITZ UNION GAME ROOM wall graphic (ru_gr_entry_graphic, ru_gr_wall_graphic_billiards): navy space scene,
    planets and a bowling ball, white and orange lettering."""
    t = Tex(64, 32, hexc("#1A2660"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#22307A"), hexc("#10163E"), y / 31))
    t.speckle(26, [hexc("#E8ECFF"), hexc("#8CA4FF")])
    t.disc(52, 22, 7, hexc("#F06A1E"))
    t.disc(50, 20, 2, hexc("#F4A060"))
    for x in range(42, 62):
        t.set(x, 22 + (x - 52) // 4, hexc("#F0D8A0"))
    t.disc(8, 26, 4, hexc("#2848C0"))
    t.disc(7, 25, 1, hexc("#101010"))
    font_text(t, "REITZ UNION", 3, 3, hexc("#DCE0EC"), font=FONT3)
    font_text(t, "GAME", 3, 10, hexc("#FFFFFF"), scale=1)
    font_text(t, "ROOM", 3, 19, hexc("#F06A1E"), scale=1)
    return t


def tx_sign_esports(seed):
    """GATOR ESPORTS CENTER lit letters (ru_es_overview) on clear."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    font_center(t, "GATOR", 2, hexc("#F4F8FF"))
    font_center(t, "ESPORTS", 12, hexc("#F4F8FF"))
    font_center(t, "CENTER", 22, hexc("#9CC0FF"))
    return t


def tx_sign_union(seed):
    """J. WAYNE REITZ UNION letters (ru_south_ground_entrance; the north soffit, ru_north_entrance_hotelsite)."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    font_center(t, "J. WAYNE", 4, hexc("#E8E8E8"))
    font_center(t, "REITZ UNION", 16, hexc("#E8E8E8"), font=FONT5, spacing=0)
    return t


def tx_floor_atlas(seed):
    """Elevator floor labels: 8 cells of 16 x 16 (4 x 2): LL G 1 2 / 3 4 5 6, white on UF blue, an orange rule."""
    t = Tex(64, 32, hexc("#1E3C9E"), seed)
    labels = ["LL", "G", "1", "2", "3", "4", "5", "6"]
    for i, lab in enumerate(labels):
        cx, cy = (i % 4) * 16, (i // 4) * 16
        t.frame(hexc("#F06A1E"), cx, cy, cx + 15, cy + 15)
        font_center(t, lab, cy + 4 if len(lab) == 1 else cy + 5, hexc("#FFFFFF"), x0=cx, x1=cx + 15, spacing=1,
                    font=FONT5 if len(lab) == 1 else FONT3)
    return t


def tx_vendor(name, bg, fg, accent, seed, sub=None):
    t = Tex(64, 32, hexc(bg), seed)
    t.noise(2)
    font_center(t, name, 5 if sub else 9, hexc(fg), scale=1 if len(name) > 6 else 2 if len(name) <= 5 else 1,
                spacing=1)
    if sub:
        font_center(t, sub, 20, hexc(accent), font=FONT3)
    t.rect(0, 29, 63, 31, hexc(accent))
    return t


def tx_menu(seed):
    """Menu boards over a counter (ru_food_court_sonic_2025): dark screens with photo tiles and price lines."""
    t = Tex(64, 32, hexc("#22262E"), seed)
    for p in range(3):
        x0 = 1 + p * 21
        t.rect(x0, 1, x0 + 19, 30, hexc("#1A1C22"))
        t.rect(x0 + 2, 3, x0 + 17, 12, [hexc("#C86A2A"), hexc("#D8A030"), hexc("#B83A2A")][p])
        for r in range(4):
            y = 15 + r * 4
            t.rect(x0 + 2, y, x0 + 12, y + 1, hexc("#E8E8E8"))
            t.rect(x0 + 15, y, x0 + 17, y + 1, hexc("#F0C030"))
    return t


def tx_art(seed):
    """Framed art on a white wall (ru_the_gallery, ru_os_g315): three frames."""
    t = Tex(64, 32, hexc("#F0EEE8"), seed)
    frames = [(2, 6, 18, 26, "#1E3C9E"), (23, 4, 41, 28, "#C84A2A"), (46, 8, 61, 24, "#3A8A5A")]
    for x0, y0, x1, y1, c in frames:
        t.rect(x0, y0, x1, y1, hexc("#2A2420"))
        t.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, hexc("#F4F2EC"))
        t.rect(x0 + 3, y0 + 3, x1 - 3, y1 - 3, hexc(c))
        for k in range(6):
            t.line(x0 + 3 + t.r.randrange(x1 - x0 - 6), y0 + 3, x0 + 3 + t.r.randrange(x1 - x0 - 6), y1 - 3,
                   shade(hexc(c), 1.4))
    return t


def tx_photos(seed):
    """Framed historic photos (ru_os_matthews_2/4): sepia prints in cherry frames with mats."""
    t = Tex(64, 32, hexc("#B4B6B8"), seed)
    for i, (x0, y0, x1, y1) in enumerate([(2, 5, 17, 26), (22, 3, 41, 28), (46, 6, 61, 25)]):
        t.rect(x0, y0, x1, y1, hexc("#5A2E1C"))
        t.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, hexc("#ECE6D8"))
        t.rect(x0 + 3, y0 + 3, x1 - 3, y1 - 3, hexc("#8A7A64"))
        t.disc((x0 + x1) / 2, (y0 + y1) / 2 - 2, 2.5, hexc("#3A3026"))
        t.rect((x0 + x1) // 2 - 3, (y0 + y1) // 2 + 1, (x0 + x1) // 2 + 3, y1 - 4, hexc("#3A3026"))
    return t


def tx_mural_acc(seed):
    """Arts & Crafts Center mural (ru_acc_entrance_mural): colour burst around a navy roundel."""
    t = Tex(32, 32, hexc("#F4F2EE"), seed)
    cols = [hexc("#E8402A"), hexc("#F0C020"), hexc("#2A8AD8"), hexc("#3AB060"), hexc("#E86AA8"), hexc("#7AD0E8")]
    for k in range(40):
        a = k * 2 * math.pi / 40
        r1 = 15 if k % 2 else 12
        t.line(16, 16, 16 + r1 * math.cos(a), 16 + r1 * math.sin(a), cols[k % len(cols)])
    t.disc(16, 16, 7, hexc("#1E2450"))
    font_center(t, "ACC", 13, hexc("#FFFFFF"), font=FONT3)
    return t


def tx_flags(seed):
    """US (left) and Florida (right) flags, for the Senate Chamber dais (ru_os_chamber)."""
    t = Tex(64, 32, hexc("#F4F4F4"), seed)
    for y in range(32):
        for x in range(30):
            t.set(x, y, hexc("#C22A2A") if (y // 3) % 2 == 0 else hexc("#F4F4F4"))
    t.rect(0, 0, 13, 16, hexc("#2A3A8A"))
    for y in range(2, 16, 3):
        for x in range(1, 13, 3):
            t.set(x, y, hexc("#FFFFFF"))
    t.rect(30, 0, 33, 31, hexc("#C8B070"))
    t.rect(34, 0, 63, 31, hexc("#F4F4F4"))
    t.line(34, 0, 63, 31, hexc("#C22A2A"))
    t.line(35, 0, 63, 30, hexc("#C22A2A"))
    t.line(63, 0, 34, 31, hexc("#C22A2A"))
    t.line(62, 0, 34, 30, hexc("#C22A2A"))
    t.disc(48, 15, 4, hexc("#3A6AA8"))
    return t


def tx_exit(seed):
    t = Tex(32, 32, hexc("#2A1A1A"), seed)
    t.rect(1, 9, 30, 22, hexc("#F4F2EC"))
    font_center(t, "EXIT", 12, hexc("#D81E1E"), font=FONT5, spacing=1)
    return t


def tx_dais(seed):
    """Senate Chamber dais front (ru_os_chamber): navy panel with the UF seal band."""
    t = Tex(64, 32, hexc("#2A3A7A"), seed)
    t.noise(3)
    t.rect(0, 0, 63, 2, hexc("#C8C0B0"))
    t.disc(32, 15, 8, hexc("#F06A1E"))
    t.disc(32, 15, 6, hexc("#1E3C9E"))
    font_center(t, "UF", 12, hexc("#FFFFFF"), font=FONT3)
    return t


def tx_window_view(seed):
    """Painted window view (hotel rooms, high windows): sky, campus canopy, brick buildings."""
    t = Tex(64, 32, hexc("#86A6BC"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#5E92D6"), hexc("#BCD6EE"), y / 20) if y < 20 else hexc("#4A6A3A"))
    for b in range(4):
        x0 = t.r.randrange(56)
        h = t.r.randrange(4, 10)
        t.rect(x0, 20 - h, x0 + 8, 21, hexc("#A2583E"))
        for x in range(x0 + 1, x0 + 8, 2):
            t.set(x, 20 - h + 2, hexc("#2E3A48"))
    for x in range(0, 64, 3):
        t.disc(x + t.r.uniform(-1, 1), 20 + t.r.uniform(-1, 1), 2.5, shade(hexc("#3E6A30"), t.r.uniform(0.8, 1.2)))
    t.rect(31, 0, 32, 31, hexc("#D8D8D4"))
    t.rect(0, 15, 63, 15, hexc("#D8D8D4"))
    return t


def tx_books(seed):
    """Free-library shelf (atrium): book spines on two shelves."""
    t = Tex(64, 32, hexc("#6A4A32"), seed)
    cols = ["#A83A2A", "#2A4A8A", "#D8B040", "#3A7A4A", "#E8E0D0", "#6A2A5A", "#E87A30"]
    for row in range(2):
        y0 = row * 16 + 2
        x = 1
        while x < 62:
            w = t.r.randrange(2, 5)
            h = t.r.randrange(9, 13)
            c = hexc(t.r.choice(cols))
            t.rect(x, y0 + 13 - h, min(62, x + w - 1), y0 + 12, c)
            t.set(x, y0 + 14 - h, shade(c, 1.3))
            x += w
        t.rect(0, y0 + 13, 63, y0 + 14, hexc("#4A3222"))
    return t


def tx_tv_hotel(seed):
    t = Tex(32, 32, hexc("#26323E"), seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, mix(hexc("#2A3A4A"), hexc("#141A20"), (x + y) / 62))
    t.line(4, 6, 12, 2, hexc("#4A5A6A"))
    t.frame(hexc("#0A0A0C"))
    return t


def tx_pins(seed):
    """Bowling pin face: white with two red neck stripes (mapped on the pin quads)."""
    t = Tex(32, 32, hexc("#F2F2EE"), seed)
    t.rect(0, 6, 31, 7, hexc("#C82222"))
    t.rect(0, 10, 31, 11, hexc("#C82222"))
    for y in range(32):
        for x in range(32):
            k = 0.86 + 0.14 * math.cos((x - 16) / 16.0 * 1.4)
            r, g, b, a = t.px[y][x]
            t.set(x, y, shade((r, g, b), k))
    return t


TEXTURES = {
    "int_ru_terrazzo": tx_terrazzo,
    "int_ru_carpet_atrium": tx_carpet_atrium,
    "int_ru_gator_track": tx_gator_track,
    "int_ru_lane": tx_lane,
    "int_ru_lane_arrows": tx_lane_arrows,
    "int_ru_plank": tx_plank,
    "int_ru_carpet_billiards": tx_carpet_billiards,
    "int_ru_fc_checker": tx_fc_checker,
    "int_ru_fc_tile": tx_fc_tile,
    "int_ru_carpet_meeting": tx_carpet_meeting,
    "int_ru_carpet_ballroom": tx_carpet_ballroom,
    "int_ru_maple": tx_maple,
    "int_ru_dance": lambda s: _flat("#2C2C30", s, 3),
    "int_ru_carpet_olive": lambda s: tx_carpet_pattern("#5C5838", "#6E6A44", s, "diamond"),
    "int_ru_carpet_grey": lambda s: tx_carpet_pattern("#9C9A96", "#B4B2AE", s, "loop"),
    "int_ru_carpet_hotel": lambda s: tx_carpet_pattern("#5C6688", "#8A7A5A", s, "diamond"),
    "int_ru_carpet_aud": lambda s: tx_carpet_pattern("#46567E", "#5E6E96", s, "tri"),
    "int_ru_concrete_dark": lambda s: _flat("#5C5C5E", s, 5),
    "int_ru_paving": tx_paving,
    "int_ru_wall": lambda s: _flat("#EDEBE6", s, 2),
    "int_ru_wall_greyblue": lambda s: _flat("#A6B2C4", s, 2),
    "int_ru_wall_royal": lambda s: _flat("#1E3CA0", s, 3),
    "int_ru_wall_navy": lambda s: _flat("#22283A", s, 3),
    "int_ru_wall_grey": lambda s: _flat("#B2B4B6", s, 2),
    "int_ru_wall_slate": lambda s: _flat("#80848A", s, 2),
    "int_ru_wall_cream": lambda s: _flat("#E8E0CC", s, 2),
    "int_ru_hex": tx_hex,
    "int_ru_hex_neon": tx_hex_neon,
    "int_ru_gator_skin": tx_gator_skin,
    "int_ru_acoustic": tx_acoustic,
    "int_ru_cherry": lambda s: tx_wood("#8C4026", s, stripe=8, gap_k=0.8),
    "int_ru_chevron": tx_chevron,
    "int_ru_cedar": lambda s: tx_wood("#C87C48", s, stripe=4, gap_k=0.62, vertical=False),
    "int_ru_brick": tx_brick,
    "int_ru_wood_panel": lambda s: tx_wood("#B07A44", s, stripe=8, gap_k=0.7),
    "int_ru_slat_dark": lambda s: tx_wood("#4C3628", s, stripe=4, gap_k=0.5, vertical=False),
    "int_ru_mirror": tx_mirror,
    "int_ru_paint_lime": lambda s: _flat("#B6D034", s, 2),
    "int_ru_paint_sky": lambda s: _flat("#90CADC", s, 2),
    "int_ru_counter_front": tx_counter_front,
    "int_ru_soffit": lambda s: _flat("#ECE6D6", s, 2),
    "int_ru_white": lambda s: _flat("#F4F4F2", s, 1),
    "int_ru_black": lambda s: _flat("#1E1F22", s, 3),
    "int_ru_steel": lambda s: tx_wood("#B4B8BC", s, stripe=32, gap_k=1.0),
    "int_ru_orange": lambda s: _flat("#F0561E", s, 3),
    "int_ru_uf_blue": lambda s: _flat("#1E3C9E", s, 3),
    "int_ru_red": lambda s: _flat("#C42A26", s, 3),
    "int_ru_coffer": tx_coffer,
    "int_ru_led": tx_led,
    "int_ru_tile_ceiling": tx_ceiling,
    "int_ru_felt": tx_felt,
    "int_ru_leather_navy": lambda s: tx_leather("#28366E", s),
    "int_ru_leather_grey": lambda s: tx_leather("#8E8C8A", s),
    "int_ru_fabric_taupe": lambda s: tx_fabric("#9C8C6E", s),
    "int_ru_fabric_navy": lambda s: tx_fabric("#26386E", s),
    "int_ru_fabric_char": lambda s: tx_fabric("#3A3C40", s),
    "int_ru_gator_green": tx_gator_green,
    "int_ru_bed": lambda s: _flat("#F0F0EC", s, 2),
    "int_ru_drape": lambda s: tx_wood("#1C1C22", s, stripe=3, gap_k=0.7),
    "int_ru_tablecloth": lambda s: tx_fabric("#1C2A5E", s),
    "int_ru_glass": lambda s: _flat("#A8CCE0", s, 2),
    "int_ru_glass_blue": lambda s: _flat("#5A8CB8", s, 3),
    "int_ru_picket": tx_picket,
    "int_ru_row_navy": lambda s: tx_row("navy", s),
    "int_ru_row_black": lambda s: tx_row("black", s),
    "int_ru_row_aud": lambda s: tx_row("aud", s),
    "int_ru_row_wood": lambda s: tx_row("wood", s),
    "int_ru_door": lambda s: tx_door("honey", s),
    "int_ru_door_walnut": lambda s: tx_door("walnut", s),
    "int_ru_door_glass": lambda s: tx_door("glass", s),
    "int_ru_door_steel": lambda s: tx_door("steel", s),
    "int_ru_video_wall": tx_video_wall,
    "int_ru_masking": tx_masking,
    "int_ru_score_tv": tx_score_tv,
    "int_ru_game_screen": tx_game_screen,
    "int_ru_arcade": tx_arcade,
    "int_ru_proj_screen": tx_proj_screen,
    "int_ru_sign_gameroom": tx_sign_gameroom,
    "int_ru_sign_esports": tx_sign_esports,
    "int_ru_sign_union": tx_sign_union,
    "int_ru_sign_wayfind": lambda s: tx_sign([("GAME ROOM >", 4, 1, "#FFFFFF", FONT3),
                                              ("< FOOD COURT", 12, 1, "#FFFFFF", FONT3),
                                              ("< ATRIUM", 20, 1, "#FFFFFF", FONT3),
                                              ("ELEVATORS >", 26, 1, "#F0A060", FONT3)], "#1E3C9E", s, "#F06A1E"),
    "int_ru_sign_rooms": lambda s: tx_sign([("MEETING", 3, 1, "#1E3C9E", FONT5), ("ROOMS", 12, 1, "#1E3C9E", FONT5),
                                            ("2315-2365 >", 23, 1, "#3A3A3A", FONT3)], "#E8E8E4", s, "#8C8E90"),
    "int_ru_sign_ballroom": lambda s: tx_sign([("GRAND", 5, 1, "#E8E8E8", FONT5), ("BALLROOM", 16, 1, "#E8E8E8", FONT5)],
                                              "#2A2E3A", s, "#8A7A5A"),
    "int_ru_sign_hotel": lambda s: tx_sign([("REITZ UNION", 6, 1, "#FFFFFF", FONT3), ("HOTEL", 15, 1, "#F06A1E", FONT5)],
                                           "#1E3C9E", s, "#F06A1E"),
    "int_ru_sign_info": lambda s: tx_sign([("INFORMATION", 7, 1, "#FFFFFF", FONT3), ("DESK", 16, 1, "#F06A1E", FONT5)],
                                          "#1E3C9E", s),
    "int_ru_sign_foodcourt": lambda s: tx_sign([("FOOD", 4, 2, "#FFFFFF", FONT5), ("COURT", 21, 1, "#1E3C9E", FONT5)],
                                               "#F05A1E", s),
    "int_ru_floor_atlas": tx_floor_atlas,
    "int_ru_vend_burger": lambda s: tx_vendor("BURGERS", "#1C2A5E", "#F04A3A", "#F0C030", s, "DRIVE-IN"),
    "int_ru_vend_pizza": lambda s: tx_vendor("PIZZA", "#2C6A3A", "#F4F0E0", "#D8302A", s),
    "int_ru_vend_wok": lambda s: tx_vendor("WOK", "#B02420", "#F8E8C0", "#2A2A2A", s, "EXPRESS"),
    "int_ru_vend_halal": lambda s: tx_vendor("HALAL", "#1E1E22", "#F0A030", "#F0A030", s, "GRILL"),
    "int_ru_vend_coffee": lambda s: tx_vendor("COFFEE", "#1E5A3E", "#F4F0E4", "#C8A060", s, "BAR"),
    "int_ru_vend_smoothie": lambda s: tx_vendor("SHAKES", "#6A3A8E", "#C8F040", "#C8F040", s, "SMOOTHIES"),
    "int_ru_vend_mac": lambda s: tx_vendor("MAC", "#E8B020", "#1E2A5E", "#1E2A5E", s, "AND CHEESE"),
    "int_ru_vend_taco": lambda s: tx_vendor("TACOS", "#1E8A86", "#F8F0D8", "#F06A3A", s),
    "int_ru_menu": tx_menu,
    "int_ru_art": tx_art,
    "int_ru_photos": tx_photos,
    "int_ru_mural_acc": tx_mural_acc,
    "int_ru_flags": tx_flags,
    "int_ru_exit": tx_exit,
    "int_ru_dais": tx_dais,
    "int_ru_window_view": tx_window_view,
    "int_ru_books": tx_books,
    "int_ru_tv_hotel": tx_tv_hotel,
    "int_ru_pins": tx_pins,
}


def write_textures(out_dir=None, sheet=None):
    from PIL import Image
    out_dir = out_dir or stage_palette.TEXTURE_DIR
    os.makedirs(out_dir, exist_ok=True)
    written = []
    missing = [n for n in RU_MATERIALS if n not in TEXTURES]
    if missing:
        raise SystemExit(f"no texture recipe for {missing}")
    for i, (name, fn) in enumerate(TEXTURES.items()):
        t = fn(1000 + i * 7)
        want = RU_MATERIALS[name]["size"]
        if (t.w, t.h) != tuple(want):
            raise SystemExit(f"{name}: recipe makes {t.w}x{t.h}, palette says {want}")
        path = os.path.join(out_dir, name + ".png")
        im = t.image()
        if os.path.exists(path):
            try:
                old = Image.open(path).convert("RGBA")
                if old.size == im.size and old.tobytes() == im.tobytes():
                    written.append(path)
                    continue
            except Exception:  # noqa: BLE001
                pass
        im.save(path)
        written.append(path)
    if sheet:
        cols = 10
        cell = 136
        rows = (len(TEXTURES) + cols - 1) // cols
        from PIL import ImageDraw
        sh = Image.new("RGB", (cols * cell, rows * (cell + 14)), (36, 36, 40))
        d = ImageDraw.Draw(sh)
        for i, name in enumerate(TEXTURES):
            im = Image.open(os.path.join(out_dir, name + ".png")).convert("RGBA")
            k = 128 // max(im.size)
            im2 = im.resize((im.width * k * 2 if im.width < 64 and im.height < 64 and False else im.width * k,
                             im.height * k), Image.NEAREST)
            bg = Image.new("RGBA", im2.size, (90, 90, 96, 255))
            bg.alpha_composite(im2)
            x, y = (i % cols) * cell, (i // cols) * (cell + 14)
            sh.paste(bg.convert("RGB"), (x + 4, y + 4))
            d.text((x + 4, y + cell - 2), name[7:], fill=(230, 230, 230))
        sh.save(sheet)
    return written


# ================================================================== plan geometry (pure Python, map metres)
EPS = 1e-9


def signed_area(p):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def ccw(p):
    p = [(float(x), float(y)) for x, y in p]
    return p if signed_area(p) >= 0 else list(reversed(p))


def cw(p):
    return list(reversed(ccw(p)))


def bbox(p):
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return (min(xs), min(ys), max(xs), max(ys))


def centroid(p):
    a = signed_area(p)
    if abs(a) < 1e-9:
        return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))
    cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]):
        c = x1 * y2 - x2 * y1
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    return (cx / (6 * a), cy / (6 * a))


def pip(pt, poly):
    """Point in polygon (even-odd)."""
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xc:
                inside = not inside
        j = i
    return inside


def seg_point_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def poly_dist(pt, poly):
    return min(seg_point_dist(pt, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def edges(poly):
    return list(zip(poly, poly[1:] + poly[:1]))


def clean(poly, eps=0.02, collinear=0.004):
    """Drop repeated points (< eps apart) and points on a straight line (|sin| < collinear)."""
    p = []
    for q in poly:
        q = (float(q[0]), float(q[1]))
        if not p or math.dist(p[-1], q) > eps:
            p.append(q)
    if len(p) > 1 and math.dist(p[0], p[-1]) <= eps:
        p.pop()
    changed = True
    while changed and len(p) > 3:
        changed = False
        for i in range(len(p)):
            a, b, c = p[i - 1], p[i], p[(i + 1) % len(p)]
            l1, l2 = math.dist(a, b), math.dist(b, c)
            if l1 < eps or l2 < eps:
                p.pop(i)
                changed = True
                break
            cr = ((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) / (l1 * l2)
            dt = ((b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]))
            if abs(cr) < collinear and dt > 0:
                p.pop(i)
                changed = True
                break
    return p


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _in_tri(p, a, b, c):
    d1, d2, d3 = _cross(a, b, p), _cross(b, c, p), _cross(c, a, p)
    neg = (d1 < -1e-12) or (d2 < -1e-12) or (d3 < -1e-12)
    pos = (d1 > 1e-12) or (d2 > 1e-12) or (d3 > 1e-12)
    return not (neg and pos)


def earclip(poly):
    """Triangulate a simple polygon (any winding; may contain hole bridges = repeated points).
    -> [(a, b, c)] counter-clockwise point triples."""
    P = ccw(poly)
    n = len(P)
    if n < 3:
        return []
    idx = list(range(n))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 4 * n * n + 100:
        guard += 1
        m = len(idx)
        clipped = False
        for k in range(m):
            ia, ib, ic = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = P[ia], P[ib], P[ic]
            if _cross(a, b, c) <= 1e-10:
                continue
            ok = True
            for j in idx:
                if j in (ia, ib, ic):
                    continue
                q = P[j]
                if q == a or q == b or q == c:
                    continue
                if _in_tri(q, a, b, c):
                    ok = False
                    break
            if ok:
                tris.append((a, b, c))
                idx.pop(k)
                clipped = True
                break
        if not clipped:
            # degenerate (collinear or a self-touching bridge): drop the flattest vertex
            best, bk = None, 0
            for k in range(m):
                a, b, c = P[idx[k - 1]], P[idx[k]], P[idx[(k + 1) % m]]
                v = abs(_cross(a, b, c))
                if best is None or v < best:
                    best, bk = v, k
            idx.pop(bk)
    if len(idx) == 3:
        a, b, c = (P[i] for i in idx)
        if _cross(a, b, c) > 1e-10:
            tris.append((a, b, c))
    return tris


def _ray_hit(M, poly):
    """Nearest intersection of the +x ray from M with poly's edges: (x, edge index) or None."""
    best = None
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > M[1]) == (b[1] > M[1]):
            if abs(a[1] - M[1]) < 1e-12 and a[0] >= M[0]:
                if best is None or a[0] < best[0]:
                    best = (a[0], i)
            continue
        x = a[0] + (M[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        if x >= M[0] - 1e-12 and (best is None or x < best[0]):
            best = (x, i)
    return best


def bridge_holes(outer, holes):
    """One polygon (with zero-width bridges) from a CCW outer ring and holes inside it (Eberly)."""
    poly = ccw(outer)
    hs = [cw(h) for h in holes if len(h) >= 3]
    hs.sort(key=lambda h: -max(p[0] for p in h))
    for h in hs:
        mi = max(range(len(h)), key=lambda i: (h[i][0], -h[i][1]))
        M = h[mi]
        hit = _ray_hit(M, poly)
        if hit is None:
            continue
        xI, ei = hit
        a, b = poly[ei], poly[(ei + 1) % len(poly)]
        I = (xI, M[1])
        pi = ei if a[0] > b[0] else (ei + 1) % len(poly)
        P = poly[pi]
        if math.dist(I, a) < 1e-9:
            pi = ei
        elif math.dist(I, b) < 1e-9:
            pi = (ei + 1) % len(poly)
        else:
            # reflex vertices inside triangle M I P: take the one with the smallest angle to the ray
            cand = []
            for j, q in enumerate(poly):
                if j == pi:
                    continue
                pr, nx_ = poly[j - 1], poly[(j + 1) % len(poly)]
                if _cross(pr, q, nx_) < 0 and _in_tri(q, M, I, P) and q[0] >= M[0]:
                    ang = abs(math.atan2(q[1] - M[1], q[0] - M[0]))
                    cand.append((ang, math.dist(q, M), j))
            if cand:
                pi = min(cand)[2]
        P = poly[pi]
        ring = h[mi:] + h[:mi] + [h[mi]]
        poly = poly[:pi + 1] + ring + [P] + poly[pi + 1:]
    return poly


def triangulate(outer, holes=()):
    outer = clean(outer)
    holes = [clean(h) for h in holes]
    holes = [h for h in holes if len(h) >= 3]
    if len(outer) < 3:
        return []
    poly = bridge_holes(outer, holes) if holes else ccw(outer)
    return earclip(poly)


def clip_convex(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a CONVEX polygon by a rectangle -> convex polygon (may be empty)."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            ci, pv = inside(cur), inside(prev)
            if ci:
                if not pv:
                    out.append(inter(prev, cur))
                out.append(cur)
            elif pv:
                out.append(inter(prev, cur))
        return out

    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))

    def iy(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / (b[1] - a[1]), yv)
    pts = list(poly)
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            return []
        pts = clip(pts, inside, inter)
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-6:
        out.pop()
    return out if len(out) >= 3 and abs(signed_area(out)) > 1e-6 else []


def clip_halfplane(poly, a, b, keep_left=True):
    """Clip a convex polygon by the line a -> b, keeping the left (or right) side."""
    def side(p):
        v = _cross(a, b, p)
        return v if keep_left else -v
    out = []
    n = len(poly)
    for i in range(n):
        cur, prev = poly[i], poly[i - 1]
        sc, sp = side(cur), side(prev)
        if sc >= 0:
            if sp < 0:
                t = sp / (sp - sc)
                out.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
            out.append(cur)
        elif sp >= 0:
            t = sp / (sp - sc)
            out.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
    clean_ = []
    for q in out:
        if not clean_ or math.dist(q, clean_[-1]) > 1e-7:
            clean_.append(q)
    if len(clean_) > 1 and math.dist(clean_[0], clean_[-1]) < 1e-7:
        clean_.pop()
    return clean_ if len(clean_) >= 3 and abs(signed_area(clean_)) > 1e-7 else []


def convex_minus(piece, hole):
    """Convex piece minus a CONVEX hole -> disjoint convex pieces."""
    hole = ccw(hole)
    rest = ccw(piece)
    out = []
    for a, b in edges(hole):
        if not rest:
            break
        outside = clip_halfplane(rest, a, b, keep_left=False)
        if outside:
            out.append(outside)
        rest = clip_halfplane(rest, a, b, keep_left=True)
    return out


def rect_cover(polys, step, avoid=(), ox=0.0, oy=0.0):
    """Cells of the global `step` grid touched by polygons, merged into maximal rectangles; cells touching an
    `avoid` polygon are returned separately as exact convex pieces (polys clipped to the cell minus avoid, holes
    triangulated). -> (rects [(x0, y0, x1, y1)], pieces [convex polygons])."""
    tris = [list(t) for p in polys for t in triangulate(p)]
    cells = {}
    for tri in tris:
        x0, y0, x1, y1 = bbox(tri)
        for i in range(math.floor((x0 - ox) / step), math.ceil((x1 - ox) / step)):
            for j in range(math.floor((y0 - oy) / step), math.ceil((y1 - oy) / step)):
                pc = clip_convex(tri, ox + i * step, oy + j * step, ox + (i + 1) * step, oy + (j + 1) * step)
                if pc:
                    cells.setdefault((i, j), []).append(pc)
    av = [(bbox(a), a) for a in avoid]
    avoid_cvx = []
    for a in avoid:          # convex holes as they are, others as triangles
        a = ccw(a)
        convex = all(_cross(a[k - 1], a[k], a[(k + 1) % len(a)]) >= -1e-9 for k in range(len(a)))
        avoid_cvx.extend([a] if convex else [list(t) for t in triangulate(a)])
    exact, full = [], set()
    for (i, j), pcs in cells.items():
        cx0, cy0 = ox + i * step, oy + j * step
        cx1, cy1 = cx0 + step, cy0 + step
        touch = any(not (b[0] >= cx1 or b[2] <= cx0 or b[1] >= cy1 or b[3] <= cy0) for b, _ in av)
        if touch:
            # the whole cell (spilling past walls into closed rooms is harmless) minus the holes
            exact.extend(subtract([[(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1)]], avoid_cvx))
        else:
            full.add((i, j))
    rects = []
    done = set()
    for (i, j) in sorted(full, key=lambda k: (k[1], k[0])):
        if (i, j) in done:
            continue
        i2 = i
        while (i2 + 1, j) in full and (i2 + 1, j) not in done:
            i2 += 1
        j2 = j
        while all((ii, j2 + 1) in full and (ii, j2 + 1) not in done for ii in range(i, i2 + 1)):
            j2 += 1
        for ii in range(i, i2 + 1):
            for jj in range(j, j2 + 1):
                done.add((ii, jj))
        rects.append((ox + i * step, oy + j * step, ox + (i2 + 1) * step, oy + (j2 + 1) * step))
    return rects, exact


def subtract(pieces, holes):
    """Convex pieces minus convex holes (bounding boxes first)."""
    hb = [(bbox(h), h) for h in holes]
    out = []
    for pc in pieces:
        cur = [pc]
        b = bbox(pc)
        for (x0, y0, x1, y1), h in hb:
            if x0 >= b[2] or x1 <= b[0] or y0 >= b[3] or y1 <= b[1]:
                continue
            nxt = []
            for q in cur:
                nxt.extend(convex_minus(q, h))
            cur = nxt
        out.extend(cur)
    return out


def grid_pieces(tris, step, ox=0.0, oy=0.0):
    """Split triangles on a global grid (cell = step m, lines at ox + k step) -> convex CCW polygons, so the
    vertex-colour bake has samples every ~step metres."""
    out = []
    for tri in tris:
        x0, y0, x1, y1 = bbox(tri)
        i0, i1 = math.floor((x0 - ox) / step), math.ceil((x1 - ox) / step)
        j0, j1 = math.floor((y0 - oy) / step), math.ceil((y1 - oy) / step)
        if i1 - i0 <= 1 and j1 - j0 <= 1:
            out.append(list(tri))
            continue
        for i in range(i0, i1):
            for j in range(j0, j1):
                pc = clip_convex(list(tri), ox + i * step, oy + j * step, ox + (i + 1) * step, oy + (j + 1) * step)
                if pc:
                    out.append(ccw(pc))
    return out


def offset_poly(poly, d):
    """Offset a polygon outward by d (CCW in, mitred corners clamped to 3 d)."""
    poly = ccw(poly)
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        L = math.dist(a, b) or 1.0
        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
        lines.append(((a[0] + nx * d, a[1] + ny * d), (b[0] + nx * d, b[1] + ny * d)))
    out = []
    for i in range(n):
        (p1, p2), (p3, p4) = lines[i - 1], lines[i]
        d1 = (p2[0] - p1[0], p2[1] - p1[1])
        d2 = (p4[0] - p3[0], p4[1] - p3[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9:
            out.append(p3)
            continue
        t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
        q = (p1[0] + d1[0] * t, p1[1] + d1[1] * t)
        o = poly[i]
        if math.dist(q, o) > 3 * abs(d):
            k = 3 * abs(d) / math.dist(q, o)
            q = (o[0] + (q[0] - o[0]) * k, o[1] + (q[1] - o[1]) * k)
        out.append(q)
    return out


def convex_hull(pts):
    pts = sorted(set((round(p[0], 4), round(p[1], 4)) for p in pts))
    if len(pts) <= 2:
        return pts
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def shrink(poly, d):
    return offset_poly(poly, -d)


def resample_arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def polyline_len(pl):
    return sum(math.dist(a, b) for a, b in zip(pl, pl[1:]))


def along(pl, s):
    """Point + unit direction at distance s along a polyline."""
    acc = 0.0
    for a, b in zip(pl, pl[1:]):
        L = math.dist(a, b)
        if acc + L >= s or (a, b) == (pl[-2], pl[-1]):
            t = 0.0 if L < 1e-9 else max(0.0, min(1.0, (s - acc) / L))
            d = ((b[0] - a[0]) / (L or 1), (b[1] - a[1]) / (L or 1))
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), d
        acc += L
    return pl[-1], (1.0, 0.0)


# ================================================================== mesh helpers on KitMesh
def add_raw(km, pts, mat, normal_hint=None):
    """A collision polygon with a material the kit does not know (instant-warp floors): appended directly."""
    pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
    if normal_hint is not None and K._dot(K.newell(pts), normal_hint) < 0:
        pts.reverse()
    km.polys.append(K.Poly(pts, mat, None, [1.0] * len(pts), None, False))


def floor_poly(V, poly, z, mat, step=3.0, holes=(), tint=None, ao=1.0, down=False, uvs_fn=None, cut=()):
    """Visual floor (or ceiling with down=True) over a polygon, split on the global step grid; cut = convex holes
    subtracted exactly."""
    tris = triangulate(poly, holes)
    pcs = grid_pieces(tris, step)
    if cut:
        pcs = subtract(pcs, cut)
    for pc in pcs:
        pts = [(x, y, z) for x, y in (reversed(pc) if down else pc)]
        V.poly(pts, mat, ao=ao, tint=tint, uvs=uvs_fn(pts) if uvs_fn else None)


def col_floor(C, poly, z, mat=K.COL, holes=(), down=False, raw=False, cut=()):
    """Collision floor / ceiling polygon (triangulated, no grid); cut = convex holes subtracted exactly."""
    pcs = [list(t) for t in triangulate(poly, holes)]
    if cut:
        pcs = subtract(pcs, cut)
    for pc in pcs:
        pts = [(p[0], p[1], z) for p in ccw(pc)]
        if down:
            pts.reverse()
        if raw:
            add_raw(C, pts, mat)
        else:
            C.poly(pts, mat)


def quad_wall(V, a, b, z0, z1, mat, uvs=None, ao=None, tint=None, glow=False):
    """Vertical quad a -> b (2D), normal on the RIGHT of a -> b."""
    return V.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat, uvs=uvs, ao=ao,
                  tint=tint, glow=glow)


def panel(V, a, b, z0, z1, mat, off=0.0, glow=False, tint=None, u0=0.0, u1=1.0, v0=0.0, v1=1.0, ao=1.0):
    """A once-mapped panel on the wall line a -> b, facing RIGHT of a -> b, pushed off metres along that normal.
    The texture reads upright and unmirrored from the front."""
    L = math.dist(a, b)
    if L < 1e-6:
        return
    nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
    pa = (a[0] + nx * off, a[1] + ny * off)
    pb = (b[0] + nx * off, b[1] + ny * off)
    # walking a -> b with the normal on the right: a viewer facing the panel has a on the LEFT, b on the right
    V.poly([(pb[0], pb[1], z0), (pa[0], pa[1], z0), (pa[0], pa[1], z1), (pb[0], pb[1], z1)], mat,
           uvs=[(u1, v0), (u0, v0), (u0, v1), (u1, v1)], glow=glow, tint=tint, ao=ao, normal_hint=(nx, ny, 0.0))


def seg_box(V, a, b, half_t, z0, z1, mat, faces="sideends_top", mats=None, tint=None, ao=None):
    """Box around segment a-b (half thickness half_t), visual: the two long sides, the two ends, the top."""
    L = math.dist(a, b)
    if L < 1e-6:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = dy, -dx
    p0 = (a[0] + nx * half_t, a[1] + ny * half_t)
    p1 = (b[0] + nx * half_t, b[1] + ny * half_t)
    q0 = (a[0] - nx * half_t, a[1] - ny * half_t)
    q1 = (b[0] - nx * half_t, b[1] - ny * half_t)
    m = mats or {}
    if "side" in faces:
        quad_wall(V, p0, p1, z0, z1, m.get("r", mat), tint=tint, ao=ao)     # right side (normal +n)
        quad_wall(V, q1, q0, z0, z1, m.get("l", mat), tint=tint, ao=ao)     # left side
    if "ends" in faces:
        quad_wall(V, q0, p0, z0, z1, m.get("e", mat), tint=tint, ao=ao)
        quad_wall(V, p1, q1, z0, z1, m.get("e", mat), tint=tint, ao=ao)
    if "top" in faces:
        V.poly([(p0[0], p0[1], z1), (p1[0], p1[1], z1), (q1[0], q1[1], z1), (q0[0], q0[1], z1)], m.get("t", mat),
               normal_hint=(0, 0, 1), tint=tint, ao=ao)
    if "bot" in faces:
        V.poly([(p0[0], p0[1], z0), (q0[0], q0[1], z0), (q1[0], q1[1], z0), (p1[0], p1[1], z0)], m.get("b", mat),
               normal_hint=(0, 0, -1), tint=tint, ao=ao)


def col_seg(C, a, b, half_t, z0, z1, mat=K.COL, top=True, bottom=False):
    """Closed collision block around segment a-b."""
    L = math.dist(a, b)
    if L < 1e-4:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    foot = ccw([(a[0] + nx * half_t, a[1] + ny * half_t), (b[0] + nx * half_t, b[1] + ny * half_t),
                (b[0] - nx * half_t, b[1] - ny * half_t), (a[0] - nx * half_t, a[1] - ny * half_t)])
    C.prism(foot, z0, z1, mat, top=mat if top else None, bottom=mat if bottom else None)


def cyl(V, x, y, r, z0, z1, mat, n=8, top=True, bottom=False, tint=None, ao=None):
    pts = [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    for a, b in edges(pts):
        quad_wall(V, a, b, z0, z1, mat, tint=tint, ao=ao)
    if top:
        V.poly([(p[0], p[1], z1) for p in pts], mat, tint=tint)
    if bottom:
        V.poly([(p[0], p[1], z0) for p in reversed(pts)], mat, tint=tint)


def prism(V, foot, z0, z1, mat, top=None, bottom=None, tint=None, ao=None):
    foot = ccw(foot)
    for a, b in edges(foot):
        quad_wall(V, a, b, z0, z1, mat, tint=tint, ao=ao)
    if top:
        floor_poly(V, foot, z1, top, step=99.0, tint=tint)
    if bottom:
        floor_poly(V, foot, z0, bottom, step=99.0, down=True, tint=tint)


# ================================================================== props (local frame: front = +y, origin base centre)
def _p(kind, **info):
    return K.Prop(kind, **info)


def bowling_lane_set(n_lanes=14, lane_len=18.29, approach=4.6, pin_deck=0.9, pit=1.2, seed=0):
    """The Game Room's 14 lanes (ru_gr_lanes_overview_1/2, ru_gr_lane_screens, ru_gr_kosmic_lanes), local frame:
    x across the lanes (centred), y = 0 at the foul line, lanes run toward -y (the pins), approach toward +y.
    Per lane 1.066 m bed + 2 x 0.24 m gutters; a 0.15 m capping between lanes; Brunswick ball returns between
    pairs; white round columns between pairs; masking unit + video wall over the pit; overhead truss with
    score monitors above the foul line. Collision: one flat floor (lane beds are floor), the pin deck, the
    masking front (a wall), ball-return blocks, columns."""
    P = _p("bowling_lanes", n=n_lanes)
    V, C = P.visual, P.collision
    bed, gut, cap = 1.066, 0.235, 0.11
    pitch = bed + 2 * gut + cap
    W = n_lanes * pitch + cap
    x0 = -W / 2
    yp = -lane_len - pin_deck           # back of the pin deck
    ypit = yp - pit
    pins = [(0, 0)]
    for row in range(1, 4):
        for k in range(row + 1):
            pins.append(((k - row / 2) * 0.305, -row * 0.264))
    for i in range(n_lanes):
        lx = x0 + cap + i * pitch + gut + bed / 2
        # lane bed: lanes + arrows segment
        V.poly([(lx - bed / 2, -lane_len, 0.0), (lx + bed / 2, -lane_len, 0.0), (lx + bed / 2, -6.0, 0.0),
                (lx - bed / 2, -6.0, 0.0)], "int_ru_lane", ao=1.0)
        V.poly([(lx - bed / 2, -6.0, 0.0), (lx + bed / 2, -6.0, 0.0), (lx + bed / 2, -2.0, 0.0),
                (lx - bed / 2, -2.0, 0.0)], "int_ru_lane_arrows", uvs=K.uv_rect(0, 0, 1, 1), ao=1.0)
        V.poly([(lx - bed / 2, -2.0, 0.0), (lx + bed / 2, -2.0, 0.0), (lx + bed / 2, 0.0, 0.0),
                (lx - bed / 2, 0.0, 0.0)], "int_ru_lane", ao=1.0)
        # foul line
        V.poly([(lx - bed / 2, -0.02, 0.003), (lx + bed / 2, -0.02, 0.003), (lx + bed / 2, 0.02, 0.003),
                (lx - bed / 2, 0.02, 0.003)], "int_ru_black", ao=1.0)
        # gutters (dark channels, 6 cm deep)
        for gx in (lx - bed / 2 - gut, lx + bed / 2):
            V.poly([(gx, yp, -0.06), (gx + gut, yp, -0.06), (gx + gut, 0.0, -0.06), (gx, 0.0, -0.06)],
                   "int_ru_black", ao=0.8)
            quad_wall(V, (gx, 0.0), (gx, yp), -0.06, 0.0, "int_ru_black", ao=0.7)
            quad_wall(V, (gx + gut, yp), (gx + gut, 0.0), -0.06, 0.0, "int_ru_black", ao=0.7)
        # pin deck
        V.poly([(lx - bed / 2, yp, 0.0), (lx + bed / 2, yp, 0.0), (lx + bed / 2, -lane_len, 0.0),
                (lx - bed / 2, -lane_len, 0.0)], "int_ru_lane", ao=0.95)
        # pins: low-poly white prisms with red neck stripes (pin face texture)
        for px, py in pins:
            cx, cy = lx + px, -lane_len - 0.3 + py
            for k in range(4):
                a0, a1 = k * math.pi / 2 + math.pi / 4, (k + 1) * math.pi / 2 + math.pi / 4
                pa = (cx + 0.06 * math.cos(a0), cy + 0.06 * math.sin(a0))
                pb = (cx + 0.06 * math.cos(a1), cy + 0.06 * math.sin(a1))
                quad_wall(V, pa, pb, 0.0, 0.38, "int_ru_pins", uvs=K.uv_rect(0, 0, 0.25, 1), ao=1.0)
        # dark pit + the lane's lit hood glow
        V.poly([(lx - bed / 2 - gut, ypit, -0.3), (lx + bed / 2 + gut, ypit, -0.3), (lx + bed / 2 + gut, yp, -0.3),
                (lx - bed / 2 - gut, yp, -0.3)], "int_ru_black", ao=0.4)
    # cappings between lanes + outer kickbacks (low black strips)
    for i in range(n_lanes + 1):
        cx0 = x0 + i * pitch
        V.box(cx0, yp, 0.0, cx0 + cap, 0.0, 0.05, "int_ru_black", faces="+x-x+z")
        if i in (0, n_lanes):
            V.box(cx0, yp, 0.0, cx0 + cap, -lane_len + 1.0, 1.1, "int_ru_wall_navy", faces="+x-x+z")
    # pin-deck front of the pit wall and the masking units (one long fascia across all lanes) + video wall
    V.box(x0, ypit - 0.3, -0.3, x0 + W, ypit, 1.4, "int_ru_black", faces="+y")
    zm0, zm1 = 1.25, 2.6
    V.poly([(x0 + W, yp + 0.2, zm0), (x0, yp + 0.2, zm0), (x0, yp + 0.2, zm1), (x0 + W, yp + 0.2, zm1)],
           "int_ru_masking", uvs=[(0, 0), (W / 4.0, 0), (W / 4.0, 1), (0, 1)], normal_hint=(0, 1, 0), ao=1.0)
    V.poly([(x0, yp + 0.2, zm0), (x0 + W, yp + 0.2, zm0), (x0 + W, yp - 0.6, zm0), (x0, yp - 0.6, zm0)],
           "int_ru_black", normal_hint=(0, 0, -1), ao=0.6)
    # video wall above the masking (ru_gr_lane_screens): 4 big screens
    nscr = 4
    sw = W / nscr
    for k in range(nscr):
        sx0 = x0 + k * sw + 0.2
        V.poly([(sx0 + sw - 0.4, yp + 0.25, zm1 + 0.15), (sx0, yp + 0.25, zm1 + 0.15), (sx0, yp + 0.25, zm1 + 2.35),
                (sx0 + sw - 0.4, yp + 0.25, zm1 + 2.35)], "int_ru_video_wall", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)],
               glow=True, normal_hint=(0, 1, 0))
    V.poly([(x0 + W, yp + 0.2, zm1), (x0, yp + 0.2, zm1), (x0, yp + 0.2, zm1 + 2.6), (x0 + W, yp + 0.2, zm1 + 2.6)],
           "int_ru_black", normal_hint=(0, 1, 0), ao=0.9)
    # collision: masking front wall above the pins (Mario can walk to the pins), pit floor
    C.wall((x0 + W, yp + 0.2), (x0, yp + 0.2), -0.3, zm1 + 3.0, K.COL)
    # ball returns between pairs (ru_gr_lanes_overview_1): black hump + hood, on the approach
    for p in range(n_lanes // 2):
        bx = x0 + cap + (2 * p + 1) * pitch - cap / 2
        V.box(bx - 0.28, 0.6, 0.0, bx + 0.28, 2.4, 0.45, "int_ru_black", faces="+x-x+y-y+z")
        V.box(bx - 0.36, 0.5, 0.0, bx + 0.36, 1.2, 0.95, "int_ru_black", faces="+x-x+y-y+z")
        V.box(bx - 0.30, 1.0, 0.95, bx + 0.30, 1.15, 1.05, "int_ru_red", faces="+x-x+y-y+z")
        K.col_box(C, bx - 0.36, 0.5, 0.0, bx + 0.36, 2.4, 0.95, K.COL_NOCAM)
        # balls on the rack
        for k, col in enumerate(("int_ru_uf_blue", "int_ru_red", "int_ru_orange", "int_ru_gator_green")):
            V.box(bx - 0.11 + (0.0 if k % 2 else 0.0), 1.35 + 0.24 * k, 0.45, bx + 0.11, 1.57 + 0.24 * k, 0.67, col,
                  faces="+x-x+y-y+z")
        # scorer pedestal (tablet on a post)
        V.box(bx - 0.05, 2.9, 0.0, bx + 0.05, 3.0, 1.05, "int_ru_black", faces="+x-x+y-y")
        V.poly([(bx - 0.18, 2.86, 1.05), (bx + 0.18, 2.86, 1.05), (bx + 0.18, 2.98, 1.30), (bx - 0.18, 2.98, 1.30)],
               "int_ru_score_tv", uvs=K.ONCE, glow=True, normal_hint=(0, 1, 1))
        # square white column between the pairs, behind the approach (ru_gr_lanes_overview_2)
        V.box(bx - 0.3, 3.3, 0.0, bx + 0.3, 3.9, 6.0, "int_ru_white", faces="+x-x+y-y")
        K.col_box(C, bx - 0.3, 3.3, 0.0, bx + 0.3, 3.9, 5.4, K.COL)
    # overhead truss with monitors over the foul line (ru_gr_lanes_truss)
    zt = 4.3
    for yy in (0.4, 1.1):
        V.box(x0, yy - 0.06, zt, x0 + W, yy + 0.06, zt + 0.12, "int_ru_black", faces="+y-y-z+z")
    for k in range(int(W / 1.2)):
        xx = x0 + 0.6 + k * 1.2
        V.box(xx - 0.03, 0.4, zt, xx + 0.03, 1.1, zt + 0.06, "int_ru_black", faces="-z+z")
    for i in range(n_lanes // 2):
        mx = x0 + cap + (2 * i + 1) * pitch - cap / 2
        # big score monitors (ru_gr_lanes_crowd_tvs): ~1.9 m wide, both faces
        V.box(mx - 1.0, 0.70, zt - 1.2, mx + 1.0, 0.80, zt - 0.05, "int_ru_black", faces="+y-y+x-x-z")
        V.poly([(mx - 0.95, 0.81, zt - 1.15), (mx + 0.95, 0.81, zt - 1.15), (mx + 0.95, 0.81, zt - 0.1),
                (mx - 0.95, 0.81, zt - 0.1)], "int_ru_score_tv", uvs=K.uv_rect(1, 0, 0, 1), glow=True,
               normal_hint=(0, 1, 0))
        V.poly([(mx + 0.95, 0.69, zt - 1.15), (mx - 0.95, 0.69, zt - 1.15), (mx - 0.95, 0.69, zt - 0.1),
                (mx + 0.95, 0.69, zt - 0.1)], "int_ru_score_tv", uvs=K.uv_rect(1, 0, 0, 1), glow=True,
               normal_hint=(0, -1, 0))
    P.info.update(width=W, pitch=pitch, pin_y=-lane_len - 0.3, back_y=ypit, lanes_x0=x0)
    for i in range(n_lanes):
        P.anchor(f"lane_{i + 1}_foul", x0 + cap + i * pitch + gut + bed / 2, 0.0, 0.0, 180.0)
        P.anchor(f"lane_{i + 1}_pins", x0 + cap + i * pitch + gut + bed / 2, -lane_len - 0.3, 0.0, 0.0)
    return P


def booth(length=3.0, depth=0.8, seat_h=0.45, back_h=1.1, curve=True, mat="int_ru_leather_navy", table=True):
    """Navy curved lounge booth (ru_gr_booth_row, ru_gr_booths_bowler): a C-shaped bench with a low back and a
    round low table; front = +y."""
    P = _p("booth")
    V, C = P.visual, P.collision
    n = 7 if curve else 1
    R = length / 2
    pts_in, pts_out = [], []
    for k in range(n + 1):
        a = math.pi + math.pi * k / n if curve else 0
        if curve:
            pts_out.append((R * math.cos(a), 0.6 + R * 0.55 * math.sin(a) * 0.9 + 0.0))
            pts_in.append(((R - depth) * math.cos(a), 0.6 + (R - depth) * 0.55 * math.sin(a) * 0.9))
    if not curve:
        pts_out = [(-R, 0.0), (R, 0.0)]
        pts_in = [(-R, depth), (R, depth)]
    for (a, b), (c, d) in zip(zip(pts_out, pts_out[1:]), zip(pts_in, pts_in[1:])):
        # seat top
        V.poly([(a[0], a[1], seat_h), (b[0], b[1], seat_h), (d[0], d[1], seat_h), (c[0], c[1], seat_h)], mat,
               normal_hint=(0, 0, 1))
        quad_wall(V, d, c, 0.0, seat_h, "int_ru_black")                 # seat front (dark base)
        # back: outer edge, thin
        quad_wall(V, b, a, seat_h, back_h, mat)                         # back face toward the seat
        quad_wall(V, a, b, 0.12, back_h, mat)                           # outside (navy, ru_gr_lanes_overview_2)
        quad_wall(V, a, b, 0.0, 0.12, "int_ru_black")
        V.poly([(a[0], a[1], back_h), (b[0], b[1], back_h), (b[0] + (d[0] - b[0]) * 0.18, b[1] + (d[1] - b[1]) * 0.18,
                back_h), (a[0] + (c[0] - a[0]) * 0.18, a[1] + (c[1] - a[1]) * 0.18, back_h)], mat,
               normal_hint=(0, 0, 1))
    xs = [p[0] for p in pts_out + pts_in]
    ys = [p[1] for p in pts_out + pts_in]
    K.col_box(C, min(xs), min(ys), 0.0, max(xs), max(ys), seat_h, K.COL_NOCAM)
    if table:
        ty = 0.6 + 0.2 if curve else depth + 0.7
        cyl(V, 0.0, ty, 0.45, 0.38, 0.44, "int_ru_leather_grey", n=8)
        cyl(V, 0.0, ty, 0.12, 0.0, 0.38, "int_ru_black", n=6, top=False)
    P.info["top_z"] = seat_h
    return P


def ball_rack(L=1.2):
    """Black ball rack with two shelves of coloured house balls (ru_gr_ball_rack, ru_gr_lanes_overview_2)."""
    P = _p("ball_rack")
    V, C = P.visual, P.collision
    V.box(-0.25, -L / 2, 0.0, 0.25, L / 2, 0.9, "int_ru_black", faces="+x-x+y-y+z")
    cols = ("int_ru_red", "int_ru_uf_blue", "int_ru_orange", "int_ru_gator_green", "int_ru_white")
    for shelf, zb in enumerate((0.42, 0.9)):
        for k in range(4):
            y = -L / 2 + 0.18 + k * (L - 0.36) / 3
            V.box(-0.11, y - 0.11, zb, 0.11, y + 0.11, zb + 0.22, cols[(k + shelf * 2) % len(cols)], faces="+x-x+y-y+z")
    K.col_box(C, -0.25, -L / 2, 0.0, 0.25, L / 2, 0.9, K.COL_NOCAM)
    return P


def cue_rack():
    """Wall cue rack (ru_gr_billiards_room): a row of pale cue sticks on a wood rail."""
    P = _p("cue_rack")
    V = P.visual
    V.box(-0.45, 0.0, 1.30, 0.45, 0.06, 1.38, "int_ru_wood_panel", faces="+x-x+y+z")
    for k in range(9):
        x = -0.4 + k * 0.1
        V.box(x - 0.012, 0.03, 0.15, x + 0.012, 0.06, 1.55, "int_wood", faces="+y+x-x")
    return P


def billiard_table(L=2.84, W=1.57, h=0.79):
    """9-ft table (ru_gr_billiards_room): blue felt, brown rails, heavy legs; long axis = local x."""
    P = _p("billiards")
    V, C = P.visual, P.collision
    rw = 0.16
    V.box(-L / 2 + rw, -W / 2 + rw, h - 0.02, L / 2 - rw, W / 2 - rw, h, "int_ru_felt", faces="+z")
    for (x0, y0, x1, y1) in ((-L / 2, -W / 2, L / 2, -W / 2 + rw), (-L / 2, W / 2 - rw, L / 2, W / 2),
                             (-L / 2, -W / 2 + rw, -L / 2 + rw, W / 2 - rw), (L / 2 - rw, -W / 2 + rw, L / 2, W / 2 - rw)):
        V.box(x0, y0, h - 0.12, x1, y1, h + 0.04, "int_ru_cherry", faces="+x-x+y-y+z")
    V.box(-L / 2 + 0.1, -W / 2 + 0.1, h - 0.32, L / 2 - 0.1, W / 2 - 0.1, h - 0.12, "int_ru_cherry",
          faces="+x-x+y-y-z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * L * 0.38 - 0.11, sy * W * 0.3 - 0.11, 0.0, sx * L * 0.38 + 0.11, sy * W * 0.3 + 0.11, h - 0.32,
                  "int_ru_cherry", faces="+x-x+y-y")
    # balls (a triangle rack + cue ball)
    for k, (bx, by) in enumerate([(0.6, 0), (0.66, 0.035), (0.66, -0.035), (0.72, 0.07), (0.72, 0), (0.72, -0.07),
                                  (-0.6, 0.0)]):
        col = ["int_ru_orange", "int_ru_uf_blue", "int_ru_red", "int_ru_gator_green", "int_ru_black",
               "int_ru_orange", "int_ru_white"][k]
        V.box(bx - 0.028, by - 0.028, h, bx + 0.028, by + 0.028, h + 0.056, col, faces="+x-x+y-y+z")
    K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h + 0.04, K.COL_NOCAM)
    P.info["top_z"] = h + 0.04
    return P


def led_frame(w, d, z, t=0.08):
    """Square LED ring light frame over a billiards table (ru_gr_billiards_room): white glowing bar."""
    P = _p("led_frame")
    V = P.visual
    for (x0, y0, x1, y1) in ((-w / 2, -d / 2, w / 2, -d / 2 + t), (-w / 2, d / 2 - t, w / 2, d / 2),
                             (-w / 2, -d / 2, -w / 2 + t, d / 2), (w / 2 - t, -d / 2, w / 2, d / 2)):
        V.box(x0, y0, z - 0.06, x1, y1, z, "int_ru_led", faces="-z+x-x+y-y", glow=True)
    P.lights.append(K.Light((0.0, 0.0, z - 0.3), radius=4.0, strength=0.30, color=(0.96, 0.98, 1.0)))
    return P


def arcade_cabinet():
    P = _p("arcade")
    V, C = P.visual, P.collision
    w, d, h = 0.72, 0.85, 1.85
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_ru_black", faces="+y-y+z")
    for sx in (-1, 1):
        x = sx * w / 2
        pts = [(x, -d / 2, 0.0), (x, d / 2, 0.0), (x, d / 2, h), (x, -d / 2, h)]
        if sx < 0:
            pts = list(reversed(pts))
        V.poly(pts, "int_ru_arcade", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if sx > 0 else [(1, 1), (1, 0), (0, 0), (0, 1)][::-1],
               normal_hint=(sx, 0, 0))
    V.poly([(-w / 2 + 0.06, d / 2 + 0.01, 1.05), (w / 2 - 0.06, d / 2 + 0.01, 1.05), (w / 2 - 0.06, d / 2 - 0.12, 1.55),
            (-w / 2 + 0.06, d / 2 - 0.12, 1.55)], "int_ru_game_screen", uvs=K.uv_rect(1, 0, 0, 1), glow=True,
           normal_hint=(0, 1, 0.3))
    V.box(-w / 2, d / 2, 0.85, w / 2, d / 2 + 0.25, 0.95, "int_ru_black", faces="+y+z+x-x")
    V.poly([(-w / 2 + 0.04, d / 2 + 0.02, 1.62), (w / 2 - 0.04, d / 2 + 0.02, 1.62), (w / 2 - 0.04, d / 2 + 0.02, 1.80),
            (-w / 2 + 0.04, d / 2 + 0.02, 1.80)], "int_ru_led", glow=True, tint=(1.0, 0.85, 0.4))
    K.col_box(C, -w / 2, -d / 2, 0.0, w / 2, d / 2 + 0.25, h, K.COL_NOCAM)
    return P


def ping_pong():
    P = _p("ping_pong")
    V, C = P.visual, P.collision
    L, W, h = 2.74, 1.525, 0.76
    V.box(-W / 2, -L / 2, h - 0.04, W / 2, L / 2, h, "int_ru_uf_blue", faces="+x-x+y-y+z")
    V.box(-0.01, -L / 2, h, 0.01, L / 2, h, "int_ru_white", faces="+z")
    V.box(-W / 2 - 0.05, -0.01, h, W / 2 + 0.05, 0.01, h + 0.15, "int_ru_white", faces="+y-y")
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * W * 0.4 - 0.03, sy * L * 0.4 - 0.03, 0.0, sx * W * 0.4 + 0.03, sy * L * 0.4 + 0.03, h - 0.04,
                  "int_ru_steel", faces="+x-x+y-y")
    K.col_box(C, -W / 2, -L / 2, 0.0, W / 2, L / 2, h, K.COL_NOCAM)
    return P


def air_hockey():
    P = _p("air_hockey")
    V, C = P.visual, P.collision
    L, W, h = 2.3, 1.2, 0.8
    V.box(-W / 2, -L / 2, 0.0, W / 2, L / 2, h, "int_ru_black", faces="+x-x+y-y")
    V.box(-W / 2 + 0.08, -L / 2 + 0.08, h - 0.02, W / 2 - 0.08, L / 2 - 0.08, h, "int_ru_uf_blue", faces="+z")
    V.box(-0.01, -L / 2 + 0.08, h, 0.01, L / 2 - 0.08, h, "int_ru_white", faces="+z")
    K.col_box(C, -W / 2, -L / 2, 0.0, W / 2, L / 2, h, K.COL_NOCAM)
    return P


def foosball():
    P = _p("foosball")
    V, C = P.visual, P.collision
    L, W, h = 1.4, 0.75, 0.9
    V.box(-L / 2, -W / 2, 0.55, L / 2, W / 2, h, "int_ru_white", faces="+x-x+y-y")
    V.box(-L / 2 + 0.05, -W / 2 + 0.05, 0.6, L / 2 - 0.05, W / 2 - 0.05, 0.62, "int_ru_gator_green", faces="+z")
    for k in range(8):
        x = -L / 2 + 0.15 + k * (L - 0.3) / 7
        V.box(x - 0.012, -W / 2 - 0.15, 0.82, x + 0.012, W / 2 + 0.15, 0.845, "int_ru_steel", faces="+z+y-y")
        V.box(x - 0.03, -0.1, 0.66, x + 0.03, 0.1, 0.82, "int_ru_orange" if k % 2 else "int_ru_uf_blue",
              faces="+x-x+y-y")
    for sx in (-1, 1):
        V.box(sx * L * 0.42 - 0.05, -W * 0.4, 0.0, sx * L * 0.42 + 0.05, W * 0.4, 0.55, "int_ru_black", faces="+x-x+y-y")
    K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def esports_row(n=6, seat_w=0.95, depth=0.75, h=0.75, double=True):
    """Gator Esports Center PC row (ru_es_oelrich_9050/9352, ru_es_pods): black desks with blue edge light,
    monitor per seat, black gaming chairs; double = back to back with a centre screen divider."""
    P = _p("esports_row", n=n)
    V, C = P.visual, P.collision
    L = n * seat_w
    sides = (1, -1) if double else (1,)
    for s in sides:
        y0, y1 = (0.05, depth) if s > 0 else (-depth, -0.05)
        V.box(-L / 2, y0, h - 0.04, L / 2, y1, h, "int_ru_black", faces="+z+x-x" + ("+y" if s > 0 else "-y"))
        ye = y1 if s > 0 else y0
        V.box(-L / 2, ye - 0.01, h - 0.06, L / 2, ye + 0.01, h - 0.02, "int_ru_led", faces="+y" if s > 0 else "-y",
              glow=True, tint=(0.35, 0.55, 1.0))
        V.box(-L / 2, min(y0, y1) + 0.1, 0.0, -L / 2 + 0.04, max(y0, y1) - 0.1, h - 0.04, "int_ru_black", faces="+x-x")
        V.box(L / 2 - 0.04, min(y0, y1) + 0.1, 0.0, L / 2, max(y0, y1) - 0.1, h - 0.04, "int_ru_black", faces="+x-x")
        for k in range(n):
            x = -L / 2 + seat_w * (k + 0.5)
            yy = 0.22 if s > 0 else -0.22
            # monitor facing the seat
            mpts = [(x - 0.32, yy, h + 0.12), (x + 0.32, yy, h + 0.12), (x + 0.32, yy, h + 0.52), (x - 0.32, yy, h + 0.52)]
            if s < 0:
                mpts = [mpts[1], mpts[0], mpts[3], mpts[2]]
            V.poly(mpts, "int_ru_game_screen", uvs=K.uv_rect(0, 0, 1, 1), glow=True, normal_hint=(0, s, 0))
            V.box(x - 0.34, yy - 0.04 * s if s > 0 else yy, h + 0.10, x + 0.34, yy if s > 0 else yy + 0.04, h + 0.54,
                  "int_ru_black", faces="-y" if s > 0 else "+y")
            # chair
            cy = (depth + 0.45) * s
            V.box(x - 0.26, cy - 0.25, 0.42, x + 0.26, cy + 0.25, 0.50, "int_ru_black", faces="+z+x-x+y-y")
            by = cy + 0.25 * s
            V.box(x - 0.24, min(by, by + 0.08 * s), 0.5, x + 0.24, max(by, by + 0.08 * s), 1.25, "int_ru_black",
                  faces="+x-x+y-y+z")
            V.box(x - 0.18, by + (0.081 * s if s > 0 else -0.001), 0.95, x + 0.18,
                  by + (0.082 * s if s > 0 else 0.0) + (0.0 if s > 0 else 0.0), 1.15, "int_ru_red", faces="+y" if s > 0 else "-y")
            V.box(x - 0.03, cy - 0.03, 0.0, x + 0.03, cy + 0.03, 0.42, "int_ru_steel", faces="+x-x+y-y")
    if double:
        V.box(-L / 2, -0.05, 0.0, L / 2, 0.05, h + 0.6, "int_ru_black", faces="+x-x+y-y+z")
    K.col_box(C, -L / 2, -depth if double else 0.05, 0.0, L / 2, depth, h, K.COL_NOCAM)
    return P


def lounge_chair(mat="int_ru_fabric_navy", seat="int_ru_fabric_taupe", w=0.85, d=0.85, swivel=False, col=True):
    """Atrium club chair (ru_atrium_enr_lounge): navy shell / taupe cushion, or the orange swivel tub chair."""
    P = _p("lounge_chair")
    V, C = P.visual, P.collision
    if swivel:
        cyl(V, 0.0, 0.0, 0.42, 0.25, 0.48, mat, n=8)
        pts = [(0.44 * math.cos(math.radians(a)), 0.44 * math.sin(math.radians(a))) for a in range(200, 341, 28)]
        for a, b in zip(pts, pts[1:]):
            quad_wall(V, b, a, 0.48, 0.85, mat)
            quad_wall(V, a, b, 0.25, 0.85, mat)
        cyl(V, 0.0, 0.0, 0.08, 0.0, 0.25, "int_ru_steel", n=6, top=False)
        if col:
            K.col_box(C, -0.42, -0.42, 0.0, 0.42, 0.42, 0.48, K.COL_NOCAM)
        return P
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, 0.42, mat, faces="+x-x+y-y")
    V.box(-w / 2 + 0.16, -d / 2 + 0.2, 0.42, w / 2 - 0.16, d / 2, 0.48, seat, faces="+z+y")
    V.box(-w / 2, -d / 2, 0.42, w / 2, -d / 2 + 0.2, 0.82, mat, faces="+x-x+y-y+z")
    for sx in (-1, 1):
        V.box(sx * w / 2 - (0.16 if sx > 0 else 0), -d / 2 + 0.2, 0.42, sx * w / 2 + (0 if sx > 0 else 0.16), d / 2,
              0.64, mat, faces="+x-x+y+z")
    if col:
        K.col_box(C, -w / 2, -d / 2, 0.0, w / 2, d / 2, 0.48, K.COL_NOCAM)
    P.info["top_z"] = 0.48
    return P


def coffee_table(L=1.2, W=0.7, h=0.42, mat="int_ru_fabric_taupe", col=True):
    P = _p("coffee_table")
    V, C = P.visual, P.collision
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, h, mat, faces="+x-x+y-y+z", mats={"+z": "int_ru_leather_grey"})
    if col:
        K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def round_table(r=0.9, h=0.75, top="int_ru_tablecloth", chairs=8, chair_mat="int_ru_fabric_navy", seats=True):
    """Banquet round table (ru_os_grand_ballroom_3/4, ru_os_matthews_1) with chairs around it."""
    P = _p("round_table")
    V, C = P.visual, P.collision
    cyl(V, 0.0, 0.0, r, h - 0.3, h, top, n=10)
    cyl(V, 0.0, 0.0, r * 0.95, 0.0, h - 0.3, top, n=10, top=False)
    if seats:
        for k in range(chairs):
            a = 2 * math.pi * k / chairs
            cx, cy = (r + 0.4) * math.cos(a), (r + 0.4) * math.sin(a)
            fx, fy = -math.cos(a), -math.sin(a)
            tx, ty = -fy, fx
            s = [(cx + tx * 0.22 - fx * 0.22, cy + ty * 0.22 - fy * 0.22), (cx - tx * 0.22 - fx * 0.22, cy - ty * 0.22 - fy * 0.22),
                 (cx - tx * 0.22 + fx * 0.22, cy - ty * 0.22 + fy * 0.22), (cx + tx * 0.22 + fx * 0.22, cy + ty * 0.22 + fy * 0.22)]
            V.poly([(p[0], p[1], 0.46) for p in s], chair_mat, normal_hint=(0, 0, 1))
            b0, b1 = s[0], s[1]
            quad_wall(V, b1, b0, 0.0, 0.46, "int_ru_black")
            # back panel (both faces)
            V.poly([(b0[0], b0[1], 0.46), (b1[0], b1[1], 0.46), (b1[0], b1[1], 1.0), (b0[0], b0[1], 1.0)], chair_mat,
                   normal_hint=(-fx, -fy, 0))
            V.poly([(b1[0], b1[1], 0.46), (b0[0], b0[1], 0.46), (b0[0], b0[1], 1.0), (b1[0], b1[1], 1.0)], chair_mat,
                   normal_hint=(fx, fy, 0))
    K.col_box(C, -r, -r, 0.0, r, r, h, K.COL_NOCAM)
    P.info["top_z"] = h
    return P


def chair_rows(rows, per_row, pitch=0.95, seat_w=0.5, aisle_every=0, aisle_w=1.2, kind="navy", seat_h=0.46):
    """Theatre-style chair rows (ballrooms, meeting rooms): each row = a seat strip + a cut-out back panel of
    chairs (int_ru_row_*: 4 chairs per texture repeat). Local: rows go toward -y (row 0 at y = 0, facing +y),
    centred in x. Collision: one low box per row block (no-cam)."""
    P = _p("chair_rows", rows=rows, per_row=per_row)
    V, C = P.visual, P.collision
    mat = {"navy": "int_ru_row_navy", "black": "int_ru_row_black", "aud": "int_ru_row_aud",
           "wood": "int_ru_row_wood"}[kind]
    # the auditorium's seats have honey-wood shells: seen from behind they read as wood (ru_os_auditorium_3)
    rear = "int_ru_row_wood" if kind == "aud" else mat
    seat_mat = {"navy": "int_ru_fabric_navy", "black": "int_ru_black", "aud": "int_ru_fabric_navy",
                "wood": "int_ru_fabric_navy"}[kind]
    blocks = []
    if aisle_every:
        n_blocks = int(math.ceil(per_row / aisle_every))
        for b in range(n_blocks):
            blocks.append(min(aisle_every, per_row - b * aisle_every))
    else:
        blocks = [per_row]
    W = sum(blocks) * seat_w + (len(blocks) - 1) * aisle_w
    for r in range(rows):
        y = -r * pitch
        x = -W / 2
        for nb in blocks:
            w = nb * seat_w
            # seat strip
            V.box(x, y - 0.45, seat_h - 0.06, x + w, y, seat_h, seat_mat, faces="+z+y")
            # back panel at the rear edge (seen from the back: rear face; from the front: the front face)
            yb = y - 0.45
            V.poly([(x, yb, 0.0), (x + w, yb, 0.0), (x + w, yb, 1.0), (x, yb, 1.0)], rear,
                   uvs=[(0, 0), (nb / 4.0, 0), (nb / 4.0, 1), (0, 1)], normal_hint=(0, -1, 0))
            V.poly([(x + w, yb + 0.02, 0.0), (x, yb + 0.02, 0.0), (x, yb + 0.02, 1.0), (x + w, yb + 0.02, 1.0)], mat,
                   uvs=[(0, 0), (nb / 4.0, 0), (nb / 4.0, 1), (0, 1)], normal_hint=(0, 1, 0))
            x += w + aisle_w
    K.col_box(C, -W / 2, -(rows - 1) * pitch - 0.45, 0.0, W / 2, 0.0, seat_h, K.COL_NOCAM)
    P.info.update(width=W, depth=(rows - 1) * pitch + 0.45)
    return P


def draped_table(L=1.8, W=0.75, h=0.76, mat="int_ru_tablecloth"):
    P = _p("draped_table")
    V, C = P.visual, P.collision
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, h, mat, faces="+x-x+y-y+z")
    return P


def folding_table(L=1.8, W=0.6, h=0.74, top="int_ru_wall_cream", chairs=3):
    """Classroom training table (ru_os_g325, ru_os_3305): light top, chrome legs, black chairs behind."""
    P = _p("folding_table")
    V, C = P.visual, P.collision
    V.box(-L / 2, -W / 2, h - 0.04, L / 2, W / 2, h, top, faces="+x-x+y-y+z")
    for sx in (-1, 1):
        V.box(sx * (L / 2 - 0.08) - 0.025, -W / 2 + 0.05, 0.0, sx * (L / 2 - 0.08) + 0.025, W / 2 - 0.05, h - 0.04,
              "int_ru_steel", faces="+x-x")
    for k in range(chairs):
        x = -L / 2 + L * (k + 0.5) / chairs
        V.box(x - 0.23, -W / 2 - 0.55, 0.42, x + 0.23, -W / 2 - 0.1, 0.47, "int_ru_black", faces="+z+y-y+x-x")
        V.box(x - 0.22, -W / 2 - 0.6, 0.47, x + 0.22, -W / 2 - 0.54, 0.95, "int_ru_black", faces="+x-x+y-y+z")
    K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def uf_letters(height=2.6, depth=0.7, base=True):
    """The giant orange UF letters of the atrium (ru_atrium_uf_letters_flickr / _wall): block letters you can sit
    in; a UF-blue plinth. Local: letters stand on y = 0, front = +y, centred in x."""
    P = _p("uf_letters")
    V, C = P.visual, P.collision
    s = height / 7.0      # one letter cell unit (the 5 x 7 grid)
    U = ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."]
    F = ["#####", "#....", "#....", "####.", "#....", "#....", "#...."]
    z0 = 0.35 if base else 0.0
    total_w = (5 + 1.4 + 5) * s
    # text reads from the prop's +x side (a viewer facing the front has the prop's right-hand side on their left)
    for li, g in enumerate((U, F)):
        ox = total_w / 2 - li * (6.4 * s)
        for gy, row in enumerate(g):
            for gx, c in enumerate(row):
                if c != "#":
                    continue
                x0, x1 = ox - (gx + 1) * s, ox - gx * s
                za, zb = z0 + (6 - gy) * s, z0 + (7 - gy) * s
                V.box(x0, -depth / 2, za, x1, depth / 2, zb, "int_ru_orange", faces="+x-x+y-y+z-z")
        # collision per letter: stems as boxes (simple, generous)
    if base:
        V.box(-total_w / 2 - 0.4, -depth / 2 - 0.25, 0.0, total_w / 2 + 0.4, depth / 2 + 0.25, z0, "int_ru_uf_blue",
              faces="+x-x+y-y+z")
    K.col_box(C, -total_w / 2 - 0.4, -depth / 2 - 0.25, 0.0, total_w / 2 + 0.4, depth / 2 + 0.25, z0 + 0.1,
              K.COL_NOCAM)
    # U stems + bottom, F stem + arms (walkable tops: the letters are a climbable sculpture)
    ox = total_w / 2
    for (x0, x1, za, zb) in ((ox - s, ox, z0 + s, z0 + 7 * s), (ox - 5 * s, ox - 4 * s, z0 + s, z0 + 7 * s),
                             (ox - 4 * s, ox - s, z0, z0 + s)):
        K.col_box(C, x0, -depth / 2, za if za > z0 + 0.01 else z0, x1, depth / 2, zb, K.COL_NOCAM, bottom=True)
    ox2 = ox - 6.4 * s
    for (x0, x1, za, zb) in ((ox2 - s, ox2, z0, z0 + 7 * s), (ox2 - 5 * s, ox2 - s, z0 + 6 * s, z0 + 7 * s),
                             (ox2 - 4 * s, ox2 - s, z0 + 3 * s, z0 + 4 * s)):
        K.col_box(C, x0, -depth / 2, za, x1, depth / 2, zb, K.COL_NOCAM, bottom=za > 0.01)
    P.anchor("u_stem_top", ox - s / 2, 0.0, z0 + 7 * s, 0.0)
    P.info.update(width=total_w + 0.8, top_z=z0 + 7 * s)
    return P


def gator_head(scale=1.0):
    """'Swamp Boss' gator-head statue (wayfinding name; no photo found: a low-poly bronze-green gator head on a
    plinth, inferred). Front = +y (snout)."""
    P = _p("gator_head")
    V, C = P.visual, P.collision
    s = scale
    V.box(-0.6 * s, -0.6 * s, 0.0, 0.6 * s, 0.6 * s, 0.9 * s, "int_ru_black", faces="+x-x+y-y+z")
    z = 0.9 * s
    # skull block, snout wedge, eyes
    V.box(-0.45 * s, -0.5 * s, z, 0.45 * s, 0.1 * s, z + 0.55 * s, "int_ru_gator_green", faces="+x-x+y-y+z")
    sn = [(-0.32 * s, 0.1 * s), (0.32 * s, 0.1 * s), (0.2 * s, 1.1 * s), (-0.2 * s, 1.1 * s)]
    for a, b in edges(sn):
        quad_wall(V, a, b, z, z + 0.25 * s, "int_ru_gator_green")
    V.poly([(p[0], p[1], z + 0.25 * s if p[1] > 0.5 * s else z + 0.38 * s) for p in sn], "int_ru_gator_green",
           normal_hint=(0, 0, 1))
    for sx in (-1, 1):
        V.box(sx * 0.3 * s - 0.08 * s, -0.25 * s, z + 0.55 * s, sx * 0.3 * s + 0.08 * s, -0.05 * s, z + 0.72 * s,
              "int_ru_gator_green", faces="+x-x+y-y+z")
        V.box(sx * 0.3 * s - 0.05 * s, -0.04 * s, z + 0.6 * s, sx * 0.3 * s + 0.05 * s, -0.03 * s, z + 0.68 * s,
              "int_ru_orange", faces="+y", glow=True)
    # teeth
    for k in range(6):
        y = 0.25 * s + k * 0.14 * s
        for sx in (-1, 1):
            x = sx * (0.3 - 0.1 * k / 6) * s
            V.poly([(x, y, z + 0.02 * s), (x, y + 0.08 * s, z + 0.02 * s), (x, y + 0.04 * s, z - 0.08 * s)], "int_ru_white",
                   normal_hint=(sx, 0, 0))
    K.col_box(C, -0.6 * s, -0.6 * s, 0.0, 0.6 * s, 0.6 * s, 0.9 * s, K.COL_NOCAM)
    return P


def storefront(width, sign_mat, wall_mat="int_ru_paint_lime", side_mat="int_ru_paint_sky", counter=True, h=4.2,
               soffit=True, menu=True, open_counter=True, depth=1.8):
    """Food court vendor front (ru_food_court_counter_2023, ru_food_court_sonic_2025): a serving counter with
    the light-blue siding front, the vendor's coloured back wall, menu screens, sign band; local: the storefront
    line is y = 0, the counter in front (+y), the kitchen behind (-y). Width along x."""
    P = _p("storefront", width=width)
    V, C = P.visual, P.collision
    W = width
    # back wall (inside the servery) + side returns
    V.poly([(W / 2, -depth, 0.0), (-W / 2, -depth, 0.0), (-W / 2, -depth, h), (W / 2, -depth, h)], wall_mat,
           normal_hint=(0, 1, 0), ao=0.9)
    for sx in (-1, 1):
        a, b = (sx * W / 2, -depth), (sx * W / 2, 0.0)
        if sx > 0:
            a, b = b, a
        quad_wall(V, a, b, 0.0, h, side_mat, ao=0.85)
    V.poly([(-W / 2, -depth, h), (W / 2, -depth, h), (W / 2, 0.0, h), (-W / 2, 0.0, h)], "int_ru_soffit",
           normal_hint=(0, 0, -1), ao=0.9)
    V.poly([(-W / 2, -depth, 0.0), (W / 2, -depth, 0.0), (W / 2, 0.0, 0.0), (-W / 2, 0.0, 0.0)], "int_ru_steel",
           normal_hint=(0, 0, 1), ao=0.8)
    # stainless kitchen line (back counter + hood)
    V.box(-W / 2 + 0.2, -depth, 0.0, W / 2 - 0.2, -depth + 0.65, 0.92, "int_ru_steel", faces="+y+z")
    V.box(-W / 2 + 0.4, -depth, 2.3, W / 2 - 0.4, -depth + 0.8, 2.9, "int_ru_steel", faces="+y-z")
    if menu:
        mw = min(W - 0.8, 3.6)
        V.poly([(mw / 2, -depth + 0.02, 1.8), (-mw / 2, -depth + 0.02, 1.8), (-mw / 2, -depth + 0.02, 2.75),
                (mw / 2, -depth + 0.02, 2.75)], "int_ru_menu", uvs=K.uv_rect(0, 0, 1, 1), glow=True,
               normal_hint=(0, 1, 0))
    if counter:
        V.box(-W / 2 + 0.1, 0.0, 0.0, W / 2 - 0.1, 0.65, 1.0, "int_ru_counter_front", faces="+y+x-x",
              uvs=None)
        V.box(-W / 2 + 0.05, -0.05, 1.0, W / 2 - 0.05, 0.72, 1.06, "int_ru_wall_cream", faces="+x-x+y-y+z")
        K.col_box(C, -W / 2, 0.0, 0.0, W / 2, 0.72, 1.06, K.COL)
    # sign band above the opening
    sw = min(W - 0.4, 3.2)
    V.poly([(sw / 2, 0.06, h - 1.2), (-sw / 2, 0.06, h - 1.2), (-sw / 2, 0.06, h - 0.15), (sw / 2, 0.06, h - 0.15)],
           sign_mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], glow=True, normal_hint=(0, 1, 0))
    P.lights.append(K.Light((0.0, -0.6, h - 0.4), radius=5.0, strength=0.35, color=(1.0, 0.95, 0.85)))
    return P


def senate_tiers(rows=4, r0=6.0, dr=1.6, a0=-55.0, a1=55.0, rise=0.18, seg=8):
    """Senate Chamber seating (ru_os_chamber): curved tiers of grey desks with navy high-back chairs, facing the
    dais at the local origin (+y side = audience). Each tier steps up `rise`."""
    P = _p("senate_tiers")
    V, C = P.visual, P.collision
    for r in range(rows):
        R = r0 + r * dr
        z = r * rise
        arc_out = [(R * math.sin(math.radians(a0 + (a1 - a0) * k / seg)), R * math.cos(math.radians(a0 + (a1 - a0) * k / seg)))
                   for k in range(seg + 1)]
        arc_in = [((R - 0.55) * math.sin(math.radians(a0 + (a1 - a0) * k / seg)),
                   (R - 0.55) * math.cos(math.radians(a0 + (a1 - a0) * k / seg))) for k in range(seg + 1)]
        arc_back = [((R + dr - 0.05) * math.sin(math.radians(a0 + (a1 - a0) * k / seg)),
                     (R + dr - 0.05) * math.cos(math.radians(a0 + (a1 - a0) * k / seg))) for k in range(seg + 1)]
        for k in range(seg):
            # tier platform (floor of this row)
            if r > 0:
                q = [arc_in[k], arc_in[k + 1], arc_back[k + 1], arc_back[k]]
                V.poly([(p[0], p[1], z) for p in q], "int_ru_carpet_aud", normal_hint=(0, 0, 1))
                quad_wall(V, arc_in[k + 1], arc_in[k], z - rise, z, "int_ru_wall_grey") if False else \
                    V.poly([(arc_in[k][0], arc_in[k][1], z - rise), (arc_in[k + 1][0], arc_in[k + 1][1], z - rise),
                            (arc_in[k + 1][0], arc_in[k + 1][1], z), (arc_in[k][0], arc_in[k][1], z)],
                           "int_ru_wall_grey", normal_hint=(-arc_in[k][0], -arc_in[k][1], 0))
            # desk: slate-grey stone top + modesty panel facing the dais + a fascia on the chairs' side
            V.poly([(arc_in[k][0], arc_in[k][1], z + 0.76), (arc_in[k + 1][0], arc_in[k + 1][1], z + 0.76),
                    (arc_out[k + 1][0], arc_out[k + 1][1], z + 0.76), (arc_out[k][0], arc_out[k][1], z + 0.76)],
                   "int_ru_wall_slate", normal_hint=(0, 0, 1))
            V.poly([(arc_out[k + 1][0], arc_out[k + 1][1], z + 0.62), (arc_out[k][0], arc_out[k][1], z + 0.62),
                    (arc_out[k][0], arc_out[k][1], z + 0.76), (arc_out[k + 1][0], arc_out[k + 1][1], z + 0.76)],
                   "int_ru_black", normal_hint=(arc_out[k][0], arc_out[k][1], 0))
            V.poly([(arc_in[k][0], arc_in[k][1], z), (arc_in[k + 1][0], arc_in[k + 1][1], z),
                    (arc_in[k + 1][0], arc_in[k + 1][1], z + 0.76), (arc_in[k][0], arc_in[k][1], z + 0.76)],
                   "int_ru_wall_grey", normal_hint=(-arc_in[k][0], -arc_in[k][1], 0))
            # chairs behind the desk (navy high backs), two per segment
            for f in (0.3, 0.75):
                a = math.radians(a0 + (a1 - a0) * (k + f) / seg)
                cx, cy = (R + 0.45) * math.sin(a), (R + 0.45) * math.cos(a)
                tx, ty = math.cos(a), -math.sin(a)
                nx, ny = math.sin(a), math.cos(a)
                b0 = (cx - tx * 0.25 + nx * 0.25, cy - ty * 0.25 + ny * 0.25)
                b1 = (cx + tx * 0.25 + nx * 0.25, cy + ty * 0.25 + ny * 0.25)
                V.poly([(b0[0], b0[1], z + 0.45), (b1[0], b1[1], z + 0.45), (b1[0], b1[1], z + 1.2), (b0[0], b0[1], z + 1.2)],
                       "int_ru_fabric_navy", normal_hint=(-nx, -ny, 0))
                V.poly([(b1[0], b1[1], z + 0.45), (b0[0], b0[1], z + 0.45), (b0[0], b0[1], z + 1.2), (b1[0], b1[1], z + 1.2)],
                       "int_ru_fabric_navy", normal_hint=(nx, ny, 0))
                s0 = (cx - tx * 0.25 - nx * 0.25, cy - ty * 0.25 - ny * 0.25)
                s1 = (cx + tx * 0.25 - nx * 0.25, cy + ty * 0.25 - ny * 0.25)
                V.poly([(s0[0], s0[1], z + 0.45), (s1[0], s1[1], z + 0.45), (b1[0], b1[1], z + 0.45), (b0[0], b0[1], z + 0.45)],
                       "int_ru_fabric_navy", normal_hint=(0, 0, 1))
        # collision: the desk band as a wall-ish block per segment pair, tier step as a floor
        for k in range(0, seg, 2):
            k2 = min(seg, k + 2)
            foot = [arc_in[k], arc_in[k2], arc_out[k2], arc_out[k]]
            K.col_prism(C, ccw(foot), z, z + 0.76, K.COL_NOCAM)
            if r > 0:
                q = ccw([arc_in[k], arc_in[k2], arc_back[k2], arc_back[k]])
                C.prism(q, z - rise, z, K.COL, top=K.COL)
    return P


def bed_set(w=1.6, L=2.1):
    """Hotel room (ru_hotel_room): queen bed (white duvet, royal-blue skirt), cherry headboard + nightstands with
    lamps. Local: headboard against the wall at y = 0, bed toward +y."""
    P = _p("hotel_bed")
    V, C = P.visual, P.collision
    V.box(-w / 2, 0.0, 0.0, w / 2, L, 0.35, "int_ru_uf_blue", faces="+x-x+y")
    V.box(-w / 2, 0.0, 0.35, w / 2, L, 0.62, "int_ru_bed", faces="+x-x+y+z")
    V.box(-w / 2 + 0.1, 0.1, 0.62, -0.05, 0.6, 0.78, "int_ru_bed", faces="+x-x+y-y+z")
    V.box(0.05, 0.1, 0.62, w / 2 - 0.1, 0.6, 0.78, "int_ru_bed", faces="+x-x+y-y+z")
    V.box(-w / 2 - 0.05, -0.06, 0.0, w / 2 + 0.05, 0.04, 1.35, "int_ru_cherry", faces="+x-x+y+z")
    for sx in (-1, 1):
        x = sx * (w / 2 + 0.35)
        V.box(x - 0.28, 0.0, 0.0, x + 0.28, 0.45, 0.62, "int_ru_cherry", faces="+x-x+y+z")
        cyl(V, x, 0.22, 0.06, 0.62, 0.95, "int_ru_steel", n=5, top=False)
        cyl(V, x, 0.22, 0.17, 0.95, 1.25, "int_ru_bed", n=6, top=False)
        P.lights.append(K.Light((x, 0.3, 1.1), radius=3.0, strength=0.25, color=(1.0, 0.86, 0.62)))
    K.col_box(C, -w / 2, 0.0, 0.0, w / 2, L, 0.62, K.COL_NOCAM)
    P.info["top_z"] = 0.62
    return P


def dresser_tv(L=1.6):
    P = _p("dresser_tv")
    V, C = P.visual, P.collision
    V.box(-L / 2, 0.0, 0.0, L / 2, 0.5, 0.8, "int_ru_cherry", faces="+x-x+y+z")
    V.poly([(-0.55, 0.03, 1.2), (0.55, 0.03, 1.2), (0.55, 0.03, 1.85), (-0.55, 0.03, 1.85)], "int_ru_tv_hotel",
           uvs=K.ONCE, normal_hint=(0, 1, 0))
    K.col_box(C, -L / 2, 0.0, 0.0, L / 2, 0.5, 0.8, K.COL_NOCAM)
    return P


def sofa(L=2.0, mat="int_ru_uf_blue"):
    P = _p("sofa")
    V, C = P.visual, P.collision
    V.box(-L / 2, 0.0, 0.0, L / 2, 0.9, 0.42, mat, faces="+x-x+y+z")
    V.box(-L / 2, 0.0, 0.42, L / 2, 0.22, 0.9, mat, faces="+x-x+y+z")
    for sx in (-1, 1):
        V.box(sx * L / 2 - (0.18 if sx > 0 else 0), 0.22, 0.42, sx * L / 2 + (0 if sx > 0 else 0.18), 0.9, 0.62, mat,
              faces="+x-x+y+z")
    K.col_box(C, -L / 2, 0.0, 0.0, L / 2, 0.9, 0.45, K.COL_NOCAM)
    return P


def cafe_table_set(table_w=0.75, h=0.75, chairs=4, chair_mat="int_ru_fabric_navy", top="int_wood", frame="int_ru_wood_panel"):
    """Square cafe table with 2-4 wood/navy chairs (food court, Arredondo Cafe)."""
    P = _p("cafe_table")
    V, C = P.visual, P.collision
    t = table_w / 2
    V.box(-t, -t, h - 0.04, t, t, h, top, faces="+x-x+y-y+z")
    V.box(-0.04, -0.04, 0.0, 0.04, 0.04, h - 0.04, "int_ru_black", faces="+x-x+y-y")
    for k in range(chairs):
        a = math.pi / 2 * k
        cx, cy = 0.62 * math.cos(a), 0.62 * math.sin(a)
        fx, fy = -math.cos(a), -math.sin(a)
        tx, ty = -fy, fx
        V.box(cx - 0.2, cy - 0.2, 0.44, cx + 0.2, cy + 0.2, 0.48, chair_mat, faces="+z")
        b0 = (cx - fx * 0.2 + tx * 0.2, cy - fy * 0.2 + ty * 0.2)
        b1 = (cx - fx * 0.2 - tx * 0.2, cy - fy * 0.2 - ty * 0.2)
        for (za, zb_, m) in ((0.0, 0.44, "int_ru_black"), (0.62, 0.88, frame)):
            V.poly([(b0[0], b0[1], za), (b1[0], b1[1], za), (b1[0], b1[1], zb_), (b0[0], b0[1], zb_)], m,
                   normal_hint=(fx, fy, 0))
            V.poly([(b1[0], b1[1], za), (b0[0], b0[1], za), (b0[0], b0[1], zb_), (b1[0], b1[1], zb_)], m,
                   normal_hint=(-fx, -fy, 0))
    K.col_box(C, -t, -t, 0.0, t, t, h, K.COL_NOCAM)
    P.info["top_z"] = h
    return P


def high_top(h=1.05, r=0.35, stools=3):
    """High-top table with stools by the dining windows (ru_dining_windows)."""
    P = _p("high_top")
    V, C = P.visual, P.collision
    cyl(V, 0.0, 0.0, r, h - 0.04, h, "int_ru_black", n=8)
    cyl(V, 0.0, 0.0, 0.04, 0.0, h - 0.04, "int_ru_steel", n=5, top=False)
    for k in range(stools):
        a = 2 * math.pi * k / stools
        cx, cy = 0.6 * math.cos(a), 0.6 * math.sin(a)
        cyl(V, cx, cy, 0.18, 0.72, 0.78, "int_ru_black", n=6)
        cyl(V, cx, cy, 0.025, 0.0, 0.72, "int_ru_steel", n=4, top=False)
    K.col_box(C, -r, -r, 0.0, r, r, h, K.COL_NOCAM)
    return P


def podium(w=0.6, d=0.5, h=1.15):
    P = _p("podium")
    V, C = P.visual, P.collision
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_ru_cherry", faces="+x-x+y-y+z")
    V.box(-w / 2 + 0.05, d / 2, 0.3, w / 2 - 0.05, d / 2 + 0.01, 0.8, "int_ru_dais", uvs=None, faces="+y")
    K.col_box(C, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, K.COL_NOCAM)
    return P


def stage_platform(w, d, h=0.6, mat="int_ru_black", drape_h=3.0, drape=True):
    """Portable stage (ru_os_grand_ballroom_2) with a black skirt and a black pipe-and-drape behind: walkable."""
    P = _p("stage_platform")
    V, C = P.visual, P.collision
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, mat, faces="+x-x+y-y+z", mats={"+z": "int_ru_concrete_dark"})
    if drape:
        V.poly([(w / 2 + 1.0, -d / 2 - 0.3, 0.0), (-w / 2 - 1.0, -d / 2 - 0.3, 0.0), (-w / 2 - 1.0, -d / 2 - 0.3, drape_h),
                (w / 2 + 1.0, -d / 2 - 0.3, drape_h)], "int_ru_drape", normal_hint=(0, 1, 0))
    C.prism([(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)], 0.0, h, K.COL, top=K.COL)
    P.info["top_z"] = h
    return P


def free_library(w=1.2, h=1.6):
    """The atrium free library (wayfinding name): a small bookcase."""
    P = _p("free_library")
    V, C = P.visual, P.collision
    V.box(-w / 2, -0.2, 0.0, w / 2, 0.2, h, "int_ru_wood_panel", faces="+x-x-y+z")
    V.poly([(-w / 2 + 0.05, 0.19, 0.2), (w / 2 - 0.05, 0.19, 0.2), (w / 2 - 0.05, 0.19, h - 0.1), (-w / 2 + 0.05, 0.19, h - 0.1)],
           "int_ru_books", uvs=[(1, 0), (0, 0), (0, 1), (1, 1)][::-1][::-1], normal_hint=(0, 1, 0))
    K.col_box(C, -w / 2, -0.2, 0.0, w / 2, 0.2, h, K.COL_NOCAM)
    return P


def info_desk(L=3.6, d=0.8, h=1.07):
    """Information desk (no photo found: a curved white counter with a navy front and UF-blue sign, inferred)."""
    P = _p("info_desk")
    V, C = P.visual, P.collision
    n = 6
    pts = [(L / 2 * math.sin(math.radians(-60 + 120 * k / n)) * 1.0, 0.6 * math.cos(math.radians(-60 + 120 * k / n)) - 0.3)
           for k in range(n + 1)]
    for a, b in zip(pts, pts[1:]):
        quad_wall(V, b, a, 0.0, h, "int_ru_uf_blue")
        a2 = (a[0] * 0.8, a[1] - d)
        b2 = (b[0] * 0.8, b[1] - d)
        V.poly([(a[0], a[1], h), (b[0], b[1], h), (b2[0], b2[1], h), (a2[0], a2[1], h)], "int_ru_white",
               normal_hint=(0, 0, 1))
    xs = [p[0] for p in pts]
    K.col_box(C, min(xs), min(p[1] for p in pts) - d, 0.0, max(xs), max(p[1] for p in pts), h, K.COL_NOCAM)
    return P


def picnic_table():
    """Breezeway picnic table (ru_breezeway_night_commons, ru_breezeway_piers_1): concrete top + benches."""
    P = _p("picnic_table")
    V, C = P.visual, P.collision
    V.box(-0.9, -0.38, 0.72, 0.9, 0.38, 0.78, "concrete", faces="+x-x+y-y+z")
    V.box(-0.15, -0.15, 0.0, 0.15, 0.15, 0.72, "concrete", faces="+x-x+y-y")
    for sy in (-1, 1):
        V.box(-0.9, sy * 0.75 - 0.15, 0.42, 0.9, sy * 0.75 + 0.15, 0.47, "concrete", faces="+x-x+y-y+z")
        V.box(-0.1, sy * 0.75 - 0.1, 0.0, 0.1, sy * 0.75 + 0.1, 0.42, "concrete", faces="+x-x+y-y")
    K.col_box(C, -0.9, -0.9, 0.0, 0.9, 0.9, 0.78, K.COL_NOCAM)
    return P


def all_props():
    return {"lanes": bowling_lane_set(4), "booth": booth(), "billiards": billiard_table(), "arcade": arcade_cabinet(),
            "esports": esports_row(4), "lounge": lounge_chair(), "swivel": lounge_chair("int_fabric_orange", swivel=True),
            "uf_letters": uf_letters(), "gator_head": gator_head(), "storefront": storefront(5.0, "int_ru_vend_burger"),
            "senate": senate_tiers(2), "bed": bed_set(), "rows": chair_rows(3, 8, aisle_every=4),
            "round_table": round_table(), "cafe": cafe_table_set(), "ping_pong": ping_pong(), "air_hockey": air_hockey(),
            "foosball": foosball(), "podium": podium(), "stage": stage_platform(6, 3), "info_desk": info_desk(),
            "picnic": picnic_table(), "folding": folding_table(), "sofa": sofa(), "dresser": dresser_tv(),
            "led": led_frame(3.4, 2.2, 3.0), "library": free_library(), "high_top": high_top(),
            "draped": draped_table(), "coffee": coffee_table()}


def selftest(verbose=True):
    problems = []
    # triangulation: L shape, square with a hole, collinear points
    L = [(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)]
    a = sum(abs(signed_area(t)) for t in triangulate(L))
    if abs(a - 6.0) > 1e-6:
        problems.append(f"L-shape area {a}")
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(3, 3), (6, 3), (6, 7), (3, 7)]
    a = sum(abs(signed_area(t)) for t in triangulate(sq, [hole]))
    if abs(a - 88.0) > 1e-6:
        problems.append(f"square-with-hole area {a}")
    a = sum(abs(signed_area(t)) for t in triangulate([(0, 0), (2, 0), (4, 0), (4, 4), (0, 4)]))
    if abs(a - 16.0) > 1e-6:
        problems.append(f"collinear area {a}")
    pcs = grid_pieces(triangulate(sq), 3.0)
    a = sum(abs(signed_area(p)) for p in pcs)
    if abs(a - 100.0) > 1e-6:
        problems.append(f"grid pieces area {a}")
    for name, P in all_props().items():
        for p in P.visual.polys + P.collision.polys:
            if not K.known_material(p.mat):
                problems.append(f"{name}: unknown material {p.mat}")
        t = P.tris()
        if verbose:
            print(f"  {name:12s} visual {t['visual']:5d}  collision {t['collision']:4d}")
    for n, m in RU_MATERIALS.items():
        if m["size"][0] * m["size"][1] > 2048:
            problems.append(f"{n}: {m['size']} exceeds 4 KB RGBA16")
    print("selftest:", "OK" if not problems else problems)
    return problems


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--textures" in args or "--sheet" in args:
        out = None
        if "--out" in args:
            out = args[args.index("--out") + 1]
        sheet = args[args.index("--sheet") + 1] if "--sheet" in args else None
        w = write_textures(out, sheet)
        print(f"interior_kit_reitz: {len(w)} textures in {out or stage_palette.TEXTURE_DIR}")
    if "--selftest" in args:
        sys.exit(1 if selftest() else 0)


# ================================================================== stairs
def stair_flight(V, C, a, b, z0, z1, width, steps=None, tread_mat="int_ru_terrazzo", side_mat="int_ru_white",
                 soffit=True, rails=True, rail_h=1.07, col_mat="COL notslip", stringer=0.35):
    """Open stair flight from a (bottom, z0) to b (top, z1) in plan, `width` wide (photos: white stringers and
    soffit, terrazzo treads, silver picket railings). Collision: one ramp (no-slip) + the two railings."""
    L = math.dist(a, b)
    if L < 0.2:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    h = z1 - z0
    n = steps or max(3, int(round(h / 0.19)))
    rise, run = h / n, L / n
    w2 = width / 2

    def P(s, off, z):
        return (a[0] + dx * s + nx * off, a[1] + dy * s + ny * off, z)
    for k in range(n):
        s0, s1 = k * run, (k + 1) * run
        zt = z0 + (k + 1) * rise
        V.poly([P(s0, -w2, zt), P(s1, -w2, zt), P(s1, w2, zt), P(s0, w2, zt)], tread_mat, normal_hint=(0, 0, 1),
               ao=1.0)
        V.poly([P(s0, w2, zt - rise), P(s0, -w2, zt - rise), P(s0, -w2, zt), P(s0, w2, zt)], side_mat,
               normal_hint=(-dx, -dy, 0), ao=0.85)
    # stringers (white side plates following the slope) + soffit
    for off in (-w2, w2):
        sgn = 1 if off > 0 else -1
        q = [P(0, off, z0 - stringer), P(L, off, z1 - stringer), P(L, off, z1 + 0.12), P(0, off, z0 + 0.12)]
        V.poly(q, side_mat, normal_hint=(nx * sgn, ny * sgn, 0), ao=0.95)
        V.poly(list(reversed(q)), side_mat, normal_hint=(-nx * sgn, -ny * sgn, 0), ao=0.9)
    if soffit:
        V.poly([P(0, w2, z0 - stringer), P(L, w2, z1 - stringer), P(L, -w2, z1 - stringer), P(0, -w2, z0 - stringer)],
               side_mat, normal_hint=(0, 0, -1), ao=0.9)
    if rails:
        for off in (-w2 + 0.05, w2 - 0.05):
            pa, pb = P(0, off, z0), P(L, off, z1)
            V.poly([pa, pb, (pb[0], pb[1], pb[2] + rail_h), (pa[0], pa[1], pa[2] + rail_h)], "int_ru_picket",
                   uvs=[(0, 0), (L / 1.1, 0), (L / 1.1, 1), (0, 1)], ao=1.0)
            V.poly([(pa[0], pa[1], pa[2] + rail_h), (pb[0], pb[1], pb[2] + rail_h), (pb[0], pb[1], pb[2] + rail_h + 0.06),
                    (pa[0], pa[1], pa[2] + rail_h + 0.06)], "int_ru_steel", ao=1.0)
            V.poly([(pb[0], pb[1], pb[2] + rail_h), (pa[0], pa[1], pa[2] + rail_h), (pa[0], pa[1], pa[2] + rail_h + 0.06),
                    (pb[0], pb[1], pb[2] + rail_h + 0.06)], "int_ru_steel", ao=1.0)
    # collision: ramp + railing blocks
    if C is not None:
        ramp = [P(0, -w2, z0), P(L, -w2, z1), P(L, w2, z1), P(0, w2, z0)]
        add_raw(C, ramp, col_mat, normal_hint=(0, 0, 1))
        if rails:
            for off in (-w2 + 0.05, w2 - 0.05):
                pa, pb = P(0, off, z0), P(L, off, z1)
                for sgn in (1, -1):
                    o = 0.07 * sgn
                    q = [(pa[0] + nx * o, pa[1] + ny * o, pa[2] - 0.3), (pb[0] + nx * o, pb[1] + ny * o, pb[2] - 0.3),
                         (pb[0] + nx * o, pb[1] + ny * o, pb[2] + rail_h), (pa[0] + nx * o, pa[1] + ny * o, pa[2] + rail_h)]
                    C.poly(q, K.COL_NOCAM, normal_hint=(nx * sgn, ny * sgn, 0))
    return {"len": L, "angle_deg": math.degrees(math.atan2(h, L)), "steps": n}


def seg_intersect(p, d, poly):
    """Smallest t >= 0 where the ray p + t d crosses an edge of poly (or None)."""
    best = None
    for a, b in edges(poly):
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
        u = ((a[0] - p[0]) * d[1] - (a[1] - p[1]) * d[0]) / den
        if t >= 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return best
