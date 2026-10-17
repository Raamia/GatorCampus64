"""Placeholder face textures for characters that do not have hand-made face art yet.

Produces the same file set and conventions as the face-art workflow
(art/<id>/textures/): eyes_open/half/closed/left/right/up/down/dead.png (64x32,
both eyes in one texture) and mouth_grin.png (32x16), drawn pixel by pixel on an
OPAQUE background of exactly colors.skin. The builder keys that colour to alpha 0.

Style choices come from character.json: eye/brow/lash colours from `colors`
(eyes, eyebrows, hair), lashes and a smiling (crinkled) lower lid are inferred
from `signature_traits` / pronouns, the mouth from the traits text (teeth smile
vs closed smile). This is deliberately simple: real art from the face-art
workflow always takes precedence.

Run standalone (no Blender needed):
    python3 sgl_face_gen.py <character_id> [out_dir]
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sgl_util import build_dir, hex_to_rgb8, load_spec, mix_hex, shade_hex, upscale, write_png  # noqa: E402

EYE_W, EYE_H = 64, 32
MOUTH_W, MOUTH_H = 32, 16
EYE_STATES = ["open", "half", "closed", "left", "right", "up", "down", "dead"]


def face_style(spec):
    c = spec.get("colors", {})
    text = " ".join(spec.get("signature_traits", []) + list(spec.get("outfit", {}).values())).lower()
    padded = f" {text} "
    feminine = any(w in padded for w in (" she ", " her ", " hers "))
    skin = c["skin"]
    hair = c.get("hair", "#1E1A1B")
    face = spec.get("face", {})
    style = {
        "skin": skin,
        "skin_shadow": c.get("skin_shadow", shade_hex(skin, 0.88)),
        "lash": face.get("lash", mix_hex(hair, "#000000", 0.25)),
        "lower_lid": face.get("lower_lid", mix_hex(c.get("skin_shadow", shade_hex(skin, 0.85)), "#5A3328", 0.55)),
        "brow": c.get("eyebrows", mix_hex(hair, skin, 0.12)),
        "sclera": "#FAF6F0",
        "iris": face.get("iris", c.get("eyes", "#3B2117")),
        "pupil": "#120A08",
        "highlight": "#FFFFFF",
        "blush": face.get("blush", mix_hex(skin, "#E8707A", 0.35)),
        "lip_line": face.get("lip_line", "#8C3A3C"),
        "lip": face.get("lip", mix_hex(skin, "#C8545C", 0.45)),
        "teeth": "#FFFDF6",
        "mouth": "#6A2226",
        "tongue": "#C25A63",
        "lashes": face.get("lashes", feminine or re.search(r"\blash(es)?\b", text) is not None),
        "smiling_eyes": face.get("smiling_eyes", any(w in text for w in ("crinkle", "squint", "crescent"))),
        "teeth_smile": face.get("teeth_smile", "teeth" in text or "toothy" in text),
        "blush_on": face.get("blush_on", feminine),
    }
    style["iris_light"] = mix_hex(style["iris"], "#B07A50", 0.35)
    return style


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = [[bg] * w for _ in range(h)]

    def put(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = col

    def get(self, x, y):
        return self.px[y][x]

    def rows(self):
        return [[hex_to_rgb8(c) + (255,) for c in row] for row in self.px]


# ------------------------------------------------------------------ eyes
# Image-left eye (the character's right eye); outer corner on the image left.
# The other eye is the mirror image (x -> 63 - x). Per column: first and last
# row of the open eye interior (sclera).
EYE_COLS = list(range(11, 27))
EYE_TOP = [17, 15, 14, 13, 13, 12, 12, 12, 12, 12, 12, 13, 13, 14, 15, 16]
EYE_BOT = [19, 20, 21, 21, 22, 22, 22, 22, 22, 22, 22, 21, 21, 21, 20, 18]
EYE_BOT_SMILE = [19, 20, 20, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21, 20, 20, 18]
IRIS_C = (18.5, 17.0)
IRIS_R = 4.3
PUPIL_R = 2.0
BROW = {12: 8, 13: 7, 14: 7, 15: 6, 16: 6, 17: 6, 18: 6, 19: 6, 20: 6, 21: 6, 22: 6, 23: 7, 24: 7, 25: 8}


def draw_eye(cv, st, state, mirror):
    def X(x):
        return 63 - x if mirror else x

    col = {}
    bot_tab = EYE_BOT_SMILE if st["smiling_eyes"] else EYE_BOT
    top = dict(zip(EYE_COLS, EYE_TOP))
    bot = dict(zip(EYE_COLS, bot_tab))

    # brows (always)
    for x, y in BROW.items():
        cv.put(X(x), y, st["brow"])
        if 14 <= x <= 18:
            cv.put(X(x), y + 1, st["brow"])

    if st["blush_on"]:
        for x, y in ((9, 25), (10, 25), (11, 25), (12, 25), (10, 26), (11, 26)):
            cv.put(X(x), y, st["blush"])

    if state == "dead":
        cx = round(IRIS_C[0])
        cy = round(IRIS_C[1])
        for d in range(-3, 4):
            for t in (0, 1):
                cv.put(X(cx + d + t), cy + d, st["lash"])
                cv.put(X(cx + d + t), cy - d, st["lash"])
        return

    if state == "closed":
        n = len(EYE_COLS) - 1
        for i, x in enumerate(EYE_COLS):
            y = 18 + round(2.0 * math.sin(math.pi * i / n))
            cv.put(X(x), y, st["lash"])
            if 2 <= i <= n - 2:
                cv.put(X(x), y - 1, st["lash"])
        if st["lashes"]:
            for x, y in ((10, 18), (9, 19), (10, 19)):
                cv.put(X(x), y, st["lash"])
        return

    if state == "half":
        top = {x: min(bot[x] - 2, max(top[x], 16)) for x in EYE_COLS}
        top[EYE_COLS[0]] = bot[EYE_COLS[0]] - 1
        top[EYE_COLS[-1]] = bot[EYE_COLS[-1]] - 1
    elif state == "down":
        top = {x: min(bot[x] - 1, top[x] + 2) for x in EYE_COLS}

    # iris centre (gaze offsets are in absolute image space, not mirrored)
    cx, cy = IRIS_C
    if mirror:
        cx = 63 - cx
    dx = {"left": -3, "right": 3}.get(state, 0)
    dy = {"up": -2, "down": 2}.get(state, 0)
    cx += dx
    cy += dy

    for x in EYE_COLS:
        for y in range(top[x], bot[x] + 1):
            xx = X(x)
            d = math.hypot(xx - cx, (y - cy) * 1.05)
            if d <= PUPIL_R:
                c = st["pupil"]
            elif d <= IRIS_R:
                c = st["iris_light"] if y >= cy + 1.5 else st["iris"]
            else:
                c = st["sclera"]
            cv.put(xx, y, c)

    # highlight: same image side on both eyes (light from the upper left)
    hx, hy = round(cx - 2.2), round(cy - 2.6)
    for x, y in ((hx, hy), (hx + 1, hy), (hx, hy + 1), (hx + 1, hy + 1)):
        for ex in EYE_COLS:
            if X(ex) == x and top[ex] <= y <= bot[ex]:
                cv.put(x, y, st["highlight"])
    sx, sy = round(cx + 2), round(cy + 2)
    for ex in EYE_COLS:
        if X(ex) == sx and top[ex] <= sy <= bot[ex]:
            cv.put(sx, sy, st["highlight"])

    # upper lid / lash line (2 px thick in the middle), outer flick
    for i, x in enumerate(EYE_COLS):
        cv.put(X(x), top[x] - 1, st["lash"])
        if 1 <= i <= len(EYE_COLS) - 3:
            cv.put(X(x), top[x] - 2, st["lash"])
    x0 = EYE_COLS[0]
    cv.put(X(x0 - 1), top[x0], st["lash"])
    if st["lashes"]:
        cv.put(X(x0 - 1), top[x0] - 1, st["lash"])
        cv.put(X(x0 - 2), top[x0] - 2, st["lash"])
        cv.put(X(x0), top[x0] - 2, st["lash"])
    # lower lid: soft line under the middle of the eye
    for i, x in enumerate(EYE_COLS):
        if 2 <= i <= len(EYE_COLS) - 3:
            cv.put(X(x), bot[x] + 1, st["lower_lid"])
    xe = EYE_COLS[-1]
    cv.put(X(xe + 1), bot[xe], st["lower_lid"])
    if st["smiling_eyes"]:
        # small smile crease under the outer corner
        cv.put(X(x0 + 1), bot[x0] + 2, st["skin_shadow"])
        cv.put(X(x0 + 2), bot[x0] + 3, st["skin_shadow"])


def make_eyes(st, state):
    cv = Canvas(EYE_W, EYE_H, st["skin"])
    draw_eye(cv, st, state, mirror=False)
    draw_eye(cv, st, state, mirror=True)
    return cv


# ------------------------------------------------------------------ mouth
def make_mouth(st):
    cv = Canvas(MOUTH_W, MOUTH_H, st["skin"])
    if st["teeth_smile"]:
        # D-shaped open smile: straight upper lip with upturned corners,
        # a band of upper teeth, dark mouth and a hint of tongue.
        top = {9: 4, 10: 5, 11: 5, 12: 5, 13: 5, 14: 5, 15: 5, 16: 5, 17: 5, 18: 5, 19: 5, 20: 5, 21: 5, 22: 4}
        bot = {10: 6, 11: 7, 12: 8, 13: 9, 14: 9, 15: 9, 16: 9, 17: 9, 18: 9, 19: 8, 20: 7, 21: 6}
        for x, y in top.items():
            cv.put(x, y, st["lip_line"])
        for x, yb in bot.items():
            for y in range(top[x] + 1, yb + 1):
                if y <= top[x] + 2:
                    c = st["teeth"]
                elif y == yb and 13 <= x <= 18:
                    c = st["tongue"]
                else:
                    c = st["mouth"]
                cv.put(x, y, c)
            cv.put(x, yb + 1, st["lip_line"])
        for x in range(12, 20):
            cv.put(x, bot.get(x, 6) + 2, st["lip"])
    else:
        # closed gentle smile
        pts = {9: 6, 10: 7, 11: 8, 12: 8, 13: 9, 14: 9, 15: 9, 16: 9, 17: 9, 18: 9, 19: 8, 20: 8, 21: 7, 22: 6}
        for x, y in pts.items():
            cv.put(x, y, st["lip_line"])
        for x in range(13, 19):
            cv.put(x, 10, st["lip"])
    return cv


def generate(spec, out_dir):
    st = face_style(spec)
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    sheet_rows = []
    for state in EYE_STATES:
        cv = make_eyes(st, state)
        path = os.path.join(out_dir, f"eyes_{'half' if state == 'half' else state}.png")
        write_png(path, cv.rows())
        files[f"eyes_{state}"] = path
        sheet_rows.append(cv.rows())
    m = make_mouth(st)
    mpath = os.path.join(out_dir, "mouth_grin.png")
    write_png(mpath, m.rows())
    files["mouth_grin"] = mpath

    # preview sheet: 2 columns of eye states + mouth, 6x nearest
    k = 6
    gap = (40, 40, 44, 255)
    tiles = [upscale(r, k) for r in sheet_rows]
    tw, th = EYE_W * k, EYE_H * k
    mouth_big = upscale(m.rows(), k)
    cols = 2
    rows_n = (len(tiles) + 1 + cols - 1) // cols
    W = cols * tw + (cols + 1) * 8
    H = rows_n * th + (rows_n + 1) * 8
    sheet = [[gap] * W for _ in range(H)]
    items = tiles + [mouth_big]
    for i, t in enumerate(items):
        r, c = divmod(i, cols)
        oy = 8 + r * (th + 8)
        ox = 8 + c * (tw + 8)
        for y, row in enumerate(t):
            sheet[oy + y][ox:ox + len(row)] = row
    write_png(os.path.join(out_dir, "preview_sheet.png"), sheet)
    return files


if __name__ == "__main__":
    cid = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(build_dir(cid), "tex", "generated")
    print(generate(load_spec(cid), out))
